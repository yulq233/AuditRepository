"""
审计轨迹API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db_cursor
from app.services.audit_trail_service import audit_trail, AuditAction

router = APIRouter()


# ==================== 数据模型 ====================

class AuditTrailQuery(BaseModel):
    """审计轨迹查询"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    target_type: Optional[str] = None


# ==================== API端点 ====================

@router.get("/projects/{project_id}/audit-trail")
async def query_audit_trail(
    project_id: str,
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    action: Optional[str] = Query(None, description="动作类型"),
    target_type: Optional[str] = Query(None, description="目标类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量")
):
    """
    查询审计轨迹

    记录每一笔样本的"为什么抽、如何抽、结果如何"
    """
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    action_enum = AuditAction(action) if action else None

    records = audit_trail.query(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        action=action_enum,
        target_type=target_type,
        page=page,
        page_size=page_size
    )

    return {
        "total": len(records),
        "items": [
            {
                "id": r.id,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "user_id": r.user_id,
                "reason": r.reason,
                "method": r.method,
                "result": r.result,
                "ip_address": r.ip_address,
                "created_at": str(r.created_at)
            }
            for r in records
        ]
    }


@router.get("/projects/{project_id}/audit-trail/statistics")
async def get_audit_statistics(
    project_id: str,
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期")
):
    """
    获取审计轨迹统计

    统计各动作类型、用户活动的数量
    """
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    stats = audit_trail.get_statistics(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "total_count": stats["total_count"],
        "by_action": stats["by_action"],
        "by_user": stats["by_user"],
        "by_date": stats["by_date"]
    }


@router.get("/projects/{project_id}/audit-trail/samples/{sample_id}")
async def get_sample_trail(project_id: str, sample_id: str):
    """
    获取样本的完整轨迹

    记录样本从创建到复核的完整过程
    """
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    records = audit_trail.get_sample_trail(
        project_id=project_id,
        sample_id=sample_id
    )

    return {
        "sample_id": sample_id,
        "records": [
            {
                "id": r.id,
                "action": r.action,
                "reason": r.reason,
                "method": r.method,
                "result": r.result,
                "created_at": str(r.created_at)
            }
            for r in records
        ]
    }


@router.get("/projects/{project_id}/audit-trail/users/{user_id}")
async def get_user_activity(
    project_id: str,
    user_id: str,
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期")
):
    """
    获取用户活动记录

    记录指定用户在项目中的所有操作
    """
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    records = audit_trail.get_user_activity(
        project_id=project_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "user_id": user_id,
        "record_count": len(records),
        "records": [
            {
                "id": r.id,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "reason": r.reason,
                "result": r.result,
                "created_at": str(r.created_at)
            }
            for r in records
        ]
    }


@router.get("/projects/{project_id}/audit-trail/export")
async def export_audit_trail(
    project_id: str,
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期")
):
    """
    导出审计轨迹

    导出项目审计轨迹为JSON格式
    """
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    data = audit_trail.export_trail(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "project_id": project_id,
        "export_time": str(datetime.now()),
        "record_count": len(data),
        "records": data
    }


@router.get("/audit-actions")
async def list_audit_actions():
    """获取审计动作类型列表"""
    return {
        "items": [
            {"value": "project.created", "label": "项目创建", "category": "项目"},
            {"value": "project.updated", "label": "项目更新", "category": "项目"},
            {"value": "voucher.imported", "label": "凭证导入", "category": "凭证"},
            {"value": "voucher.viewed", "label": "凭证查看", "category": "凭证"},
            {"value": "voucher.ocr", "label": "凭证OCR", "category": "凭证"},
            {"value": "sample.created", "label": "样本创建", "category": "抽样"},
            {"value": "sample.reviewed", "label": "样本复核", "category": "抽样"},
            {"value": "sample.exported", "label": "样本导出", "category": "抽样"},
            {"value": "rule.created", "label": "规则创建", "category": "规则"},
            {"value": "rule.executed", "label": "规则执行", "category": "规则"},
            {"value": "ai.analyzed", "label": "AI分析", "category": "AI"},
            {"value": "ai.sampling", "label": "AI抽样", "category": "AI"},
            {"value": "task.assigned", "label": "任务分派", "category": "任务"},
            {"value": "task.started", "label": "任务开始", "category": "任务"},
            {"value": "task.completed", "label": "任务完成", "category": "任务"},
            {"value": "paper.generated", "label": "底稿生成", "category": "底稿"},
            {"value": "paper.exported", "label": "底稿导出", "category": "底稿"},
            {"value": "compliance.checked", "label": "合规检查", "category": "验证"},
            {"value": "matching.performed", "label": "匹配执行", "category": "验证"}
        ]
    }