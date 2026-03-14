"""
Agent Service — v1.0 (browser-use Powered)

使用 browser-use 库实现 AI Agent 驱动的浏览器自动化执行。
Agent 能"看见"页面的 Accessibility Tree，实现 观察→推理→执行→验证 的闭环。

与 AIService 的区别：
- AIService: 纯 Prompt → LLM → JSON Steps (盲猜模式, 快速但不精准)
- AgentService: 自然语言 → Agent 打开浏览器执行 → 提取已验证的 Steps (精准模式)
"""
import time
import re
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

    核心能力：
    1. 接收自然语言任务描述
    2. 启动浏览器，Agent 实时观察页面 Accessibility Tree
    3. LLM 基于真实页面结构推理下一步
    4. Agent 执行操作并验证结果
    5. 提取已验证的 Steps 返回给平台
    """

    # ==========================================
    # 核心方法: 构建大模型驱动 Agent
    # ==========================================

    def _build_llm(self, model_config: Any):
        """
        根据数据库模型配置构建 LLM 实例。

        - DeepSeek → ChatDeepSeek (browser-use 原生支持)
        - 其他 OpenAI 兼容厂商 → ChatOpenAI (LangChain)
        """
        import json
        
        base_url = model_config.base_url or ""
        api_key = model_config.api_key
        model_name = model_config.model_identifier
        
        # 提取动态参数
        temperature = model_config.temperature if model_config.temperature is not None else 0.1
        max_tokens = model_config.max_tokens if model_config.max_tokens is not None else 8192
        
        # 提取额外 kwargs
        extra_kwargs = {}
        if hasattr(model_config, 'kwargs') and model_config.kwargs:
            try:
                extra_kwargs = json.loads(model_config.kwargs)
                if not isinstance(extra_kwargs, dict):
                    extra_kwargs = {}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse kwargs JSON for model {model_config.name}")

        # 根据模型标识符本身判断是否属于 DeepSeek 系列，而非强依赖域名（适应各种内部网关 / 第三方API代理转发）
        is_deepseek = "deepseek" in (model_name or "").lower()

        if is_deepseek:
            logger.info(f"AgentService: Using ChatDeepSeek for {model_config.name} (temp={temperature}, kwargs={extra_kwargs})")
            return ChatDeepSeek(
                base_url=base_url,
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
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
                max_tokens=max_tokens,
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
    ) -> Dict[str, Any]:
        """
        执行 AI Agent 任务。

        Args:
            db: 数据库会话
            task: 自然语言任务描述
            model_id: AI 模型 ID (可选，默认使用系统默认模型)
            headless: 是否无头模式
            max_steps: Agent 最大步骤数
            use_vision: 是否使用视觉模型 (消耗更多 Token)

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
                "message": "未找到可用的 AI 模型配置，请先在 AI 配置页面添加模型。",
                "steps": [],
                "execution_time": 0.0,
                "total_agent_steps": 0,
                "errors": ["No active AI model found"],
            }

        # 2. 构建 LLM
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
            logger.info(f"AgentService: Initializing browser (headless={headless})...")
            browser = Browser(headless=headless)
            await browser.start()
            
            # 3.2 创建 Agent
            logger.info("AgentService: Creating Agent instance...")
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                use_vision=use_vision,
                extend_system_message="""
你是一个 UI 自动化测试执行引擎。请严格按照用户意图执行浏览器操作。
注意事项：
1. 优先使用 data-testid、aria-label 等稳定属性定位元素
2. 操作前确认元素可见且可交互
3. 每一步都要验证结果是否符合预期
4. 遇到加载状态时适当等待
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

        execution_time = time.time() - start_time
        # AgentHistoryList 有 __len__ 方法
        total_steps = len(agent_history) if agent_history else 0

        return {
            "success": len(errors) == 0 and len(steps) > 0,
            "message": f"Agent 执行完成，共识别 {len(steps)} 个有效步骤（耗时 {execution_time:.1f}s）" if not errors else f"执行遇到问题: {'; '.join(errors)}",
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
    ):
        """
        流式执行 AI Agent 任务，实时通过 yield 返回步骤。
        """
        from app.services.ai_model_service import ai_model_service
        import asyncio

        db_model = None
        if model_id and str(model_id).isdigit():
            db_model = await ai_model_service.get(db, int(model_id))
        if not db_model:
            db_model = await ai_model_service.get_default(db)

        if not db_model or not db_model.is_active:
            yield {"type": "error", "message": "未找到可用的 AI 模型配置"}
            return

        try:
            llm = self._build_llm(db_model)
        except Exception as e:
            yield {"type": "error", "message": f"LLM 初始化失败: {str(e)}"}
            return

        browser = None
        try:
            logger.info(f"AgentService Stream: Initializing browser (headless={headless})...")
            browser = Browser(headless=headless)
            await browser.start()

            queue = asyncio.Queue()

            # 记录上一个发送的步骤，用于实时去重
            last_step_data = None

            async def step_callback(state, agent_output, step_number):
                nonlocal last_step_data
                if agent_output and agent_output.action:
                    # state 是 BrowserStateSummary，在 v0.11+ 中 selector_map 在 dom_state 下
                    selector_map = None
                    if hasattr(state, 'dom_state') and hasattr(state.dom_state, 'selector_map'):
                        selector_map = state.dom_state.selector_map
                    
                    for action_model in agent_output.action:
                        step = self._action_to_platform_step(action_model, selector_map)
                        if step:
                            # 实时去重逻辑：如果当前步骤与上一步完全一致，则跳过
                            current_identity = (step['action'], step['target'], step['value'])
                            if last_step_data == current_identity:
                                logger.info(f"AgentService Stream: Skipping duplicate step | {step['action']}")
                                continue
                            
                            last_step_data = current_identity
                            logger.info(f"AgentService Stream: Yielding step {step_number} | {step['action']}")
                            await queue.put({"type": "step", "data": step, "step_number": step_number})

            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                use_vision=use_vision,
                register_new_step_callback=step_callback,
                use_thinking=False,  # 禁用思维过程以提升速度
                max_actions_per_step=10,  # 允许每步执行更多动作，减少轮换次数
                extend_system_message="""
你是一个 UI 自动化测试执行引擎。请严格按照用户意图执行浏览器操作。
注意事项：
1. 优先使用 data-testid、aria-label 等稳定属性定位元素
2. 操作前确认元素可见且可交互
3. 每一步都要验证结果是否符合预期
4. 遇到加载状态时适当等待
5. 完成任务后直接调用 done
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

    def _action_to_platform_step(self, action_model, selector_map=None, interacted_elements=None, result_content=None) -> Optional[Dict[str, Any]]:
        """
        将单条 ActionModel 转换为平台标准 Step 格式。
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
                
                # 情况 A：有实时 selector_map
                if idx is not None and selector_map:
                    element = selector_map.get(idx)
                    if element:
                        target = getattr(element, 'css_selector', None) or \
                                 getattr(element, 'xpath', None) or \
                                 f"xpath=//node()[@highlight_index={idx}]"
                # 情况 B：有历史 interacted_elements
                elif idx is not None and interacted_elements:
                    for el in interacted_elements:
                        if el and hasattr(el, 'x_path'):
                            target = el.x_path
                            break
            elif isinstance(params, str):
                value = params
            
            if platform_action == 'wait' and not value:
                value = "1000"
            
            # 如果是提取类动作，优先使用 ActionResult 中的内容
            if platform_action == 'get_text' and result_content:
                value = result_content

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

            return {
                "action": platform_action,
                "target": str(target),
                "value": str(value),
                "description": desc,
            }
        except Exception as e:
            logger.warning(f"AgentService: Action conversion error: {e}")
            return None

    def _extract_steps_from_history(self, history) -> List[Dict[str, Any]]:
        """
        重构后的历史提取。
        支持 Action-Result 配对，确保提取的内容不为空。
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
                        result_content = results[i].extracted_content

                    step = self._action_to_platform_step(
                        action_model, 
                        interacted_elements=interacted,
                        result_content=result_content
                    )
                    
                    if step:
                        # 历史去重与噪声过滤
                        current_identity = (step['action'], step['target'], step['value'])
                        
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
        return steps


# 全局实例
agent_service = AgentService()
