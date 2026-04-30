"""
风险画像API
提供项目风险概览、多维分析、交易风险清单、配置管理等接口
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import logging
import json
import uuid
import random

logger = logging.getLogger(__name__)

from app.core.database import get_db_cursor, get_db
from app.services.risk_profile_service import (
    risk_profile_generator,
    RiskProfile,
    RiskFactor,
    RiskLevel
)
from app.services.voucher_risk_service import voucher_risk_service
from app.services.risk_config_service import risk_config_service
from app.core.auth import get_current_user, UserInDB

router = APIRouter()


# ==================== 响应模型 ====================

class RiskFactorResponse(BaseModel):
    """风险因素响应"""
    name: str
    weight: float
    score: float
    description: str


class RiskProfileResponse(BaseModel):
    """风险画像响应"""
    id: str
    project_id: str
    subject_code: str
    subject_name: str
    risk_level: str
    risk_score: float
    risk_factors: List[RiskFactorResponse]
    material_amount: float
    anomaly_score: float
    recommendation: str
    created_at: datetime


class ProjectRiskOverviewResponse(BaseModel):
    """项目风险概览响应"""
    id: str
    project_id: str
    overall_risk_score: float
    overall_risk_level: str
    dimension_scores: Dict[str, float]
    high_risk_subjects: List[Dict[str, Any]]
    risk_trend: List[Dict[str, Any]]
    generated_at: datetime


class CounterpartyRiskResponse(BaseModel):
    """交易对手风险响应"""
    id: str
    project_id: str
    counterparty_name: str
    total_amount: float
    transaction_count: int
    concentration_ratio: float
    is_related_party: bool
    is_new_customer: bool
    risk_score: float
    risk_level: str
    risk_factors: List[str]


class TimeRiskResponse(BaseModel):
    """时间维度风险响应"""
    id: str
    project_id: str
    period: str
    period_type: str
    total_amount: float
    transaction_count: int
    volatility_score: float
    period_end_concentration: float
    anomaly_indicators: List[str]


class TransactionRiskItem(BaseModel):
    """交易风险项"""
    id: str
    voucher_no: str
    voucher_date: Optional[str]
    amount: float
    subject_code: Optional[str]
    subject_name: Optional[str]
    description: Optional[str]
    counterparty: Optional[str]
    risk_score: float
    risk_level: str
    risk_tags: List[Dict[str, Any]]
    risk_factors: Optional[List[str]] = None  # 风险因素说明
    ai_analysis: Optional[Dict[str, Any]] = None  # AI分析结果


class TransactionListResponse(BaseModel):
    """交易风险列表响应"""
    items: List[TransactionRiskItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class RiskTagStatistics(BaseModel):
    """风险标签统计"""
    tag_code: str
    tag_name: str
    tag_category: str
    severity: str
    count: int


class BatchAddSamplingRequest(BaseModel):
    """批量加入抽样请求"""
    voucher_ids: List[str]
    reason: Optional[str] = "风险画像批量添加"


class BatchAddSamplingResponse(BaseModel):
    """批量加入抽样响应"""
    success: bool
    record_id: str
    added_count: int
    message: str


class UpdateWeightsRequest(BaseModel):
    """更新权重请求"""
    weights: Dict[str, float]


class UpdateThresholdsRequest(BaseModel):
    """更新阈值请求"""
    thresholds: Dict[str, int]


class ToggleRuleRequest(BaseModel):
    """切换规则请求"""
    enabled: bool


class SaveTemplateRequest(BaseModel):
    """保存模板请求"""
    template_name: str


class LoadTemplateRequest(BaseModel):
    """加载模板请求"""
    template_name: str


class LayeredSamplingResponse(BaseModel):
    """分层抽样响应"""
    layers: List[Dict[str, Any]]
    total_sample_size: int
    recommendation: str


# ==================== 项目风险概览 ====================

@router.get("/overview", response_model=ProjectRiskOverviewResponse)
async def get_project_risk_overview(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取项目整体风险概览"""
    overview = risk_profile_generator.get_project_overview(project_id)

    if not overview:
        # 如果不存在，自动生成
        overview = risk_profile_generator.generate_project_overview(project_id)

    return ProjectRiskOverviewResponse(
        id=overview.id,
        project_id=overview.project_id,
        overall_risk_score=overview.overall_risk_score,
        overall_risk_level=overview.overall_risk_level,
        dimension_scores=overview.dimension_scores,
        high_risk_subjects=overview.high_risk_subjects,
        risk_trend=overview.risk_trend,
        generated_at=overview.generated_at
    )


@router.post("/overview/generate", response_model=ProjectRiskOverviewResponse)
async def generate_project_risk_overview(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """生成项目风险概览（基于已有的科目画像）"""
    # 直接生成项目概览（不再重复生成科目画像，前端已单独调用）
    overview = risk_profile_generator.generate_project_overview(project_id)

    return ProjectRiskOverviewResponse(
        id=overview.id,
        project_id=overview.project_id,
        overall_risk_score=overview.overall_risk_score,
        overall_risk_level=overview.overall_risk_level,
        dimension_scores=overview.dimension_scores,
        high_risk_subjects=overview.high_risk_subjects,
        risk_trend=overview.risk_trend,
        generated_at=overview.generated_at
    )


@router.get("/trend")
async def get_risk_trend(
    project_id: str,
    periods: int = Query(default=6, ge=1, le=24),
    current_user: UserInDB = Depends(get_current_user)
):
    """获取风险趋势"""
    trend = risk_profile_generator._get_risk_trend(project_id, periods)
    return {"trend": trend}


# ==================== 多维风险分析 ====================

@router.get("/dimensions/counterparty", response_model=List[CounterpartyRiskResponse])
async def get_counterparty_risk_analysis(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取交易对手风险分析"""
    risks = risk_profile_generator.get_counterparty_risks(project_id)

    if not risks:
        risks = risk_profile_generator.assess_counterparty_risk(project_id)

    return [
        CounterpartyRiskResponse(
            id=r.id,
            project_id=r.project_id,
            counterparty_name=r.counterparty_name,
            total_amount=r.total_amount,
            transaction_count=r.transaction_count,
            concentration_ratio=r.concentration_ratio,
            is_related_party=r.is_related_party,
            is_new_customer=r.is_new_customer,
            risk_score=r.risk_score,
            risk_level=r.risk_level,
            risk_factors=r.risk_factors
        )
        for r in risks
    ]


@router.get("/dimensions/time", response_model=List[TimeRiskResponse])
async def get_time_risk_analysis(
    project_id: str,
    period_type: str = Query(default="monthly", regex="^(monthly|quarterly)$"),
    current_user: UserInDB = Depends(get_current_user)
):
    """获取时间维度风险分析"""
    analyses = risk_profile_generator.get_time_risk_analysis(project_id)

    if not analyses:
        analyses = risk_profile_generator.assess_time_risk(project_id, period_type)

    return [
        TimeRiskResponse(
            id=a.id,
            project_id=a.project_id,
            period=a.period,
            period_type=a.period_type,
            total_amount=a.total_amount,
            transaction_count=a.transaction_count,
            volatility_score=a.volatility_score,
            period_end_concentration=a.period_end_concentration,
            anomaly_indicators=a.anomaly_indicators
        )
        for a in analyses
    ]


@router.get("/dimensions/document")
async def get_document_completeness(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取文档完整性分析"""
    with get_db_cursor() as cursor:
        # 统计各类文档缺失情况
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN va.id IS NOT NULL THEN 1 ELSE 0 END) as with_attachment
            FROM vouchers v
            LEFT JOIN voucher_attachments va ON v.id = va.voucher_id
            WHERE v.project_id = ?
            """,
            [project_id]
        )
        row = cursor.fetchone()

        total = row[0] or 0
        with_attachment = row[1] or 0

        # 按科目统计缺失情况
        cursor.execute(
            """
            SELECT
                v.subject_name,
                COUNT(*) as total,
                SUM(CASE WHEN va.id IS NULL THEN 1 ELSE 0 END) as missing
            FROM vouchers v
            LEFT JOIN voucher_attachments va ON v.id = va.voucher_id
            WHERE v.project_id = ? AND v.subject_name IS NOT NULL
            GROUP BY v.subject_name
            ORDER BY missing DESC
            LIMIT 10
            """,
            [project_id]
        )
        by_subject = [
            {
                "subject_name": row[0],
                "total": row[1],
                "missing": row[2],
                "missing_rate": round(row[2] / row[1] * 100, 2) if row[1] > 0 else 0
            }
            for row in cursor.fetchall()
        ]

    return {
        "total_vouchers": total,
        "with_attachment": with_attachment,
        "missing_attachment": total - with_attachment,
        "completeness_rate": round(with_attachment / total * 100, 2) if total > 0 else 0,
        "by_subject": by_subject
    }


# ==================== 交易风险清单 ====================

@router.get("/transactions", response_model=TransactionListResponse)
async def get_transaction_risk_list(
    project_id: str,
    risk_level: Optional[str] = Query(default=None, regex="^(high|medium|low)$"),
    min_amount: Optional[float] = Query(default=None, ge=0),
    max_amount: Optional[float] = Query(default=None, ge=0),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    counterparty: Optional[str] = None,
    subject_code: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: UserInDB = Depends(get_current_user)
):
    """获取交易风险清单（支持高级筛选）"""
    filters = {}
    if risk_level:
        filters["risk_level"] = risk_level
    if min_amount is not None:
        filters["min_amount"] = min_amount
    if max_amount is not None:
        filters["max_amount"] = max_amount
    if start_date:
        filters["start_date"] = str(start_date)
    if end_date:
        filters["end_date"] = str(end_date)
    if counterparty:
        filters["counterparty"] = counterparty
    if subject_code:
        filters["subject_code"] = subject_code

    result = voucher_risk_service.get_transaction_list(
        project_id, filters if filters else None, page, page_size
    )

    return TransactionListResponse(**result)


@router.get("/transactions/{voucher_id}")
async def get_transaction_risk_detail(
    project_id: str,
    voucher_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取单条交易风险详情"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, voucher_no, voucher_date, amount,
                   subject_code, subject_name, description, counterparty,
                   risk_score, risk_level, risk_tags, ai_analysis
            FROM vouchers
            WHERE id = ? AND project_id = ?
            """,
            [voucher_id, project_id]
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="凭证不存在")

        import json
        risk_tags = json.loads(row[10]) if isinstance(row[10], str) else row[10] or []
        ai_analysis = json.loads(row[11]) if isinstance(row[11], str) else row[11] or {}

        # 构建风险因素说明
        risk_factors = []
        for tag in risk_tags:
            if isinstance(tag, dict):
                risk_factors.append(tag.get('name', ''))

        # 添加AI分析的风险因素
        if ai_analysis:
            ai_explanation = ai_analysis.get('explanation', '')
            ai_attention = ai_analysis.get('audit_attention', [])
            if ai_explanation and ai_explanation not in risk_factors:
                risk_factors.append(f"AI分析: {ai_explanation}")
            for attention in ai_attention:
                if attention and attention not in risk_factors:
                    risk_factors.append(f"AI建议: {attention}")

        return {
            "id": row[0],
            "voucher_no": row[1],
            "voucher_date": str(row[2]) if row[2] else None,
            "amount": float(row[3]) if row[3] else 0,
            "subject_code": row[4],
            "subject_name": row[5],
            "description": row[6],
            "counterparty": row[7],
            "risk_score": float(row[8]) if row[8] else 0,
            "risk_level": row[9] or "low",
            "risk_tags": risk_tags,
            "risk_factors": risk_factors,
            "ai_analysis": ai_analysis
        }


@router.post("/transactions/batch-add-sampling", response_model=BatchAddSamplingResponse)
async def batch_add_to_sampling(
    project_id: str,
    request: BatchAddSamplingRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """批量添加交易到抽样清单"""
    if not request.voucher_ids:
        raise HTTPException(status_code=400, detail="凭证ID列表不能为空")

    result = voucher_risk_service.batch_add_to_sampling(
        project_id,
        request.voucher_ids,
        request.reason or "风险画像批量添加"
    )

    return BatchAddSamplingResponse(**result)


# ==================== 风险标签统计 ====================

@router.get("/tags", response_model=List[RiskTagStatistics])
async def get_risk_tags(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取风险标签统计"""
    stats = voucher_risk_service.get_risk_tag_statistics(project_id)
    return [RiskTagStatistics(**s) for s in stats]


@router.get("/tags/by-voucher/{voucher_id}")
async def get_voucher_risk_tags(
    project_id: str,
    voucher_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取指定凭证的风险标签"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT tag_code, tag_name, tag_category, severity, details
            FROM voucher_risk_tags
            WHERE project_id = ? AND voucher_id = ?
            """,
            [project_id, voucher_id]
        )
        rows = cursor.fetchall()

        import json
        return [
            {
                "tag_code": row[0],
                "tag_name": row[1],
                "tag_category": row[2],
                "severity": row[3],
                "details": json.loads(row[4]) if isinstance(row[4], str) else row[4]
            }
            for row in rows
        ]


# ==================== 高风险科目 ====================

@router.get("/high-risk-subjects")
async def get_high_risk_subjects(
    project_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    current_user: UserInDB = Depends(get_current_user)
):
    """获取高风险科目TOP N"""
    profiles = risk_profile_generator.get_project_profiles(project_id)

    sorted_profiles = sorted(profiles, key=lambda p: p.risk_score, reverse=True)[:limit]

    return [
        {
            "subject_code": p.subject_code,
            "subject_name": p.subject_name,
            "risk_score": p.risk_score,
            "risk_level": p.risk_level.value,
            "material_amount": p.material_amount,
            "recommendation": p.recommendation
        }
        for p in sorted_profiles
    ]


# ==================== 科目风险画像 ====================

@router.get("/subjects", response_model=List[RiskProfileResponse])
async def get_subject_profiles(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取所有科目风险画像"""
    profiles = risk_profile_generator.get_project_profiles(project_id)

    return [
        RiskProfileResponse(
            id=p.id,
            project_id=p.project_id,
            subject_code=p.subject_code,
            subject_name=p.subject_name,
            risk_level=p.risk_level.value,
            risk_score=p.risk_score,
            risk_factors=[
                RiskFactorResponse(
                    name=f.name,
                    weight=f.weight,
                    score=f.score,
                    description=f.description
                ) for f in p.risk_factors
            ],
            material_amount=p.material_amount,
            anomaly_score=p.anomaly_score,
            recommendation=p.recommendation,
            created_at=p.created_at
        )
        for p in profiles
    ]


@router.post("/subjects/generate", response_model=List[RiskProfileResponse])
async def generate_subject_profiles(
    project_id: str,
    use_ai: bool = Query(default=True, description="是否启用AI增强分析"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    生成科目风险画像

    Args:
        use_ai: true=AI增强模式（较慢，更智能），false=规则引擎模式（快速）
    """
    import asyncio

    if use_ai:
        # AI增强模式：使用异步方法
        profiles = await risk_profile_generator._generate_profiles_with_ai_from_api(project_id)
    else:
        # 快速模式：使用线程池执行同步方法
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            profiles = await loop.run_in_executor(
                executor,
                risk_profile_generator.generate_project_profiles,
                project_id,
                False  # use_ai=False
            )

    return [
        RiskProfileResponse(
            id=p.id,
            project_id=p.project_id,
            subject_code=p.subject_code,
            subject_name=p.subject_name,
            risk_level=p.risk_level.value,
            risk_score=p.risk_score,
            risk_factors=[
                RiskFactorResponse(
                    name=f.name,
                    weight=f.weight,
                    score=f.score,
                    description=f.description
                ) for f in p.risk_factors
            ],
            material_amount=p.material_amount,
            anomaly_score=p.anomaly_score,
            recommendation=p.recommendation,
            created_at=p.created_at
        )
        for p in profiles
    ]


@router.get("/subjects/{subject_code}", response_model=RiskProfileResponse)
async def get_subject_profile_detail(
    project_id: str,
    subject_code: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取科目风险画像详情"""
    profile = risk_profile_generator.get_profile(project_id, subject_code)

    if not profile:
        raise HTTPException(status_code=404, detail="科目风险画像不存在")

    return RiskProfileResponse(
        id=profile.id,
        project_id=profile.project_id,
        subject_code=profile.subject_code,
        subject_name=profile.subject_name,
        risk_level=profile.risk_level.value,
        risk_score=profile.risk_score,
        risk_factors=[
            RiskFactorResponse(
                name=f.name,
                weight=f.weight,
                score=f.score,
                description=f.description
            ) for f in profile.risk_factors
        ],
        material_amount=profile.material_amount,
        anomaly_score=profile.anomaly_score,
        recommendation=profile.recommendation,
        created_at=profile.created_at
    )


# ==================== 分层抽样建议 ====================

@router.get("/layered-sampling", response_model=LayeredSamplingResponse)
async def get_layered_sampling_recommendation(
    project_id: str,
    high_ratio: float = Query(default=1.0, ge=0, le=1),
    medium_ratio: float = Query(default=0.3, ge=0, le=1),
    low_ratio: float = Query(default=0.05, ge=0, le=1),
    current_user: UserInDB = Depends(get_current_user)
):
    """获取分层抽样建议"""
    result = risk_profile_generator.calculate_layered_sample_size(
        project_id, high_ratio, medium_ratio, low_ratio
    )

    return LayeredSamplingResponse(**result)


# ==================== 风险配置 ====================

@router.get("/config/weights")
async def get_risk_weights(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取风险权重配置"""
    return risk_config_service.get_weights(project_id)


@router.put("/config/weights")
async def update_risk_weights(
    project_id: str,
    request: UpdateWeightsRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """更新风险权重配置"""
    try:
        result = risk_config_service.update_weights(project_id, request.weights)
        return {"success": True, "weights": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新风险权重配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新配置失败，请稍后重试")


@router.get("/config/thresholds")
async def get_risk_thresholds(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取风险阈值配置"""
    return risk_config_service.get_thresholds(project_id)


@router.put("/config/thresholds")
async def update_risk_thresholds(
    project_id: str,
    request: UpdateThresholdsRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """更新风险阈值配置"""
    try:
        result = risk_config_service.update_thresholds(project_id, request.thresholds)
        return {"success": True, "thresholds": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/config/rules")
async def get_risk_rules(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取风险规则列表"""
    return risk_config_service.get_rules(project_id)


@router.put("/config/rules/{rule_code}")
async def toggle_risk_rule(
    project_id: str,
    rule_code: str,
    request: ToggleRuleRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """切换规则开关"""
    try:
        result = risk_config_service.toggle_rule(project_id, rule_code, request.enabled)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/config/templates")
async def get_risk_templates(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取配置模板列表"""
    return risk_config_service.get_templates(project_id)


@router.post("/config/templates/save")
async def save_risk_template(
    project_id: str,
    request: SaveTemplateRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """保存当前配置为模板"""
    result = risk_config_service.save_template(project_id, request.template_name)
    return result


@router.post("/config/templates/load")
async def load_risk_template(
    project_id: str,
    request: LoadTemplateRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """加载配置模板"""
    try:
        result = risk_config_service.load_template(project_id, request.template_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/config/templates/{template_name}")
async def delete_risk_template(
    project_id: str,
    template_name: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """删除配置模板"""
    result = risk_config_service.delete_template(project_id, template_name)
    return result


@router.get("/config/full")
async def get_full_config(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取完整配置"""
    return risk_config_service.get_full_config(project_id)


@router.post("/config/reset")
async def reset_config_to_default(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """重置为默认配置"""
    result = risk_config_service.reset_to_default(project_id)
    return result


# ==================== 导出功能 ====================

from fastapi.responses import StreamingResponse
import io
import csv
from datetime import datetime as dt


@router.get("/export/excel")
async def export_risk_excel(
    project_id: str,
    risk_level: Optional[str] = Query(default=None, regex="^(high|medium|low)$"),
    include_tags: bool = Query(default=True),
    current_user: UserInDB = Depends(get_current_user)
):
    """导出风险清单为CSV（Excel兼容）"""
    filters = {}
    if risk_level:
        filters["risk_level"] = risk_level

    result = voucher_risk_service.get_transaction_list(
        project_id, filters if filters else None, page=1, page_size=10000
    )

    # 生成CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入标题行
    headers = ["凭证号", "日期", "金额", "科目代码", "科目名称", "交易对手", "摘要", "风险分数", "风险等级"]
    if include_tags:
        headers.append("风险标签")
    writer.writerow(headers)

    # 写入数据行
    for item in result.get("items", []):
        row = [
            item.get("voucher_no", ""),
            item.get("voucher_date", ""),
            item.get("amount", 0),
            item.get("subject_code", ""),
            item.get("subject_name", ""),
            item.get("counterparty", ""),
            item.get("description", ""),
            item.get("risk_score", 0),
            getRiskLabel(item.get("risk_level", "low"))
        ]
        if include_tags:
            tags = ", ".join([t.get("name", "") for t in item.get("risk_tags", [])])
            row.append(tags)
        writer.writerow(row)

    output.seek(0)

    # 获取项目名称
    with get_db_cursor() as cursor:
        cursor.execute("SELECT name FROM projects WHERE id = ?", [project_id])
        project_row = cursor.fetchone()
        project_name = project_row[0] if project_row else "项目"

    filename = f"{project_name}_风险清单_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # 添加BOM以支持Excel打开
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def getRiskLabel(level: str) -> str:
    """获取风险等级标签"""
    labels = {"high": "高风险", "medium": "中风险", "low": "低风险"}
    return labels.get(level, level)


@router.get("/export/subject-excel")
async def export_subject_risk_excel(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """导出科目风险画像为CSV"""
    profiles = risk_profile_generator.get_project_profiles(project_id)

    # 生成CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入标题行
    headers = ["科目代码", "科目名称", "风险等级", "风险分数", "重要性水平", "异常分数", "抽样建议"]
    writer.writerow(headers)

    # 写入数据行
    for p in profiles:
        row = [
            p.subject_code,
            p.subject_name,
            getRiskLabel(p.risk_level.value),
            round(p.risk_score, 2),
            p.material_amount,
            p.anomaly_score,
            p.recommendation[:100] if p.recommendation else ""
        ]
        writer.writerow(row)

    output.seek(0)

    # 获取项目名称
    with get_db_cursor() as cursor:
        cursor.execute("SELECT name FROM projects WHERE id = ?", [project_id])
        project_row = cursor.fetchone()
        project_name = project_row[0] if project_row else "项目"

    filename = f"{project_name}_科目风险画像_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/summary")
async def export_risk_summary(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """导出风险分析摘要"""
    # 获取各类数据
    overview = risk_profile_generator.get_project_overview(project_id)
    profiles = risk_profile_generator.get_project_profiles(project_id)
    counterparty_risks = risk_profile_generator.get_counterparty_risks(project_id)

    # 统计数据
    risk_distribution = {"high": 0, "medium": 0, "low": 0}
    for p in profiles:
        risk_distribution[p.risk_level.value] = risk_distribution.get(p.risk_level.value, 0) + 1

    # 生成摘要
    summary = {
        "project_id": project_id,
        "generated_at": dt.now().isoformat(),
        "overall_risk": {
            "score": overview.overall_risk_score if overview else 0,
            "level": overview.overall_risk_level if overview else "unknown"
        },
        "subject_statistics": {
            "total_subjects": len(profiles),
            "risk_distribution": risk_distribution
        },
        "counterparty_statistics": {
            "total_counterparties": len(counterparty_risks),
            "related_party_count": sum(1 for c in counterparty_risks if c.is_related_party),
            "new_customer_count": sum(1 for c in counterparty_risks if c.is_new_customer)
        },
        "top_risk_subjects": [
            {
                "code": p.subject_code,
                "name": p.subject_name,
                "score": p.risk_score,
                "level": p.risk_level.value
            }
            for p in sorted(profiles, key=lambda x: x.risk_score, reverse=True)[:5]
        ]
    }

    return summary


# ==================== 执行风险分层抽样 ====================

class ExecuteLayeredSamplingRequest(BaseModel):
    """执行分层抽样请求"""
    high_ratio: float = Field(default=1.0, ge=0, le=1, description="高风险抽样比例")
    medium_ratio: float = Field(default=0.3, ge=0, le=1, description="中风险抽样比例")
    low_ratio: float = Field(default=0.05, ge=0, le=1, description="低风险抽样比例")
    use_ai: bool = Field(default=False, description="是否使用AI增强分析")


class LayeredSamplingResult(BaseModel):
    """分层抽样结果"""
    record_id: str
    total_sample_size: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    layers_summary: List[Dict[str, Any]]
    message: str


@router.post("/execute-layered-sampling", response_model=LayeredSamplingResult)
async def execute_layered_sampling(
    project_id: str,
    request: ExecuteLayeredSamplingRequest = ExecuteLayeredSamplingRequest(),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    执行风险分层抽样

    根据凭证风险等级进行分层抽样：
    - 高风险凭证：100%检查（默认）
    - 中风险凭证：30%抽样（默认）
    - 低风险凭证：5%抽样（默认）

    如果use_ai=True，先使用AI重新分析凭证风险再抽样

    Returns:
        LayeredSamplingResult: 抽样结果
    """
    import uuid
    import random
    from datetime import datetime

    # 如果使用AI增强模式，先进行AI风险分析
    if request.use_ai:
        logger.info(f"[分层抽样] 开始AI增强分析，项目: {project_id}")
        try:
            from app.services.voucher_risk_service import voucher_risk_service
            await voucher_risk_service.batch_analyze_vouchers(project_id, use_ai=True)
            logger.info(f"[分层抽样] AI分析完成")
        except Exception as e:
            logger.error(f"[分层抽样] AI分析失败: {e}")
            # AI失败时继续使用现有风险等级

    with get_db_cursor() as cursor:
        # 验证项目存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 获取各风险等级的凭证（此时风险等级已更新）
        cursor.execute(
            """
            SELECT id, voucher_no, voucher_date, amount, subject_code, subject_name,
                   description, counterparty, risk_score, risk_level
            FROM vouchers
            WHERE project_id = ?
            """,
            [project_id]
        )
        all_vouchers = cursor.fetchall()

        if not all_vouchers:
            raise HTTPException(status_code=400, detail="项目中没有凭证数据")

        # 按风险等级分组
        high_risk_vouchers = []
        medium_risk_vouchers = []
        low_risk_vouchers = []

        for v in all_vouchers:
            risk_level = v[9] or "low"
            if risk_level == "high":
                high_risk_vouchers.append(v)
            elif risk_level == "medium":
                medium_risk_vouchers.append(v)
            else:
                low_risk_vouchers.append(v)

        # 执行分层抽样
        selected_samples = []
        layers_summary = []

        # 高风险层
        random.shuffle(high_risk_vouchers)
        high_sample_count = len(high_risk_vouchers)
        if request.high_ratio >= 1.0:
            high_sample_count = len(high_risk_vouchers)  # 100%检查
        else:
            high_sample_count = max(1, int(len(high_risk_vouchers) * request.high_ratio))
        high_samples = high_risk_vouchers[:high_sample_count]
        selected_samples.extend(high_samples)
        layers_summary.append({
            "level": "high",
            "total_count": len(high_risk_vouchers),
            "sample_count": high_sample_count,
            "ratio": request.high_ratio
        })

        # 中风险层
        random.shuffle(medium_risk_vouchers)
        medium_sample_count = max(1, int(len(medium_risk_vouchers) * request.medium_ratio))
        medium_sample_count = min(medium_sample_count, len(medium_risk_vouchers))
        medium_samples = medium_risk_vouchers[:medium_sample_count]
        selected_samples.extend(medium_samples)
        layers_summary.append({
            "level": "medium",
            "total_count": len(medium_risk_vouchers),
            "sample_count": medium_sample_count,
            "ratio": request.medium_ratio
        })

        # 低风险层
        random.shuffle(low_risk_vouchers)
        # 如果总体数量大于0，至少抽取1笔样本
        low_sample_count = len(low_risk_vouchers) * request.low_ratio
        if low_sample_count > 0 and low_sample_count < 1:
            low_sample_count = 1  # 至少抽取1笔
        else:
            low_sample_count = int(low_sample_count)
        low_sample_count = min(low_sample_count, len(low_risk_vouchers))
        if low_sample_count > 0:
            low_samples = low_risk_vouchers[:low_sample_count]
            selected_samples.extend(low_samples)
        layers_summary.append({
            "level": "low",
            "total_count": len(low_risk_vouchers),
            "sample_count": low_sample_count,
            "ratio": request.low_ratio
        })

        # 创建抽样记录
        record_id = str(uuid.uuid4())
        rule_id = str(uuid.uuid4())
        now = datetime.now()

        # 创建抽样规则记录
        cursor.execute(
            """
            INSERT INTO sampling_rules (id, project_id, name, rule_type, rule_config, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                rule_id,
                project_id,
                "风险分层抽样",
                "stratified",
                json.dumps({
                    "high_ratio": request.high_ratio,
                    "medium_ratio": request.medium_ratio,
                    "low_ratio": request.low_ratio
                }, ensure_ascii=False),
                True,
                now
            ]
        )

        # 创建抽样记录
        cursor.execute(
            """
            INSERT INTO sampling_records (id, project_id, rule_id, rule_name, rule_type,
                                         sample_size, high_risk_count, medium_risk_count, low_risk_count, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record_id,
                project_id,
                rule_id,
                "风险分层抽样",
                "stratified",
                len(selected_samples),
                high_sample_count,
                medium_sample_count,
                low_sample_count,
                "completed",
                now
            ]
        )

        # 统计风险等级数量
        high_risk_count = high_sample_count
        medium_risk_count = medium_sample_count
        low_risk_count = low_sample_count

        # 保存样本
        for v in selected_samples:
            sample_id = str(uuid.uuid4())
            voucher_id = v[0]
            risk_score = float(v[8]) if v[8] else 0
            risk_level = v[9] or "low"

            cursor.execute(
                """
                INSERT INTO samples (id, project_id, record_id, rule_id, voucher_id, risk_score, risk_level, reason, sampled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    sample_id,
                    project_id,
                    record_id,
                    rule_id,
                    voucher_id,
                    risk_score,
                    risk_level,
                    f"风险分层抽样 - {risk_level}风险层",
                    now
                ]
            )

        get_db().commit()

        return LayeredSamplingResult(
            record_id=record_id,
            total_sample_size=len(selected_samples),
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            layers_summary=layers_summary,
            message=f"风险分层抽样完成。高风险{high_risk_count}笔，中风险{medium_risk_count}笔，低风险{low_risk_count}笔，共{len(selected_samples)}笔样本已添加到抽样清单。"
        )