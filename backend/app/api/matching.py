"""
三单匹配API
发票、订单、入库单自动匹配核对
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from enum import Enum

from app.api.dependencies import validate_project_exists
from app.core.database import get_db_cursor, get_db
from app.services.three_way_matching_service import three_way_matcher, MatchStatus
from app.core.auth import get_current_user, UserInDB

router = APIRouter(prefix="/matching", tags=["三单匹配"])


class MatchStatusEnum(str, Enum):
    fully_matched = "fully_matched"
    partially_matched = "partially_matched"
    not_matched = "not_matched"


@router.post("/projects/{project_id}/matching/execute")
async def execute_matching(
    project_id: str,
    amount_tolerance: float = Query(default=0.01, description="金额容差（比例）"),
    date_tolerance: int = Query(default=30, description="日期容差（天数）"),
    invoice_ids: Optional[List[str]] = None,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    执行三单匹配

    Args:
        project_id: 项目ID
        amount_tolerance: 金额容差（默认1%）
        date_tolerance: 日期容差（默认30天）
        invoice_ids: 指定发票ID列表（可选）
    """
    validate_project_exists(project_id)

    # 设置容差参数
    three_way_matcher.amount_tolerance = amount_tolerance
    three_way_matcher.date_tolerance = date_tolerance

    # 执行匹配
    results = three_way_matcher.match_from_database(project_id, invoice_ids)

    return {
        "total": len(results),
        "results": [
            {
                "id": r.id,
                "invoice_no": r.invoice_no,
                "order_no": r.order_no,
                "receipt_no": r.receipt_no,
                "match_status": r.match_status.value,
                "amount": 0,  # 需要从凭证获取
                "amount_difference": r.amount_difference,
                "date_difference": r.date_difference,
                "differences": r.differences if isinstance(r.differences, list) else [],
                "suggestions": r.suggestions
            }
            for r in results
        ]
    }


@router.get("/projects/{project_id}/matching/results")
async def get_matching_results(
    project_id: str,
    status: Optional[MatchStatusEnum] = None,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    获取匹配结果列表

    Args:
        project_id: 项目ID
        status: 匹配状态筛选
    """
    validate_project_exists(project_id)

    match_status = MatchStatus(status.value) if status else None
    results = three_way_matcher.get_match_results(project_id, match_status)

    # 获取金额信息
    with get_db_cursor() as cursor:
        for r in results:
            cursor.execute(
                "SELECT amount FROM vouchers WHERE id = ?",
                [r.invoice_id]
            )
            row = cursor.fetchone()
            r.amount = float(row[0]) if row and row[0] else 0

    return {
        "total": len(results),
        "results": [
            {
                "id": r.id,
                "invoice_no": r.invoice_no,
                "order_no": r.order_no,
                "receipt_no": r.receipt_no,
                "match_status": r.match_status.value,
                "amount": getattr(r, 'amount', 0),
                "amount_difference": r.amount_difference,
                "date_difference": r.date_difference,
                "differences": [],
                "suggestions": r.suggestions
            }
            for r in results
        ]
    }


@router.delete("/projects/{project_id}/matching/results")
async def clear_matching_results(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """清空匹配结果"""
    validate_project_exists(project_id)

    with get_db_cursor() as cursor:
        cursor.execute("DELETE FROM matching_results WHERE project_id = ?", [project_id])
        get_db().commit()

    return {"message": "匹配结果已清空"}
