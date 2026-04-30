"""
合规检查API
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.database import get_db_cursor, get_db
from app.services.compliance_service import compliance_checker, ComplianceAlert
from app.schemas.enums import ComplianceSeverity
from app.core.auth import get_current_user, UserInDB

router = APIRouter()


# ==================== Pydantic模型 ====================

class ComplianceCheckRequest(BaseModel):
    """合规检查请求"""
    rule_codes: Optional[List[str]] = Field(default=None, description="指定检查的规则代码列表")


class ComplianceAlertResponse(BaseModel):
    """合规预警响应"""
    id: str
    project_id: str
    voucher_id: str
    voucher_no: str
    rule_code: str
    rule_name: str
    rule_description: str
    severity: str
    alert_message: str
    details: dict
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime


class ComplianceRuleResponse(BaseModel):
    """合规规则响应"""
    code: str
    name: str
    description: str
    severity: str
    enabled: bool


class ComplianceCheckResultResponse(BaseModel):
    """合规检查结果响应"""
    project_id: str
    total_checked: int
    alert_count: int
    summary: dict
    checked_at: datetime


class ResolveAlertRequest(BaseModel):
    """处理预警请求"""
    resolved_by: Optional[str] = Field(default=None, description="处理人")


# ==================== API端点 ====================

@router.get("/projects/{project_id}/compliance/rules")
async def get_compliance_rules(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取合规检查规则列表"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    rules = []
    for code, rule in compliance_checker.rules.items():
        rules.append(ComplianceRuleResponse(
            code=rule.code,
            name=rule.name,
            description=rule.description,
            severity=rule.severity.value,
            enabled=rule.enabled
        ))

    return rules


@router.post("/projects/{project_id}/compliance/check")
async def run_compliance_check(
    project_id: str,
    request: ComplianceCheckRequest = None,
    current_user: UserInDB = Depends(get_current_user)
):
    """执行合规检查"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    # 清除旧的预警（可选，根据业务需求决定是否保留历史）
    with get_db_cursor() as cursor:
        cursor.execute(
            "DELETE FROM compliance_alerts WHERE project_id = ?",
            [project_id]
        )
        get_db().commit()

    # 执行检查
    rule_codes = request.rule_codes if request else None
    result = compliance_checker.check_project(project_id, rule_codes)

    return ComplianceCheckResultResponse(
        project_id=result.project_id,
        total_checked=result.total_checked,
        alert_count=len(result.alerts),
        summary=result.summary,
        checked_at=result.checked_at
    )


@router.get("/projects/{project_id}/compliance/alerts")
async def get_compliance_alerts(
    project_id: str,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取合规预警列表"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    # 获取预警
    severity_enum = ComplianceSeverity(severity) if severity else None
    alerts = compliance_checker.get_alerts(project_id, severity_enum, resolved)

    result = []
    for alert in alerts:
        result.append(ComplianceAlertResponse(
            id=alert.id,
            project_id=alert.project_id,
            voucher_id=alert.voucher_id,
            voucher_no=alert.voucher_no,
            rule_code=alert.rule_code,
            rule_name=alert.rule_name,
            rule_description=alert.rule_description,
            severity=alert.severity.value,
            alert_message=alert.alert_message,
            details=alert.details,
            is_resolved=alert.is_resolved,
            resolved_at=alert.resolved_at,
            created_at=alert.created_at
        ))

    return result


@router.put("/projects/{project_id}/compliance/alerts/{alert_id}/resolve")
async def resolve_compliance_alert(
    project_id: str,
    alert_id: str,
    request: ResolveAlertRequest = None,
    current_user: UserInDB = Depends(get_current_user)
):
    """处理合规预警"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 验证预警存在
        cursor.execute(
            "SELECT id FROM compliance_alerts WHERE id = ? AND project_id = ?",
            [alert_id, project_id]
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="预警不存在")

    # 标记为已处理
    resolved_by = request.resolved_by if request else None
    compliance_checker.resolve_alert(alert_id, resolved_by)

    return {"message": "预警已标记为已处理"}


@router.get("/projects/{project_id}/compliance/statistics")
async def get_compliance_statistics(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取合规检查统计"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    # 统计预警
    with get_db_cursor() as cursor:
        # 总预警数
        cursor.execute(
            "SELECT COUNT(*) FROM compliance_alerts WHERE project_id = ?",
            [project_id]
        )
        total = cursor.fetchone()[0]

        # 未处理数
        cursor.execute(
            "SELECT COUNT(*) FROM compliance_alerts WHERE project_id = ? AND is_resolved = FALSE",
            [project_id]
        )
        pending = cursor.fetchone()[0]

        # 按严重程度统计
        cursor.execute(
            """
            SELECT severity, COUNT(*)
            FROM compliance_alerts
            WHERE project_id = ?
            GROUP BY severity
            """,
            [project_id]
        )
        by_severity = {row[0]: row[1] for row in cursor.fetchall()}

        # 按规则统计
        cursor.execute(
            """
            SELECT rule_name, COUNT(*)
            FROM compliance_alerts
            WHERE project_id = ?
            GROUP BY rule_name
            """,
            [project_id]
        )
        by_rule = {row[0]: row[1] for row in cursor.fetchall()}

    return {
        "total": total,
        "pending": pending,
        "resolved": total - pending,
        "by_severity": by_severity,
        "by_rule": by_rule
    }
