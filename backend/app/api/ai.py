"""
AI服务API
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from app.core.database import get_db_cursor
from app.core.config import settings
from app.services.llm_service import LLMConfig, LLMFactory, llm_service
from app.services.ai_sampling_service import (
    risk_analyzer, intelligent_sampler,
    voucher_understanding_service
)
from app.services.embedding_service import semantic_search_service

router = APIRouter()


# ==================== 数据模型 ====================

class AIAnalyzeRequest(BaseModel):
    """AI分析请求"""
    project_id: str = Field(..., description="项目ID")
    voucher_ids: Optional[List[str]] = Field(None, description="凭证ID列表，为空则分析前100张")
    analysis_type: str = Field(default="risk", description="分析类型: risk/anomaly/summary")


class AIAnalyzeResponse(BaseModel):
    """AI分析响应"""
    analysis_id: str
    status: str
    total_analyzed: int
    results: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class AIIntelligentSampleRequest(BaseModel):
    """AI智能抽凭请求"""
    project_id: str = Field(..., description="项目ID")
    sample_size: int = Field(default=50, ge=1, le=500, description="期望样本量")
    focus_areas: Optional[List[str]] = Field(None, description="重点关注领域")


class IntelligentSampleResponse(BaseModel):
    """智能抽样响应"""
    project_id: str
    total_analyzed: int
    recommendations: List[Dict[str, Any]]
    risk_summary: Dict[str, int]
    strategy_suggestion: str


class ModelInfo(BaseModel):
    """模型信息"""
    provider: str
    model: str
    is_available: bool
    description: Optional[str] = None


class AIConfigUpdate(BaseModel):
    """AI配置更新"""
    provider: str = Field(..., description="提供商: ollama/qwen/ernie/zhipu")
    model: Optional[str] = Field(None, description="模型名称")
    api_key: Optional[str] = Field(None, description="API密钥(商业API需要)")
    base_url: Optional[str] = Field(None, description="API基础URL")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(2048, ge=1, le=32000, description="最大输出token")


class SemanticSearchRequest(BaseModel):
    """语义搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询")
    project_id: Optional[str] = Field(None, description="项目ID")
    top_k: int = Field(default=10, ge=1, le=50, description="返回数量")


class VoucherUnderstandingRequest(BaseModel):
    """凭证理解请求"""
    voucher_id: str = Field(..., description="凭证ID")
    include_ocr: bool = Field(default=True, description="是否包含OCR文本")


# ==================== API端点 ====================

@router.get("/models", response_model=List[ModelInfo])
async def list_models():
    """
    获取可用AI模型列表

    返回所有配置的模型及其可用状态
    """
    models = []

    # 从配置获取可用模型列表
    available_models = settings.get_available_models()

    for model_name in available_models:
        model_info = settings.get_model_info(model_name)
        models.append(ModelInfo(
            provider=settings.AI_PROVIDER,
            model=model_name,
            is_available=settings.QWEN_API_KEY is not None if settings.AI_PROVIDER == "qwen" else True,
            description=model_info.get("description", "")
        ))

    # 添加Ollama本地模型
    if settings.OLLAMA_BASE_URL:
        models.append(ModelInfo(
            provider="ollama",
            model=settings.OLLAMA_DEFAULT_MODEL,
            is_available=True,
            description="本地部署，支持离线使用"
        ))

    # 添加其他提供商（如果有API Key）
    if settings.ERNIE_API_KEY and settings.ERNIE_SECRET_KEY:
        models.extend([
            ModelInfo(
                provider="ernie",
                model="ernie-4.0-8k",
                is_available=True,
                description="百度文心一言4.0"
            ),
            ModelInfo(
                provider="ernie",
                model="ernie-3.5-8k",
                is_available=True,
                description="百度文心一言3.5"
            )
        ])

    if settings.ZHIPU_API_KEY:
        models.extend([
            ModelInfo(
                provider="zhipu",
                model="glm-4",
                is_available=True,
                description="智谱GLM-4"
            )
        ])

    return models


@router.put("/config")
async def update_ai_config(config: AIConfigUpdate):
    """
    配置AI模型

    更新当前使用的AI模型配置
    """
    try:
        new_config = LLMConfig(
            provider=config.provider,
            model=config.model or "qwen2.5:14b",
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=config.temperature or 0.7,
            max_tokens=config.max_tokens or 2048
        )

        # 验证配置
        adapter = LLMFactory.create(new_config)

        # 更新全局配置
        llm_service.set_config(new_config)

        return {
            "message": "配置更新成功",
            "provider": config.provider,
            "model": config.model
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)}")


@router.get("/status")
async def get_ai_status():
    """
    获取AI服务状态

    返回当前AI服务的可用状态
    """
    is_available = await llm_service.is_available()

    return {
        "provider": llm_service.config.provider,
        "model": llm_service.config.model,
        "is_available": is_available,
        "status": "可用" if is_available else "不可用"
    }


@router.post("/analyze", response_model=AIAnalyzeResponse)
async def analyze_vouchers(
    request: AIAnalyzeRequest,
    background_tasks: BackgroundTasks
):
    """
    分析凭证风险

    使用AI分析凭证的风险等级、异常点等
    """
    # 获取凭证数据
    with get_db_cursor() as cursor:
        # 验证项目
        cursor.execute("SELECT id FROM projects WHERE id = ?", [request.project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 获取凭证
        if request.voucher_ids:
            placeholders = ",".join(["?" for _ in request.voucher_ids])
            cursor.execute(
                f"""
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty
                FROM vouchers
                WHERE project_id = ? AND id IN ({placeholders})
                """,
                [request.project_id] + request.voucher_ids
            )
        else:
            cursor.execute(
                """
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty
                FROM vouchers
                WHERE project_id = ?
                ORDER BY amount DESC
                LIMIT 100
                """,
                [request.project_id]
            )

        rows = cursor.fetchall()

    if not rows:
        raise HTTPException(status_code=400, detail="没有凭证数据可供分析")

    # 构建凭证列表
    vouchers = [
        {
            "id": row[0],
            "voucher_no": row[1],
            "voucher_date": str(row[2]) if row[2] else None,
            "amount": float(row[3]) if row[3] else 0,
            "subject_code": row[4],
            "subject_name": row[5],
            "description": row[6],
            "counterparty": row[7]
        }
        for row in rows
    ]

    try:
        # 执行风险分析
        assessments = await risk_analyzer.batch_analyze(vouchers)

        # 构建结果
        results = [
            {
                "voucher_id": a.voucher_id,
                "risk_level": a.risk_level,
                "risk_score": a.risk_score,
                "risk_factors": a.risk_factors,
                "explanation": a.explanation,
                "confidence": a.confidence
            }
            for a in assessments
        ]

        return AIAnalyzeResponse(
            analysis_id=f"analysis_{request.project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status="completed",
            total_analyzed=len(vouchers),
            results=results
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/intelligent-sample", response_model=IntelligentSampleResponse)
async def intelligent_sample(request: AIIntelligentSampleRequest):
    """
    AI智能抽凭

    基于AI分析推荐最优抽样方案
    """
    # 验证项目
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [request.project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    try:
        # 执行智能抽样
        result = await intelligent_sampler.recommend_samples(
            project_id=request.project_id,
            sample_size=request.sample_size,
            focus_areas=request.focus_areas
        )

        return IntelligentSampleResponse(
            project_id=result.project_id,
            total_analyzed=result.total_analyzed,
            recommendations=[
                {
                    "voucher_id": r.voucher_id,
                    "priority": r.priority,
                    "reason": r.reason,
                    "risk_indicators": r.risk_indicators,
                    "recommended_action": r.recommended_action
                }
                for r in result.recommendations
            ],
            risk_summary=result.risk_summary,
            strategy_suggestion=result.strategy_suggestion
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能抽样失败: {str(e)}")


@router.post("/describe-voucher")
async def describe_voucher(request: VoucherUnderstandingRequest):
    """
    AI理解凭证内容

    分析凭证的业务类型、会计分录、风险点等
    """
    # 获取凭证数据
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, voucher_no, voucher_date, amount,
                   subject_code, subject_name, description, counterparty
            FROM vouchers
            WHERE id = ?
            """,
            [request.voucher_id]
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="凭证不存在")

        voucher = {
            "id": row[0],
            "voucher_no": row[1],
            "voucher_date": str(row[2]) if row[2] else None,
            "amount": float(row[3]) if row[3] else 0,
            "subject_code": row[4],
            "subject_name": row[5],
            "description": row[6],
            "counterparty": row[7]
        }

        # 获取OCR文本
        ocr_text = None
        if request.include_ocr:
            cursor.execute(
                "SELECT raw_text FROM voucher_ocr_results WHERE voucher_id = ?",
                [request.voucher_id]
            )
            ocr_row = cursor.fetchone()
            if ocr_row and ocr_row[0]:
                try:
                    raw_text = json.loads(ocr_row[0])
                    ocr_text = " ".join([t.get("text", "") for t in raw_text])
                except:
                    ocr_text = ocr_row[0]

    try:
        # 执行理解
        result = await voucher_understanding_service.understand_voucher(
            voucher=voucher,
            ocr_text=ocr_text
        )

        return {
            "voucher_id": request.voucher_id,
            "voucher": voucher,
            "understanding": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"理解失败: {str(e)}")


@router.post("/semantic-search")
async def semantic_search(request: SemanticSearchRequest):
    """
    语义搜索凭证

    基于自然语言查询搜索相关凭证
    """
    try:
        results = await semantic_search_service.search(
            query=request.query,
            project_id=request.project_id,
            top_k=request.top_k
        )

        return {
            "query": request.query,
            "total": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/projects/{project_id}/build-index")
async def build_semantic_index(project_id: str, background_tasks: BackgroundTasks):
    """
    为项目构建语义索引

    在后台为项目的所有凭证构建语义索引
    """
    # 验证项目
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 获取凭证数量
        cursor.execute("SELECT COUNT(*) FROM vouchers WHERE project_id = ?", [project_id])
        count = cursor.fetchone()[0]

    if count == 0:
        raise HTTPException(status_code=400, detail="项目中没有凭证数据")

    # 添加后台任务
    background_tasks.add_task(
        _build_index_task,
        project_id
    )

    return {
        "message": "索引构建任务已启动",
        "project_id": project_id,
        "voucher_count": count
    }


async def _build_index_task(project_id: str):
    """后台构建索引任务"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, voucher_no, voucher_date, amount,
                   subject_code, subject_name, description, counterparty
            FROM vouchers
            WHERE project_id = ?
            """,
            [project_id]
        )
        rows = cursor.fetchall()

        vouchers = [
            {
                "id": row[0],
                "voucher_no": row[1],
                "voucher_date": str(row[2]) if row[2] else None,
                "amount": float(row[3]) if row[3] else 0,
                "subject_code": row[4],
                "subject_name": row[5],
                "description": row[6],
                "counterparty": row[7]
            }
            for row in rows
        ]

    # 批量构建索引
    await semantic_search_service.batch_index_vouchers(vouchers)