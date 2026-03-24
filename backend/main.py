"""
AI审计抽凭助手 - FastAPI后端入口
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import projects, vouchers, sampling, ai, auth, files, tasks, papers, audit_trail

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()

    # 打印AI配置信息
    logger.info("=" * 50)
    logger.info("AI审计抽凭助手 启动中...")
    logger.info(f"AI提供商: {settings.AI_PROVIDER}")
    logger.info(f"默认模型: {settings.AI_DEFAULT_MODEL}")
    logger.info(f"可用模型: {settings.get_available_models()}")
    logger.info(f"温度参数: {settings.AI_TEMPERATURE}")
    logger.info(f"最大Token: {settings.AI_MAX_TOKENS}")
    if settings.QWEN_API_KEY:
        logger.info("通义千问 API Key: 已配置")
    else:
        logger.info("通义千问 API Key: 未配置")
    logger.info("=" * 50)

    yield
    # 关闭时清理资源
    close_db()


app = FastAPI(
    title="AI审计抽凭助手",
    description="基于大语言模型的智能审计抽凭系统API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
app.include_router(vouchers.router, prefix="/api", tags=["凭证管理"])
app.include_router(sampling.router, prefix="/api", tags=["智能抽样"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI服务"])
app.include_router(files.router, prefix="/api/files", tags=["文件服务"])
app.include_router(tasks.router, prefix="/api", tags=["任务管理"])
app.include_router(papers.router, prefix="/api", tags=["工作底稿"])
app.include_router(audit_trail.router, prefix="/api", tags=["审计轨迹"])


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=False,  # 禁用reload以避免DuckDB多进程冲突
    )