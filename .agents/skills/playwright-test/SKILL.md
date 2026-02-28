---
name: playwright-test
description: 为本项目的 UI 自动化测试平台创建测试步骤和测试用例，理解平台内部的测试步骤数据结构、Runner 执行逻辑和 Playwright 操作类型。
---

# Playwright 测试用例创建规范

## 测试步骤数据结构

本平台使用 JSON 格式的步骤列表来描述测试用例。每个步骤的结构如下：

```python
# 步骤基本结构 (对应 backend/app/models/ 中的 Step 模型)
{
    "action": str,      # 动作类型 (见下方支持的动作列表)
    "selector": str,    # CSS/XPath 选择器 (对于需要元素的操作)
    "value": str,       # 输入值 (对于 fill、select 等操作)
    "description": str, # 步骤描述
    "wait_ms": int,     # 等待时间 (毫秒，可选)
    "screenshot": bool, # 是否截图 (可选)
}
```

## 支持的动作类型

| action | 说明 | 必需字段 |
|--------|------|----------|
| `goto` | 跳转到 URL | `value` (URL) |
| `click` | 点击元素 | `selector` |
| `fill` | 填写输入框 | `selector`, `value` |
| `select` | 选择下拉选项 | `selector`, `value` |
| `wait` | 等待指定时间 | `wait_ms` |
| `wait_for_selector` | 等待元素出现 | `selector` |
| `assert_text` | 断言文本内容 | `selector`, `value` |
| `assert_visible` | 断言元素可见 | `selector` |
| `screenshot` | 截图 | _(无必需字段)_ |
| `hover` | 悬停元素 | `selector` |
| `press` | 键盘按键 | `selector`, `value` (键名如 `Enter`) |

## 选择器最佳实践

优先级从高到低：

```python
# 1. 最优: 语义化属性
"[data-testid='login-btn']"
"[aria-label='提交']"

# 2. 次优: 表单属性
"#username"
"[name='password']"
"[type='submit']"

# 3. 可用: 文本内容
"text=登录"
"button:has-text('确认')"

# 4. 最后: CSS 类名/层级 (避免使用，脆弱)
".login-form .submit-btn"
```

## 与 runner.py 的交互方式

`backend/app/services/runner.py` 负责执行测试步骤。当在平台内创建测试用例时：

1. **通过 API 创建**: `POST /api/v1/cases/` 提交步骤列表
2. **通过 AI 生成**: `POST /api/v1/ai/generate` 用自然语言描述，系统自动解析为步骤
3. **通过录制**: 使用录制功能捕获浏览器操作

## 示例测试用例

### 登录测试

```json
[
    {"action": "goto", "value": "http://localhost:5173", "description": "打开应用"},
    {"action": "wait_for_selector", "selector": "#username", "description": "等待登录表单"},
    {"action": "fill", "selector": "#username", "value": "admin", "description": "输入用户名"},
    {"action": "fill", "selector": "#password", "value": "password123", "description": "输入密码"},
    {"action": "click", "selector": "[type='submit']", "description": "点击登录"},
    {"action": "wait_for_selector", "selector": ".dashboard", "description": "等待仪表板加载"},
    {"action": "assert_visible", "selector": ".dashboard", "description": "验证登录成功"},
    {"action": "screenshot", "description": "截图记录"}
]
```

### 搜索功能测试

```json
[
    {"action": "goto", "value": "https://www.baidu.com", "description": "打开百度"},
    {"action": "fill", "selector": "#kw", "value": "Python Playwright", "description": "输入搜索词"},
    {"action": "press", "selector": "#kw", "value": "Enter", "description": "按回车搜索"},
    {"action": "wait_for_selector", "selector": "#content_left", "description": "等待结果"},
    {"action": "assert_text", "selector": "h1", "value": "Python Playwright", "description": "验证结果标题"},
    {"action": "screenshot", "description": "搜索结果截图"}
]
```

## AI 生成提示词技巧

使用 AI 生成时，使用英文更准确，动作词应清晰：

- ✅ `"Open http://localhost:5173 and click the Login button"`
- ✅ `"Fill in username field with 'admin', password with '123456', then click Submit"`
- ✅ `"Wait for the dashboard to appear and take a screenshot"`
- ❌ `"测试一下登录功能"` (太模糊)

## 调试技巧

如果测试失败，检查：
1. 选择器是否正确 - 在浏览器 DevTools 中验证
2. 是否需要增加 `wait_for_selector` 步骤等待元素加载
3. 查看 `allure-results/` 目录中的截图和日志
4. 后端日志文件: `backend/backend_proper.log`
