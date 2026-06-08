"""
FastAPI应用入口模块

创建和配置FastAPI应用实例，注册所有API路由，
配置CORS中间件以支持前端跨域访问。

路由结构：
- /api/game/* : 游戏核心API（初始化、行动执行、状态查询）
- /api/map/* : 地图数据API
- /api/ai/* : AI配置和决策API
- /api/save/* : 存档管理API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import game_router, map_router, ai_router, save_router

# 创建FastAPI应用实例
app = FastAPI(
    title="AI三国演义 API",
    description="基于因果沙盒的三国博弈叙事沙盒后端服务",
    version="0.1.0",
)

# 配置CORS中间件，允许前端跨域访问
# 开发环境允许所有来源，生产环境应限制具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 允许所有来源（开发环境）
    allow_credentials=False,    # 不允许携带凭证
    allow_methods=["*"],        # 允许所有HTTP方法
    allow_headers=["*"],        # 允许所有请求头
)

# 注册API路由，所有路由以/api为前缀
app.include_router(game_router, prefix="/api")   # 游戏核心路由
app.include_router(map_router, prefix="/api")    # 地图数据路由
app.include_router(ai_router, prefix="/api")     # AI配置和决策路由
app.include_router(save_router, prefix="/api")   # 存档管理路由


@app.get("/")
def root():
    """根路径，返回API基本信息。"""
    return {"name": "AI三国演义 API", "version": "0.1.0"}


@app.get("/health")
def health():
    """健康检查端点，用于监控服务是否正常运行。"""
    return {"status": "ok"}
