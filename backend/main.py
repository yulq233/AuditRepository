"""
AI审计抽凭助手 - FastAPI后端入口
"""
import logging
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import init_db, close_db, get_db_cursor
from app.api import projects, vouchers, sampling, ai, auth, files, tasks, papers, audit_trail, crawler, compliance, risk

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 速率限制器配置
limiter = Limiter(key_func=get_remote_address)


def load_ai_configs_from_db():
    """从数据库加载AI模型配置"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT config_name, config_data
                FROM risk_configurations
                WHERE config_type = 'ai_model' AND is_active = TRUE
                """
            )
            rows = cursor.fetchall()

            for row in rows:
                purpose = row[0]
                try:
                    config_data = json.loads(row[1])
                except:
                    continue

                # 更新settings的场景化配置（包括API Key）
                # 注意：settings是lru_cache单例，需要修改其属性
                if purpose == "recognition":
                    settings.AI_RECOGNITION_PROVIDER = config_data.get("provider")
                    settings.AI_RECOGNITION_MODEL = config_data.get("model")
                    settings.AI_RECOGNITION_TEMPERATURE = config_data.get("temperature", 0.3)
                    # 加载用途级别的API Key（如果有）
                    if config_data.get("api_key"):
                        settings.AI_RECOGNITION_API_KEY = config_data.get("api_key")
                    if config_data.get("base_url"):
                        settings.AI_RECOGNITION_BASE_URL = config_data.get("base_url")
                    logger.info(f"加载识别用途配置: provider={config_data.get('provider')}, model={config_data.get('model')}")
                elif purpose == "risk_analysis":
                    settings.AI_RISK_ANALYSIS_PROVIDER = config_data.get("provider")
                    settings.AI_RISK_ANALYSIS_MODEL = config_data.get("model")
                    settings.AI_RISK_ANALYSIS_TEMPERATURE = config_data.get("temperature", 0.3)
                    # 加载用途级别的API Key（如果有）
                    if config_data.get("api_key"):
                        settings.AI_RISK_ANALYSIS_API_KEY = config_data.get("api_key")
                    if config_data.get("base_url"):
                        settings.AI_RISK_ANALYSIS_BASE_URL = config_data.get("base_url")
                    logger.info(f"加载风险分析用途配置: provider={config_data.get('provider')}, model={config_data.get('model')}")
                elif purpose == "general":
                    # 通用配置更新全局配置
                    if config_data.get("provider"):
                        settings.AI_PROVIDER = config_data.get("provider")
                    if config_data.get("model"):
                        settings.AI_DEFAULT_MODEL = config_data.get("model")
                    if config_data.get("temperature"):
                        settings.AI_TEMPERATURE = config_data.get("temperature")
                    # 加载用途级别的API Key（如果有）
                    if config_data.get("api_key"):
                        settings.AI_GENERAL_API_KEY = config_data.get("api_key")
                    if config_data.get("base_url"):
                        settings.AI_GENERAL_BASE_URL = config_data.get("base_url")
                    logger.info(f"加载通用配置: provider={config_data.get('provider')}, model={config_data.get('model')}")

            if rows:
                logger.info(f"从数据库加载了 {len(rows)} 个AI模型配置")
            else:
                logger.info("数据库中无AI模型配置，使用默认配置")

    except Exception as e:
        logger.warning(f"加载AI配置失败，使用默认配置: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()

    # 从数据库加载AI配置（覆盖默认配置）
    load_ai_configs_from_db()

    # 打印AI配置信息
    logger.info("=" * 50)
    logger.info("AI审计抽凭助手 启动中...")
    logger.info(f"AI提供商: {settings.AI_PROVIDER}")
    logger.info(f"默认模型: {settings.AI_DEFAULT_MODEL}")
    logger.info(f"可用模型: {settings.get_available_models()}")
    logger.info(f"温度参数: {settings.AI_TEMPERATURE}")
    logger.info(f"最大Token: {settings.AI_MAX_TOKENS}")

    # 打印场景化配置
    if settings.AI_RECOGNITION_PROVIDER:
        logger.info(f"识别用途: {settings.AI_RECOGNITION_PROVIDER}/{settings.AI_RECOGNITION_MODEL}")
    else:
        logger.info(f"识别用途: 使用默认配置")
    if settings.AI_RISK_ANALYSIS_PROVIDER:
        logger.info(f"风险分析用途: {settings.AI_RISK_ANALYSIS_PROVIDER}/{settings.AI_RISK_ANALYSIS_MODEL}")
    else:
        logger.info(f"风险分析用途: 使用默认配置")

    # 安全配置检查
    security_issues = settings.validate_security_config()
    if security_issues:
        logger.warning("=" * 50)
        logger.warning("安全配置警告:")
        for issue in security_issues:
            logger.warning(f"  - {issue}")
        logger.warning("请检查 .env 文件或环境变量配置")
        logger.warning("=" * 50)

    # 打印脱敏后的配置状态
    redacted = settings.get_redacted_config()
    logger.info(f"配置状态: SECRET_KEY={redacted['SECRET_KEY']}")
    logger.info(f"配置状态: QWEN_API_KEY={redacted['QWEN_API_KEY']}")
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

# 添加速率限制
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(crawler.router, prefix="/api/crawler", tags=["爬虫服务"])
app.include_router(compliance.router, prefix="/api", tags=["合规检查"])
app.include_router(risk.router, prefix="/api/projects/{project_id}/risk", tags=["风险画像"])


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