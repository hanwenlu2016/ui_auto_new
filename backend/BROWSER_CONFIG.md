# 浏览器配置说明

## 配置文件位置
`backend/app/core/config.py`

## 配置项

### BROWSER_HEADLESS
- **类型**: bool
- **默认值**: True
- **说明**: 
  - `True`: 无头模式,浏览器不显示界面(推荐用于 CI/CD)
  - `False`: 有头模式,显示浏览器窗口(推荐用于本地调试)

### BROWSER_TYPE
- **类型**: str
- **默认值**: "chromium"
- **可选值**:
  - `"chromium"`: Chrome/Edge 浏览器
  - `"firefox"`: Firefox 浏览器
  - `"webkit"`: Safari 浏览器

## 使用方法

### 方法 1: 修改配置文件(全局默认)
编辑 `backend/app/core/config.py`:
```python
# Browser Configuration
BROWSER_HEADLESS: bool = False  # 改为 False 启用有头模式
BROWSER_TYPE: str = "firefox"   # 改为 firefox 使用火狐浏览器
```

### 方法 2: 环境变量(推荐)
创建 `.env` 文件:
```bash
BROWSER_HEADLESS=false
BROWSER_TYPE=firefox
```

### 方法 3: API 请求时指定(覆盖默认值)
```bash
curl -X POST "http://localhost:8000/api/v1/execution/cases/1/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "headless": false,
    "browser_type": "firefox"
  }'
```

## 优先级
API 请求参数 > 环境变量 > 配置文件默认值

## 注意事项
1. 修改配置文件后需要重启服务
2. 有头模式需要图形界面支持(不适用于无界面服务器)
3. Webkit 需要系统支持(macOS 最佳)
