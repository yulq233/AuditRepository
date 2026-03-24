"""
AI审计抽凭助手 - FastAPI后端入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import projects, vouchers, sampling, ai, auth, files, tasks, papers, audit_trail


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
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
        reload=True,
    )