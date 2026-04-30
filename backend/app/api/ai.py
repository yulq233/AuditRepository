"""
AI服务API
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db_cursor
from app.core.config import settings
from app.core.auth import get_current_user, UserInDB
from app.services.llm_service import LLMConfig, LLMFactory, llm_service
from app.services.ai_sampling_service import (
    risk_analyzer, intelligent_sampler,
    voucher_understanding_service
)
from app.services.voucher_risk_service import voucher_risk_service
from app.services.embedding_service import semantic_search_service
from app.services.ai_usage_service import ai_usage_query

logger = logging.getLogger(__name__)
router = APIRouter()

# AI接口速率限制器（较严格的限制）
limiter = Limiter(key_func=get_remote_address)


# ==================== 数据模型 ====================

class AIAnalyzeRequest(BaseModel):
    """AI分析请求"""
    project_id: str = Field(..., description="项目ID")
    voucher_ids: Optional[List[str]] = Field(None, description="凭证ID列表，为空则分析前100张")
    analysis_type: str = Field(default="risk", description="分析类型: risk/anomaly/summary/population_risk")
    population_stats: Optional[Dict[str, Any]] = Field(None, description="总体统计数据（用于population_risk分析）")


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
async def list_models(current_user: UserInDB = Depends(get_current_user)):
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
async def update_ai_config(config: AIConfigUpdate, current_user: UserInDB = Depends(get_current_user)):
    """
    配置AI模型

    更新当前使用的AI模型配置
    """
    adapter = None
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
        logger.error(f"AI配置更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="配置更新失败，请稍后重试")
    finally:
        # 确保关闭临时adapter
        if adapter:
            await adapter.close()


@router.get("/status")
async def get_ai_status(current_user: UserInDB = Depends(get_current_user)):
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


# ==================== 用途配置API ====================

class PurposeModelConfig(BaseModel):
    """用途模型配置"""
    purpose: str
    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    is_available: bool = True
    has_api_key: bool = True


class PurposeConfigUpdateRequest(BaseModel):
    """用途配置更新请求"""
    configs: List[PurposeModelConfig]


class PurposeModelTestRequest(BaseModel):
    """用途模型测试请求"""
    purpose: str


@router.get("/models/purposes")
async def get_models_by_purpose(current_user: UserInDB = Depends(get_current_user)):
    """
    获取各用途可用模型列表

    返回general、recognition、risk_analysis三种用途的模型列表
    """
    purposes = ["general", "recognition", "risk_analysis"]
    result = []

    for purpose in purposes:
        models = settings.get_models_for_purpose(purpose)
        model_list = []

        for model_name in models:
            model_info = settings.get_model_info(model_name)
            # 获取该用途的配置
            config = settings.get_ai_config_for_purpose(purpose)

            model_list.append({
                "provider": config["provider"],
                "model": model_name,
                "is_available": config["api_key"] is not None,
                "description": model_info.get("description", ""),
                "supports_image": model_info.get("supports_image", False),
                "category": model_info.get("category", "general")
            })

        # 当前使用的模型
        current_config = settings.get_ai_config_for_purpose(purpose)
        current_model = current_config["model"]

        result.append({
            "purpose": purpose,
            "current_model": current_model,
            "current_provider": current_config["provider"],
            "models": model_list
        })

    return result


@router.get("/config/purposes")
async def get_purpose_configs(current_user: UserInDB = Depends(get_current_user)):
    """
    获取各用途的配置详情
    """
    purposes = ["general", "recognition", "risk_analysis"]
    result = []

    for purpose in purposes:
        config = settings.get_ai_config_for_purpose(purpose)
        result.append({
            "purpose": purpose,
            "provider": config["provider"],
            "model": config["model"],
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
            "is_available": config["api_key"] is not None,
            "has_api_key": config["api_key"] is not None
        })

    return result


@router.put("/config/purposes")
async def update_purpose_configs(request: PurposeConfigUpdateRequest, current_user: UserInDB = Depends(get_current_user)):
    """
    更新用途配置

    注：此API仅更新内存中的配置，持久化需要修改.env文件
    """
    updated = []
    for cfg in request.configs:
        # 这里只做简单验证，实际配置更新需要修改settings或环境变量
        updated.append({
            "purpose": cfg.purpose,
            "model": cfg.model,
            "status": "updated"
        })

    return {"message": "配置已更新", "updated": updated}


@router.post("/test-purpose-model")
async def test_purpose_model(request: PurposeModelTestRequest, current_user: UserInDB = Depends(get_current_user)):
    """
    测试指定用途的模型

    发送简单测试请求验证模型是否可用
    """
    import time

    config = settings.get_ai_config_for_purpose(request.purpose)

    if not config["api_key"]:
        return {
            "success": False,
            "error": "未配置API Key",
            "elapsed_time": 0
        }

    adapter = None
    try:
        start_time = time.time()

        # 创建临时LLM配置
        test_config = LLMConfig(
            provider=config["provider"],
            model=config["model"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            temperature=0.1,
            max_tokens=50
        )

        adapter = LLMFactory.create(test_config)

        # 发送简单测试请求
        from app.services.llm_service import ChatMessage
        response = await adapter.chat([
            ChatMessage(role="user", content="你好，请回复'测试成功'")
        ])

        elapsed_time = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "model": config["model"],
            "response": response.content[:100] if response.content else "",
            "elapsed_time": elapsed_time
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed_time": 0
        }
    finally:
        # 确保关闭临时adapter，避免资源泄漏
        if adapter:
            await adapter.close()


@router.post("/analyze", response_model=AIAnalyzeResponse)
@limiter.limit("20/hour")  # 每小时最多20次分析请求
async def analyze_vouchers(
    http_request: Request,
    request: AIAnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    分析凭证风险

    使用AI分析凭证的风险等级、异常点等

    analysis_type:
    - risk: 单张凭证风险分析
    - population_risk: 总体风险分析（返回总体报告）
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
                       subject_code, subject_name, description, counterparty,
                       (SELECT COUNT(*) FROM voucher_attachments va WHERE va.voucher_id = v.id) as has_attachment,
                       (SELECT COUNT(*) FROM voucher_attachments va WHERE va.voucher_id = v.id AND va.recognition_result IS NOT NULL) as attachment_analyzed
                FROM vouchers v
                WHERE project_id = ? AND id IN ({placeholders})
                """,
                [request.project_id] + request.voucher_ids
            )
        else:
            cursor.execute(
                """
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty,
                       (SELECT COUNT(*) FROM voucher_attachments va WHERE va.voucher_id = v.id) as has_attachment,
                       (SELECT COUNT(*) FROM voucher_attachments va WHERE va.voucher_id = v.id AND va.recognition_result IS NOT NULL) as attachment_analyzed
                FROM vouchers v
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
            "counterparty": row[7],
            "has_attachment": row[8] > 0 if row[8] else False,
            "attachment_analyzed": row[9] > 0 if row[9] else False
        }
        for row in rows
    ]

    try:
        # 如果是总体风险分析类型，使用带附件识别的服务
        if request.analysis_type == "population_risk":
            # 使用voucher_risk_service进行AI分析（包含附件识别预处理）
            voucher_ids = [v["id"] for v in vouchers]
            filters = {"voucher_ids": voucher_ids} if voucher_ids else None
            risk_results = await voucher_risk_service.batch_analyze_vouchers(
                project_id=request.project_id,
                filters=filters,
                use_ai=True,
                save_results=False  # 第二步不保存结果，只返回分析报告
            )
            return _build_population_risk_response(request.project_id, vouchers, risk_results)

        # 普通风险分析
        assessments = await risk_analyzer.batch_analyze(vouchers)

        # 构建单张凭证分析结果
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
        logger.error(f"AI分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="分析失败，请稍后重试")


def _build_population_risk_response(
    project_id: str,
    vouchers: List[Dict[str, Any]],
    assessments: List[Any]
) -> AIAnalyzeResponse:
    """
    构建总体风险分析报告

    返回符合前端抽样向导期望的格式
    """
    total_count = len(vouchers)
    total_amount = sum(v.get("amount", 0) for v in vouchers)
    avg_amount = total_amount / total_count if total_count > 0 else 0

    # 统计风险分布
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0

    # 构建凭证风险详情列表
    voucher_risk_details = []

    for voucher, assessment in zip(vouchers, assessments):
        risk_level = assessment.risk_level
        if risk_level == "high":
            high_risk_count += 1
        elif risk_level == "medium":
            medium_risk_count += 1
        else:
            low_risk_count += 1

        # 使用原始风险因素描述（与执行抽样时保持一致）
        voucher_risk_details.append({
            "voucher_id": voucher["id"],
            "voucher_no": voucher.get("voucher_no", ""),
            "voucher_date": voucher.get("voucher_date", ""),
            "amount": voucher.get("amount", 0),
            "subject_name": voucher.get("subject_name", ""),
            "counterparty": voucher.get("counterparty", ""),
            "risk_level": risk_level,
            "risk_score": assessment.risk_score,
            "risk_factors": assessment.risk_factors,  # 使用原始风险因素描述
            "explanation": assessment.explanation,
            "ai_risk_explanation": getattr(assessment, 'ai_risk_explanation', ''),
            "ai_audit_attention": getattr(assessment, 'ai_audit_attention', []),
            "has_attachment": voucher.get("has_attachment", False),
            "attachment_analyzed": voucher.get("attachment_analyzed", False)
        })

    # 计算总体风险评分
    if high_risk_count > total_count * 0.2:
        overall_risk_level = "high"
        overall_risk_score = 70 + min(20, int(high_risk_count / total_count * 100))
    elif medium_risk_count > total_count * 0.3 or high_risk_count > 0:
        overall_risk_level = "medium"
        overall_risk_score = 50 + min(19, int((high_risk_count + medium_risk_count) / total_count * 50))
    else:
        overall_risk_level = "low"
        overall_risk_score = 30 + min(19, int(medium_risk_count / total_count * 50)) if medium_risk_count > 0 else 25

    # 收集主要风险因素（清理间隔号·）
    risk_factors_set = set()
    for assessment in assessments:
        for factor in assessment.risk_factors:
            # 清理间隔号·
            cleaned_factor = factor.replace('·', '').strip() if factor else factor
            if cleaned_factor:
                risk_factors_set.add(cleaned_factor)

    risk_factors = list(risk_factors_set)[:8]  # 取前8个

    # 生成分层抽样建议
    stratification_suggestion = _generate_stratification_suggestion(
        total_count, total_amount, avg_amount,
        high_risk_count, medium_risk_count, low_risk_count
    )

    # 生成分层配置
    stratification_config = {
        "layers": [
            {"name": "高风险层", "min_amount": avg_amount * 2, "max_amount": None, "sampling_rate": 1.0},
            {"name": "中风险层", "min_amount": avg_amount * 0.5, "max_amount": avg_amount * 2, "sampling_rate": 0.3},
            {"name": "低风险层", "min_amount": 0, "max_amount": avg_amount * 0.5, "sampling_rate": 0.1}
        ]
    }

    # 构建总体风险报告结果
    population_risk_result = {
        "overall_risk_score": overall_risk_score,
        "overall_risk_level": overall_risk_level,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "low_risk_count": low_risk_count,
        "high_risk_ratio": round(high_risk_count / total_count * 100) if total_count > 0 else 0,
        "medium_risk_ratio": round(medium_risk_count / total_count * 100) if total_count > 0 else 0,
        "low_risk_ratio": round(low_risk_count / total_count * 100) if total_count > 0 else 0,
        "risk_factors": risk_factors,
        "stratification_suggestion": stratification_suggestion,
        "stratification_config": stratification_config,
        "voucher_risk_details": voucher_risk_details
    }

    return AIAnalyzeResponse(
        analysis_id=f"population_risk_{project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        status="completed",
        total_analyzed=total_count,
        results=[population_risk_result]
    )


def _generate_stratification_suggestion(
    total_count: int,
    total_amount: float,
    avg_amount: float,
    high_risk: int,
    medium_risk: int,
    low_risk: int
) -> str:
    """生成分层抽样建议"""
    high_ratio = high_risk / total_count * 100 if total_count > 0 else 0
    medium_ratio = medium_risk / total_count * 100 if total_count > 0 else 0

    suggestion = f"本次分析了 {total_count} 张凭证，总金额 ¥{total_amount:,.2f}。\n"
    suggestion += f"风险分布：高风险 {high_risk} 张 ({high_ratio:.1f}%)，"
    suggestion += f"中风险 {medium_risk} 张 ({medium_ratio:.1f}%)，"
    suggestion += f"低风险 {low_risk} 张。\n\n"

    if high_ratio > 20:
        suggestion += "建议采用分层抽样：高风险凭证100%检查，中风险凭证50%抽样，低风险凭证10%抽样。"
    elif medium_ratio > 30:
        suggestion += f"建议采用分层抽样：大额凭证（>=¥{avg_amount*2:,.0f}）100%抽取，"
        suggestion += f"中额凭证 30%抽取，小额凭证 10%抽取。"
    else:
        suggestion += f"建议采用分层抽样：大额凭证（>=¥{avg_amount*2:,.0f}）50%抽取，"
        suggestion += f"中额凭证 25%抽取，小额凭证 10%抽取。"

    return suggestion


def _simplify_risk_factor(factor: str, max_length: int = 12) -> str:
    """
    简化风险因素标签，提取关键词

    Args:
        factor: 原始风险因素文本
        max_length: 最大字符长度

    Returns:
        简化后的风险因素标签
    """
    # 常见风险关键词映射（优先提取）
    keywords_map = {
        "时间敏感": ["月末", "年末", "季度末", "非工作日", "周日", "周六", "截止", "跨期"],
        "凭证编号异常": ["凭证编号", "编号异常", "年份不符"],
        "科目使用不当": ["科目使用", "科目不规范", "科目分类", "会计科目"],
        "交易对手存疑": ["交易对手", "关联方", "个体户", "个人"],
        "金额异常": ["金额为整数", "大额", "金额异常"],
        "摘要信息不足": ["摘要", "信息不足", "描述模糊"],
        "内控缺陷": ["内控", "控制缺陷", "系统缺陷"],
        "税务风险": ["税务", "个税", "增值税"],
        "虚构交易嫌疑": ["虚构", "套取资金", "利益输送"],
    }

    # 尝试匹配关键词
    for tag, keywords in keywords_map.items():
        for keyword in keywords:
            if keyword in factor:
                return tag

    # 如果没有匹配到关键词，提取冒号前的内容
    if "：" in factor:
        prefix = factor.split("：")[0]
        if len(prefix) <= max_length:
            return prefix

    if ":" in factor:
        prefix = factor.split(":")[0]
        if len(prefix) <= max_length:
            return prefix

    # 直接截取前 max_length 个字符
    if len(factor) <= max_length:
        return factor

    # 尝试在标点处截断
    for sep in ["，", "、", "；", " "]:
        if sep in factor[:max_length + 5]:
            return factor[:factor.index(sep)]

    return factor[:max_length] + "..."


@router.post("/intelligent-sample", response_model=IntelligentSampleResponse)
@limiter.limit("10/hour")  # 每小时最多10次智能抽样请求
async def intelligent_sample(
    http_request: Request,
    request: AIIntelligentSampleRequest,
    current_user: UserInDB = Depends(get_current_user)
):
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
        logger.error(f"智能抽样失败: {str(e)}")
        raise HTTPException(status_code=500, detail="智能抽样失败，请稍后重试")


@router.post("/describe-voucher")
@limiter.limit("30/hour")  # 每小时最多30次凭证理解请求
async def describe_voucher(
    http_request: Request,
    request: VoucherUnderstandingRequest,
    current_user: UserInDB = Depends(get_current_user)
):
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
        logger.error(f"凭证理解失败: {str(e)}")
        raise HTTPException(status_code=500, detail="凭证理解失败，请稍后重试")


@router.post("/semantic-search")
@limiter.limit("60/hour")  # 每小时最多60次语义搜索请求
async def semantic_search(
    http_request: Request,
    request: SemanticSearchRequest,
    current_user: UserInDB = Depends(get_current_user)
):
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
        logger.error(f"语义搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索失败，请稍后重试")


@router.post("/projects/{project_id}/build-index")
@limiter.limit("5/hour")  # 每小时最多5次索引构建请求（资源密集型）
async def build_semantic_index(
    http_request: Request,
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_user)
):
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


# ==================== 附件识别公共函数 ====================

async def recognize_voucher_attachments(project_id: str, voucher_ids: List[str]) -> Dict[str, str]:
    """
    获取凭证附件识别结果（公共函数，供其他模块调用）

    Args:
        project_id: 项目ID
        voucher_ids: 凭证ID列表

    Returns:
        Dict[str, str]: 附件识别内容字典，key为voucher_id，value为识别内容
    """
    if not voucher_ids:
        logger.warning("[附件识别] voucher_ids为空，返回空结果")
        return {}

    attachment_contents = {}

    with get_db_cursor() as cursor:
        placeholders = ",".join(["?" for _ in voucher_ids])

        # 从 voucher_attachments 表获取已有识别结果
        try:
            cursor.execute(
                f"""
                SELECT voucher_id, recognition_result
                FROM voucher_attachments
                WHERE voucher_id IN ({placeholders}) AND recognition_result IS NOT NULL
                """,
                voucher_ids
            )
            results = cursor.fetchall()
            logger.info(f"[附件识别] 已有识别结果数: {len(results)}")

            for row in results:
                voucher_id = row[0]
                recognition_result = row[1]
                if recognition_result:
                    try:
                        result_json = json.loads(recognition_result)
                        content_parts = []
                        if result_json.get("key_info"):
                            content_parts.append(f"内容摘要: {result_json['key_info']}")
                        if result_json.get("amount"):
                            content_parts.append(f"金额: {result_json['amount']}")
                        if result_json.get("counterparty"):
                            content_parts.append(f"交易对手: {result_json['counterparty']}")
                        if result_json.get("voucher_date"):
                            content_parts.append(f"日期: {result_json['voucher_date']}")
                        if result_json.get("description"):
                            content_parts.append(f"摘要: {result_json['description']}")

                        if content_parts:
                            attachment_contents[voucher_id] = "\n".join(content_parts)
                    except Exception as e:
                        logger.warning(f"[附件识别] 解析结果失败: {e}")

        except Exception as e:
            logger.error(f"[附件识别] 查询失败: {e}")

    logger.info(f"[附件识别] 返回内容数: {len(attachment_contents)}")
    return attachment_contents


# ==================== 用量统计API ====================

@router.get("/usage/summary")
async def get_usage_summary(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    provider: Optional[str] = Query(None, description="供应商过滤"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    获取AI用量统计汇总

    返回总调用次数、Token数、成功率等统计信息
    """
    try:
        summary = ai_usage_query.get_summary(
            start_date=start_date,
            end_date=end_date,
            provider=provider
        )
        return summary
    except Exception as e:
        logger.error(f"[用量统计] 查询失败: {e}")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/usage/daily")
async def get_daily_usage(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    days: int = Query(30, ge=1, le=365, description="查询天数"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    获取每日AI用量统计

    返回每日的调用次数、Token数、成功率等趋势数据
    """
    try:
        daily_data = ai_usage_query.get_daily_usage(
            start_date=start_date,
            end_date=end_date,
            days=days
        )
        return daily_data
    except Exception as e:
        logger.error(f"[每日用量] 查询失败: {e}")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/logs")
async def get_usage_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    provider: Optional[str] = Query(None, description="供应商过滤"),
    purpose: Optional[str] = Query(None, description="用途过滤"),
    status: Optional[str] = Query(None, description="状态过滤 (success/error)"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    获取AI调用日志列表

    返回详细的调用记录，支持分页和过滤
    """
    try:
        logs = ai_usage_query.get_logs(
            page=page,
            page_size=page_size,
            provider=provider,
            purpose=purpose,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        return logs
    except Exception as e:
        logger.error(f"[调用日志] 查询失败: {e}")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/logs/{log_id}")
async def get_log_detail(log_id: str, current_user: UserInDB = Depends(get_current_user)):
    """
    获取单条调用日志详情

    Args:
        log_id: 日志ID
    """
    try:
        log = ai_usage_query.get_log_detail(log_id)
        if not log:
            raise HTTPException(status_code=404, detail="日志不存在")
        return log
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[日志详情] 查询失败: {e}")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/providers")
async def get_ai_providers(current_user: UserInDB = Depends(get_current_user)):
    """
    获取AI供应商列表

    返回所有配置的供应商及其可用状态
    """
    providers = []

    # 通义千问
    qwen_models = settings.get_models_for_purpose("general")
    providers.append({
        "name": "qwen",
        "display_name": "通义千问",
        "is_available": settings.QWEN_API_KEY is not None,
        "api_key_configured": settings.QWEN_API_KEY is not None,
        "base_url": settings.QWEN_BASE_URL,
        "models": qwen_models
    })

    # 智谱GLM
    zhipu_models = []
    if settings.AI_PROVIDER == "zhipu" or settings.ZHIPU_API_KEY:
        zhipu_models = ["glm-4", "glm-4v", "glm-4v-flash"]
    providers.append({
        "name": "zhipu",
        "display_name": "智谱GLM",
        "is_available": settings.ZHIPU_API_KEY is not None,
        "api_key_configured": settings.ZHIPU_API_KEY is not None,
        "base_url": settings.ZHIPU_BASE_URL,
        "models": zhipu_models
    })

    # 百度文心
    ernie_models = []
    if settings.AI_PROVIDER == "ernie" or (settings.ERNIE_API_KEY and settings.ERNIE_SECRET_KEY):
        ernie_models = ["ernie-4.0-8k", "ernie-3.5-8k"]
    providers.append({
        "name": "ernie",
        "display_name": "百度文心",
        "is_available": settings.ERNIE_API_KEY is not None and settings.ERNIE_SECRET_KEY is not None,
        "api_key_configured": settings.ERNIE_API_KEY is not None,
        "base_url": "https://qianfan.baidubce.com/cms/compatible-mode/v1",
        "models": ernie_models
    })

    # Ollama本地模型
    ollama_models = [settings.OLLAMA_DEFAULT_MODEL] if settings.OLLAMA_DEFAULT_MODEL else []
    providers.append({
        "name": "ollama",
        "display_name": "Ollama本地",
        "is_available": True,  # 本地模型默认可用
        "api_key_configured": True,  # 本地模型不需要API Key
        "base_url": settings.OLLAMA_BASE_URL,
        "models": ollama_models
    })

    return providers