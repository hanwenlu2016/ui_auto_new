"""
UI 自动化测试平台 - 主应用入口

本模块是 FastAPI 应用的主入口，负责：
1. 初始化 FastAPI 应用实例
2. 配置 CORS 中间件
3. 注册 API 路由
4. 挂载静态文件服务（Allure 报告）
5. 初始化全局日志系统
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# 初始化全局日志系统
from app.core.logger import setup_logger, logger
setup_logger()

# 创建 FastAPI 应用实例
app = FastAPI(title="UI Automation Platform API")

# CORS 配置 - 允许前端跨域访问
origins = [
    "http://localhost:5173",  # Vite 默认端口
    "http://localhost:3000",  # 备用开发端口
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """
    根路径健康检查接口
    
    Returns:
        dict: 包含欢迎消息的字典
    """
    return {"message": "Welcome to UI Automation Platform API"}

# 导入并注册 API 路由
from app.api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")

# 挂载静态文件服务 - 用于提供 Allure 测试报告
# 计算 backend 根目录路径（main.py 位于 backend/app/main.py）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
reports_dir = os.path.join(BASE_DIR, "allure-reports")
os.makedirs(reports_dir, exist_ok=True)
app.mount("/reports", StaticFiles(directory=reports_dir), name="reports")

logger.info("UI Automation Platform API started successfully")
