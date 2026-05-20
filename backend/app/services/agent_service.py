"""
Agent Service — v1.0 (browser-use Powered)

使用 browser-use 库实现 AI Agent 驱动的浏览器自动化执行.
Agent 能"看见"页面的 Accessibility Tree,实现 观察→推理→执行→验证 的闭环.

与 AIService 的区别:
- AIService: 纯 Prompt → LLM → JSON Steps (盲猜模式, 快速但不精准)
- AgentService: 自然语言 → Agent 打开浏览器执行 → 提取已验证的 Steps (精准模式)
"""
import time
import re
import json
import asyncio
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logger import logger

# browser-use imports
from browser_use import Agent, Browser
from browser_use.llm import ChatDeepSeek, ChatOpenAI


class AgentService:
    """
    browser-use Agent Service — AI 精准执行引擎

    核心能力:
    1. 接收自然语言任务描述
    2. 启动浏览器,Agent 实时观察页面 Accessibility Tree
    3. LLM 基于真实页面结构推理下一步
    4. Agent 执行操作并验证结果
    5. 提取已验证的 Steps 返回给平台
    """

    # ==========================================
    # 核心方法: 构建大模型驱动 Agent
    # ==========================================

    def _build_llm(self, model_config: Any):
        """
        根据数据库模型配置构建 LLM 实例.

        - DeepSeek → ChatDeepSeek (browser-use 原生支持)
        - 其他 OpenAI 兼容厂商 → ChatOpenAI (LangChain)
        """
        import json
        
        base_url = model_config.base_url or ""
        api_key = model_config.api_key
        model_name = model_config.model_identifier
        
        # 提取动态参数
        temperature = getattr(model_config, 'temperature', 0.1)
        if temperature is None:
            temperature = 0.1
            
        max_tokens = getattr(model_config, 'max_tokens', 8192)
        if max_tokens is None:
            max_tokens = 8192
        
        # 提取额外 kwargs
        extra_kwargs = {}
        raw_kwargs = getattr(model_config, 'kwargs', None)
        if raw_kwargs:
            try:
                extra_kwargs = json.loads(raw_kwargs)
                if not isinstance(extra_kwargs, dict):
                    extra_kwargs = {}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse kwargs JSON for model {model_config.name}")

        # 根据模型标识符本身判断是否属于 DeepSeek 系列,而非强依赖域名(适应各种内部网关 / 第三方API代理转发)
        is_deepseek = "deepseek" in (model_name or "").lower()

        if is_deepseek:
            # DeepSeek Reasoner / R1 系列,以及可能存在的 v4
            is_reasoning_model = any(keyword in (model_name or "").lower() for keyword in ["reasoner", "r1", "v4-"])
            
            if is_reasoning_model:
                if "reasoning_effort" not in extra_kwargs:
                    extra_kwargs["reasoning_effort"] = "high"
                
                # 兼容一些第三方中转 API 的 thinking 模式(官方 API 暂不支持此 extra_body 字段,但支持 reasoning_content)
                # 如果是官方 API 且识别为 reasoning 模型,ChatDeepSeek 内部会自动处理
                if "extra_body" not in extra_kwargs:
                    # 仅在非官方或特定场景下添加,标准 ChatDeepSeek 包装器会处理官方逻辑
                    pass 

            logger.info(f"AgentService: Using ChatDeepSeek for {model_config.name} (temp={temperature}, kwargs={extra_kwargs})")
            return ChatDeepSeek(
                base_url=base_url,
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                **extra_kwargs
            )
        else:
            # MiniMax, GLM, 通义千问等 OpenAI 兼容厂商
            logger.info(f"AgentService: Using browse-use native ChatOpenAI wrapper for {model_config.name} (temp={temperature}, kwargs={extra_kwargs})")
            return ChatOpenAI(
                base_url=base_url,
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                **extra_kwargs
            )

    async def execute_task(
        self,
        db: AsyncSession,
        task: str,
        model_id: Optional[str] = None,
        headless: bool = True,
        max_steps: int = 20,
        use_vision: bool = False,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        执行 AI Agent 任务.

        Args:
            db: 数据库会话
            task: 自然语言任务描述
            model_id: AI 模型 ID (可选,默认使用系统默认模型)
            headless: 是否无头模式
            max_steps: Agent 最大步骤数
            use_vision: 是否使用视觉模型 (消耗更多 Token)
            project_id: 当前关联项目ID(用于拉取 Page Object 库和记忆)

        Returns:
            dict: 包含 success, message, steps, execution_time 等
        """
        start_time = time.time()

        # 1. 从数据库获取模型配置
        from app.services.ai_model_service import ai_model_service

        db_model = None
        if model_id and str(model_id).isdigit():
            db_model = await ai_model_service.get(db, int(model_id))

        if not db_model:
            db_model = await ai_model_service.get_default(db)

        if not db_model or not db_model.is_active:
            return {
                "success": False,
                "message": "未找到可用的 AI 模型配置,请先在 AI 配置页面添加模型.",
                "steps": [],
                "execution_time": 0.0,
                "total_agent_steps": 0,
                "errors": ["No active AI model found"],
            }

        # 2. 构建 LLM
        is_deepseek = db_model and "deepseek" in (db_model.model_identifier or "").lower()
        try:
            llm = self._build_llm(db_model)
        except Exception as e:
            logger.error(f"AgentService: Failed to build LLM: {e}")
            return {
                "success": False,
                "message": f"LLM 初始化失败: {str(e)}",
                "steps": [],
                "execution_time": 0.0,
                "total_agent_steps": 0,
                "errors": [str(e)],
            }

        # 3. 执行核心逻辑 (包装在 try 中防止 500)
        errors = []
        agent_history = None
        browser = None
        
        try:
            # 3.1 配置并启动浏览器
            logger.info(f"AgentService: Initializing browser (headless={headless}, incognito=True)...")
            browser = Browser(headless=headless, args=["--incognito"])
            await browser.start()
            
            # 3.2 创建 Agent
            logger.info("AgentService: Creating Agent instance...")
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                use_vision=use_vision,
                use_thinking=True if is_deepseek else False, # DeepSeek 模型开启思维链以提高 JSON 结构准确度
                extend_system_message="""
你是一个具备高度推理能力的 UI 自动化专家. 你的目标是将用户的自然语言意图转化为精准的浏览器操作序列.

【思维引擎 (Chain of Thought)】
在输出 JSON 前, 请在 `thinking` 字段中按以下顺序思考:
1. 目标理解: 用一句话概括用户最终想完成什么.
2. 状态检查: 当前 URL 是什么? 是否需要跳转?
3. 元素识别: 我该点击或输入哪个元素? 它有什么独特的属性 (id, name, data-testid, aria-label)?
4. 预期变化: 操作后页面应该发生什么变化?

【动作规范】
1. 导航优先: 如果任务包含 URL 且当前不在该页面, Step 1 必须是 `navigate`.
2. 属性优先: 在操作元素时, 优先选择具备稳定属性 (如 id, data-testid) 的元素.
3. 参数嵌套: 严禁展平参数. 必须使用 `{"click": {"index": 1}}` 这种结构.
4. 耐心等待: 在执行点击 (尤其是提交/搜索按钮) 后, 页面加载需要时间. 如果状态未变, 请先使用 `wait` 动作等待 (例如 `{"wait": {"seconds": 3}}`), 绝不要立即重复之前的操作或重新 `navigate`.
5. 完成确认: 只有当确定所有步骤已完成且页面处于预期状态时, 才调用 `done` 动作 (例如 `{"done": {"text": "任务完成"}}`).

【输出示例】
{
  "thinking": "用户想要登录. 当前在空白页, 我需要先 navigate 到登录页. 然后识别账号输入框并 input.",
  "action": [
    { "navigate": { "url": "http://localhost:5173/login" } }
  ]
}
""",
            )

            # 3.3 执行 Agent
            logger.info(f"AgentService: Starting task | model={db_model.name} | task={task[:80]}...")
            agent_history = await agent.run(max_steps=max_steps)
            logger.info(f"AgentService: Task completed in {time.time() - start_time:.1f}s")
            
        except Exception as e:
            logger.error(f"AgentService: Execution failed at stage: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            errors.append(str(e))
        finally:
            # 确保浏览器关闭 (v0.11+ 使用 stop 而非 close)
            if browser:
                try:
                    logger.info("AgentService: Stopping browser...")
                    await browser.stop()
                except Exception as be:
                    logger.warning(f"AgentService: Failed to stop browser: {be}")

        # 5. 提取步骤
        steps = self._extract_steps_from_history(agent_history)
        
        # 6. 绑定已有项目资产
        if project_id and steps:
            from app.services.ai_service import ai_service
            project_memory = await ai_service.load_project_memory(db, project_id)
            if project_memory:
                steps = ai_service.bind_steps_to_library(steps, project_memory)

        execution_time = time.time() - start_time
        # AgentHistoryList 有 __len__ 方法
        total_steps = len(agent_history) if agent_history else 0

        return {
            "success": len(errors) == 0 and len(steps) > 0,
            "message": f"Agent 执行完成,共识别 {len(steps)} 个有效步骤(耗时 {execution_time:.1f}s)" if not errors else f"执行遇到问题: {'; '.join(errors)}",
            "steps": steps,
            "execution_time": round(execution_time, 2),
            "total_agent_steps": total_steps,
            "errors": errors,
        }

    async def execute_task_stream(
        self,
        db: AsyncSession,
        task: str,
        model_id: Optional[str] = None,
        headless: bool = True,
        max_steps: int = 20,
        use_vision: bool = False,
        project_id: Optional[int] = None,
    ):
        """
        流式执行 AI Agent 任务, 实时通过 yield 返回步骤
        """
        from app.services.ai_model_service import ai_model_service
        from app.services.ai_service import ai_service
        import asyncio

        project_memory = None
        if project_id:
            project_memory = await ai_service.load_project_memory(db, project_id)

        db_model = None
        if model_id and str(model_id).isdigit():
            db_model = await ai_model_service.get(db, int(model_id))
        if not db_model:
            db_model = await ai_model_service.get_default(db)

        if not db_model or not db_model.is_active:
            yield {"type": "error", "message": "未找到可用的 AI 模型配置"}
            return

        is_deepseek = db_model and "deepseek" in (db_model.model_identifier or "").lower()
        try:
            llm = self._build_llm(db_model)
        except Exception as e:
            yield {"type": "error", "message": f"LLM 初始化失败: {str(e)}"}
            return

        browser = None
        try:
            logger.info(f"AgentService Stream: Initializing browser (headless={headless})...")
            browser = Browser(headless=headless, args=["--incognito"])
            await browser.start()

            queue = asyncio.Queue()

            # 记录上一个发送的步骤,用于实时去重
            last_step_data = None

            async def step_callback(state, agent_output, step_number):
                nonlocal last_step_data
                if agent_output and agent_output.action:
                    # state 是 BrowserStateSummary,在 v0.11+ 中 selector_map 在 dom_state 下
                    selector_map = None
                    if hasattr(state, 'dom_state') and hasattr(state.dom_state, 'selector_map'):
                        selector_map = state.dom_state.selector_map
                    
                    for action_model in agent_output.action:
                        step = self._action_to_platform_step(action_model, selector_map)
                        if step:
                            # 实时去重逻辑:如果当前步骤与上一步完全一致,则跳过
                            current_identity = self._build_step_identity(step, action_model)
                            if last_step_data == current_identity:
                                logger.info(f"AgentService Stream: Skipping duplicate step | {step['action']}")
                                continue

                            last_step_data = current_identity
                            
                            # Bind immediately
                            if project_memory:
                                step = ai_service.bind_steps_to_library([step], project_memory)[0]
                                
                            logger.info(f"AgentService Stream: Yielding step {step_number} | {step['action']}")
                            await queue.put({"type": "step", "data": step, "step_number": step_number})

            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                use_vision=use_vision,
                register_new_step_callback=step_callback,
                use_thinking=True if is_deepseek else False,  # DeepSeek 开启思维过程以提升 JSON 稳定性
                max_actions_per_step=10,  # 允许每步执行更多动作,减少轮换次数
                extend_system_message="""
你是一个具备高度推理能力的 UI 自动化专家. 你的目标是将用户的自然语言意图转化为精准的浏览器操作序列.

【思维引擎 (Chain of Thought)】
在输出 JSON 前, 请在 `thinking` 字段中按以下顺序思考:
1. 目标理解: 用户想完成什么?
2. 状态检查: 是否需要 navigate?
3. 元素识别: 优先使用稳定属性 (data-testid, aria-label, id).
4. 完成确认: 任务是否已彻底完成? (如完成, 使用 `{"done": {"text": "成功"}}`)

【动作规范】
1. 导航优先: 任务包含 URL 时, Step 1 必须是 `navigate`.
2. 参数嵌套: 严禁展平参数. 正确结构: `{"click": {"index": 1}}`.
3. 耐心等待: 点击按钮后如页面未变化, 优先使用 `wait` 等待 (例如 `{"wait": {"seconds": 3}}`), 严禁立即重复相同操作.
4. 稳定性: 避免产生重复或无效的中间步骤.

【输出示例】
{
  "thinking": "用户想要登录. 第一步先跳转到目标 URL.",
  "action": [
    { "navigate": { "url": "http://localhost:5173/login" } }
  ]
}
""",
            )

            # 在后台运行 agent.run()
            task_execution = asyncio.create_task(agent.run(max_steps=max_steps))
            
            # 循环从队列中获取结果并 yield
            while not task_execution.done() or not queue.empty():
                try:
                    # 等待队列中的新步骤
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)  # 缩短等待时间
                    yield item
                except asyncio.TimeoutError:
                    continue
            
            # 确认任务无异常
            history = await task_execution
            # 提取已验证的历史步骤 (包含真实的 ActionResult 数据)
            final_steps = self._extract_steps_from_history(history)
            if project_memory and final_steps:
                final_steps = ai_service.bind_steps_to_library(final_steps, project_memory)
            yield {"type": "done", "total_steps": len(final_steps), "final_steps": final_steps}

        except Exception as e:
            logger.error(f"AgentService Stream Error: {e}")
            yield {"type": "error", "message": str(e)}
        finally:
            if browser:
                try:
                    await browser.stop()
                except:
                    pass

    # Actions that require a target selector to execute.
    # Steps without a resolved selector will rely on the runner's multi-strategy fallback chain
    # (semantic healing → visual matching) instead of failing immediately.
    _INTERACTIVE_ACTIONS = {"click", "fill", "select", "hover", "press"}

    def _action_to_platform_step(self, action_model, selector_map=None, interacted_elements=None, result_content=None) -> Optional[Dict[str, Any]]:
        """
        将单条 ActionModel 转换为平台标准 Step 格式
        selector_map: 用于实时回调 (BrowserStateSummary)
        interacted_elements: 用于历史提取 (BrowserStateHistory)
        result_content: 动作执行结果 (例如提取到的文本)
        """
        ACTION_MAP = {
            'goto': ['go_to_url', 'navigate', 'navigate_to', 'open_url'],
            'fill': ['input_text', 'type_text', 'fill_element', 'fill', 'enter_text'],
            'click': ['click_element', 'click', 'click_button', 'click_link'],
            'wait': ['wait', 'sleep', 'wait_for_load', 'wait_ms'],
            'scroll': ['scroll_down', 'scroll_up', 'scroll_to_element', 'scroll'],
            'get_text': ['extract_content', 'get_element_text', 'extract', 'read_text'],
            'hover': ['hover_element', 'hover'],
            'select': ['select_dropdown_option', 'select_option', 'select'],
            'press': ['press_key', 'send_keys', 'press'],
        }
        NAME_TO_PLATFORM = {}
        for platform_name, aliases in ACTION_MAP.items():
            for alias in aliases:
                NAME_TO_PLATFORM[alias] = platform_name

        try:
            action_dict = action_model.model_dump()
            # 排除掉思考等非动作字段
            raw_action_name = next((k for k in action_dict.keys() if k not in ['index', 'thought']), None)
            if not raw_action_name:
                return None
            
            params = action_dict[raw_action_name]
            platform_action = NAME_TO_PLATFORM.get(raw_action_name, raw_action_name)
            
            # 排除 'done' 动作为测试步骤
            if platform_action == 'done':
                return None
            
            target = ""
            value = ""
            
            if isinstance(params, dict):
                # 提取 Value 相关字段
                value = params.get('url') or params.get('text') or params.get('value') or \
                        params.get('content') or params.get('key') or ""
                
                # 特殊处理 scroll
                if platform_action == 'scroll' and not value:
                    if 'amount' in params:
                        value = str(params['amount'])
                    elif raw_action_name == 'scroll_down':
                        value = "500"
                    elif raw_action_name == 'scroll_up':
                        value = "-500"

                idx = params.get('index')
                
                # 情况 A:有实时 selector_map
                if idx is not None and selector_map:
                    element = selector_map.get(idx)
                    if element:
                        target = getattr(element, 'css_selector', None) or \
                                 getattr(element, 'xpath', None) or \
                                 f"xpath=//node()[@highlight_index={idx}]"
                # 情况 B:有历史 interacted_elements
                elif idx is not None and interacted_elements:
                    for el in interacted_elements:
                        if not el:
                            continue
                        if idx != getattr(el, 'highlight_index', None):
                            continue
                        
                        # 尝试生成更稳定的属性 XPath (Healing), 否则回退到 structural XPath
                        attrs = getattr(el, 'attributes', {}) or {}
                        tag = getattr(el, 'node_name', getattr(el, 'tag_name', '*'))
                        text = getattr(el, 'node_value', getattr(el, 'text', ''))
                        target = self._build_stable_xpath(tag, attrs, text) or \
                                 getattr(el, 'x_path', None) or getattr(el, 'xpath', None) or ""
                        if target:
                            break
            elif isinstance(params, str):
                value = params
            
            if platform_action == 'wait' and not value:
                value = "1000"
            
            # 如果是提取类动作,优先使用 ActionResult 中的内容
            if platform_action == 'get_text' and result_content:
                value = result_content

            # For interactive actions without a resolved selector, keep target empty.
            # The runner will use multi-strategy fallback (semantic healing → visual matching).

            # 生成更友好的中文描述
            desc = ""
            if platform_action == 'goto':
                desc = f"访问地址: {value}"
            elif platform_action == 'click':
                desc = f"点击元素: {target or '当前焦点'}"
            elif platform_action == 'fill':
                desc = f"输入内容 '{value}' 到: {target or '当前框'}"
            elif platform_action == 'wait':
                desc = f"等待 {value}ms"
            elif platform_action == 'scroll':
                desc = f"滚动页面: {value} 像素"
            elif platform_action == 'get_text':
                desc = f"提取文本 {target or '当前元素'}: {value or '正在提取...'}"
            elif platform_action == 'hover':
                desc = f"鼠标悬停在: {target}"
            elif platform_action == 'press':
                desc = f"按键: {value}"
            else:
                desc = f"执行 {platform_action} {target} {value}".strip()

            # Generate multi-strategy independent locator chain.
            # Each strategy uses a completely different mechanism to locate the element,
            # so they fail independently rather than cascading.
            locator_chain = None
            if target and isinstance(params, dict) and (selector_map or interacted_elements):
                element = None
                idx = params.get('index')
                if idx is not None and selector_map:
                    element = selector_map.get(idx)
                elif idx is not None and interacted_elements:
                    for el in interacted_elements:
                        if el and idx == getattr(el, 'highlight_index', None):
                            element = el
                            break

                if element:
                    attrs = getattr(element, 'attributes', {}) or {}
                    tag = (getattr(element, 'node_name', '') or '').lower()
                    text = ""
                    if hasattr(element, 'get_meaningful_text_for_llm'):
                        text = (element.get_meaningful_text_for_llm() or "").strip()

                    strategy_role = self._build_role_selector(tag, attrs, text)
                    strategy_attr = self._build_stable_attr_selector(attrs)
                    strategy_text = self._build_text_selector(text)
                    strategy_label = self._build_label_selector(attrs)
                    strategy_xpath = self._build_stable_xpath(tag, attrs, text)

                    # Primary uses the most stable available strategy
                    primary = strategy_attr or str(target)
                    for attr in ['data-testid', 'data-test', 'data-qa', 'data-cy', 'aria-label', 'id', 'name']:
                        val = attrs.get(attr)
                        if val:
                            if attr == 'id':
                                primary = f"#{val}"
                            elif attr == 'aria-label':
                                primary = f"[aria-label=\"{str(val).replace('\"', '\\\"')}\"]"
                            else:
                                primary = f"[{attr}=\"{str(val).replace('\"', '\\\"')}\"]"
                            break

                    locator_chain = {
                        "strategy_role": strategy_role,
                        "strategy_attr": strategy_attr,
                        "strategy_text": strategy_text,
                        "strategy_label": strategy_label,
                        "strategy_xpath": strategy_xpath,
                        # Backward-compatible fields
                        "primary": primary,
                        "fallback_1": strategy_role or strategy_text,
                        "fallback_2": strategy_text or strategy_xpath,
                        "fallback_3": strategy_xpath,
                    }

            # If no complex chain was built, use the simple one
            if not locator_chain and target:
                locator_chain = {
                    "strategy_attr": str(target),
                    "strategy_role": None,
                    "strategy_text": None,
                    "strategy_label": None,
                    "strategy_xpath": None,
                    "primary": str(target),
                    "fallback_1": None,
                    "fallback_2": None,
                    "fallback_3": None,
                }

            return {
                "action": platform_action,
                "target": str(target),
                "value": str(value),
                "description": desc,
                "locator_chain": locator_chain,
            }
        except Exception as e:
            logger.warning(f"AgentService: Action conversion error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def _build_step_identity(self, step: Dict[str, Any], action_model: Any = None) -> Any:
        target = step.get('target')
        base_identity = (step.get('action'), target, step.get('value'))
        if target:
            return base_identity
        # For steps without a concrete selector, use description and action payload
        # to distinguish genuinely different actions
        if action_model is None:
            return (*base_identity, step.get('description'))
        try:
            action_payload = action_model.model_dump()
            normalized_payload = {
                key: value
                for key, value in action_payload.items()
                if key not in {'index', 'thought'}
            }
            return (*base_identity, json.dumps(normalized_payload, sort_keys=True, ensure_ascii=False))
        except Exception:
            return (*base_identity, step.get('description'))

    # ==========================================
    # Multi-Strategy Selector Builders
    # Each strategy is independent — failure of one doesn't cascade.
    # ==========================================

    @staticmethod
    def _build_role_selector(tag: str, attrs: dict, text: str) -> Optional[str]:
        """Build Playwright role-based semantic locator (e.g. role=button[name='Submit'])."""
        ROLE_MAP = {
            'button': 'button', 'a': 'link', 'textarea': 'textbox',
            'select': 'combobox', 'img': 'img', 'nav': 'navigation',
            'main': 'main', 'header': 'banner', 'footer': 'contentinfo',
            'form': 'form', 'table': 'table', 'li': 'listitem',
            'ul': 'list', 'ol': 'list',
            'h1': 'heading', 'h2': 'heading', 'h3': 'heading',
            'h4': 'heading', 'h5': 'heading', 'h6': 'heading',
        }
        role = ROLE_MAP.get(tag)
        if not role:
            input_type = attrs.get('type', 'text')
            if tag == 'input':
                role = {
                    'text': 'textbox', 'email': 'textbox', 'password': 'textbox',
                    'search': 'searchbox', 'checkbox': 'checkbox', 'radio': 'radio',
                    'submit': 'button', 'button': 'button', 'reset': 'button',
                }.get(input_type)
        if not role:
            role = attrs.get('role')
        if not role:
            return None

        name = attrs.get('aria-label') or attrs.get('name') or attrs.get('title') or text or ""
        name = str(name).replace('"', '\\"')[:80]
        if name:
            return f'role={role}[name="{name}"]'
        return f'role={role}'

    @staticmethod
    def _build_stable_attr_selector(attrs: dict) -> Optional[str]:
        """Build most stable attribute-based CSS selector."""
        for attr in ['data-testid', 'data-test', 'data-qa', 'data-cy', 'aria-label', 'id', 'name']:
            val = attrs.get(attr)
            if not val:
                continue
            if attr == 'id':
                return f'#{val}'
            safe_val = str(val).replace('"', '\\"')
            return f'[{attr}="{safe_val}"]'
        return None

    @staticmethod
    def _build_text_selector(text: str) -> Optional[str]:
        """Build text-based selector."""
        if not text or len(text) < 2:
            return None
        safe_text = text.replace('"', '\\"').strip()[:60]
        if safe_text:
            return f'text="{safe_text}"'
        return None

    @staticmethod
    def _build_label_selector(attrs: dict) -> Optional[str]:
        """Build label/placeholder selector for form inputs."""
        placeholder = attrs.get('placeholder')
        if placeholder:
            safe = str(placeholder).replace('"', '\\"')[:100]
            return f'[placeholder="{safe}"]'
        label = attrs.get('aria-label')
        if label:
            safe = str(label).replace('"', '\\"')[:100]
            return f'[aria-label="{safe}"]'
        title = attrs.get('title')
        if title:
            safe = str(title).replace('"', '\\"')[:100]
            return f'[title="{safe}"]'
        return None

    @staticmethod
    def _build_stable_xpath(tag: str, attrs: dict, text: str) -> Optional[str]:
        """Build a short, attribute-based relative XPath (not structural path)."""
        tag = tag or '*'
        for attr in ['data-testid', 'data-test', 'data-qa', 'data-cy', 'aria-label', 'id']:
            val = attrs.get(attr)
            if val:
                safe_val = str(val).replace("'", "\\'")
                return f"//{tag}[@{attr}='{safe_val}']"
        if text and len(text) < 60:
            safe_text = text.replace("'", "\\'")
            return f"//{tag}[contains(text(),'{safe_text}')]"
        name = attrs.get('name')
        if name:
            safe_name = str(name).replace("'", "\\'")
            return f"//{tag}[@name='{safe_name}']"
        return None

    def _extract_steps_from_history(self, history) -> List[Dict[str, Any]]:
        """
        重构后的历史提取.
        支持 Action-Result 配对,确保提取的内容不为空.
        """
        if not history or not hasattr(history, 'history'):
            return []

        steps = []
        last_identity = None

        try:
            for item in history.history:
                if not item.model_output or not item.model_output.action:
                    continue

                # 获取该轮次交互的元素列表
                interacted = getattr(item.state, 'interacted_element', None)
                # 获取该轮次的执行结果列表 (ActionResult)
                results = item.result or []

                # 配对 Action 与 Result
                for i, action_model in enumerate(item.model_output.action):
                    # ActionResult 列表索引与 Action 列表一一对应
                    result_content = None
                    if i < len(results):
                        # 如果该动作执行失败(有 error),则跳过该步骤,不计入测试用例
                        if results[i].error:
                            logger.info(f"AgentService: Skipping failed action {action_model}: {results[i].error}")
                            continue
                        result_content = results[i].extracted_content

                    step = self._action_to_platform_step(
                        action_model,
                        interacted_elements=interacted,
                        result_content=result_content
                    )

                    if step:
                        # 历史去重与噪声过滤
                        current_identity = self._build_step_identity(step, action_model)

                        # 1. 跳过连续重复的步骤
                        if last_identity == current_identity:
                            continue

                        # 2. 过滤掉内容为空的静默提取
                        if step['action'] == 'get_text' and not step['value']:
                            continue

                        steps.append(step)
                        last_identity = current_identity
        except Exception as e:
            logger.warning(f"AgentService: History extraction error: {e}")
        
        # 3. 步骤后处理:去除导航前的干扰步骤
        # 如果历史记录中包含跳转(navigate),则认为跳转之前的交互步骤都是无效的探索
        first_nav_idx = -1
        for i, step in enumerate(steps):
            if step['action'] == 'goto':
                first_nav_idx = i
                break
        
        if first_nav_idx > 0:
            logger.info(f"AgentService: Discarding {first_nav_idx} pre-navigation noise steps")
            steps = steps[first_nav_idx:]
            
        # 4. 去除完整的重复循环 (Restart Loops)
        # 如果模型多次尝试 navigate 到同一个连续的 URL，说明前面的尝试失败了，只保留最后一次尝试。
        cleaned_steps = []
        goto_seen = {} # url -> index in cleaned_steps
        last_goto_url = None
        
        for step in steps:
            if step['action'] == 'goto':
                url = step.get('value', '')
                # 如果这个跳转和上一次记录的跳转不同，清空历史记录，这意味着用户真的想要去新的页面
                if last_goto_url and url != last_goto_url:
                    goto_seen.clear()
                    
                if url in goto_seen:
                    # 遇到了连续的相同跳转，说明是重试循环，截断之前的尝试
                    truncate_idx = goto_seen[url]
                    logger.info(f"AgentService: Truncating loop starting at step {truncate_idx} for url {url}")
                    cleaned_steps = cleaned_steps[:truncate_idx]
                
                goto_seen[url] = len(cleaned_steps)
                last_goto_url = url
                
            cleaned_steps.append(step)
            
        return cleaned_steps


# 全局实例
agent_service = AgentService()
