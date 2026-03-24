"""
智能抽样API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
import json

from app.core.database import get_db_cursor, get_db

router = APIRouter()


# ==================== 数据模型 ====================

class SamplingRuleCreate(BaseModel):
    """创建抽凭规则"""
    name: str = Field(..., description="规则名称")
    rule_type: str = Field(..., description="规则类型: random/amount/subject/date/ai")
    rule_config: dict = Field(..., description="规则配置")


class SamplingRuleResponse(BaseModel):
    """抽凭规则响应"""
    id: str
    project_id: str
    name: str
    rule_type: str
    rule_config: dict
    is_active: bool
    created_at: datetime


class SamplingExecuteRequest(BaseModel):
    """执行抽凭请求"""
    rule_id: str = Field(..., description="规则ID")
    sample_size: Optional[int] = Field(None, description="样本数量")


class SampleResponse(BaseModel):
    """抽样结果"""
    id: str
    voucher_id: str
    voucher_no: str
    amount: Optional[float]
    subject_name: Optional[str]
    description: Optional[str]
    risk_score: Optional[float]
    reason: Optional[str]


class SamplingResultResponse(BaseModel):
    """抽凭结果响应"""
    rule_id: str
    rule_name: str
    total_population: int
    sample_size: int
    samples: List[SampleResponse]


class RiskProfileResponse(BaseModel):
    """风险画像响应"""
    id: str
    subject_code: str
    subject_name: Optional[str]
    risk_level: str
    risk_factors: List[str]
    material_amount: Optional[float]
    anomaly_score: Optional[float]
    recommendation: Optional[str]


# ==================== API端点 ====================

@router.get("/projects/{project_id}/sampling-rules", response_model=List[SamplingRuleResponse])
async def list_sampling_rules(project_id: str):
    """获取抽凭规则列表"""
    with get_db_cursor() as cursor:
        # 验证项目存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        cursor.execute(
            """
            SELECT id, project_id, name, rule_type, rule_config, is_active, created_at
            FROM sampling_rules
            WHERE project_id = ?
            ORDER BY created_at DESC
            """,
            [project_id]
        )
        rows = cursor.fetchall()

        return [
            SamplingRuleResponse(
                id=row[0],
                project_id=row[1],
                name=row[2],
                rule_type=row[3],
                rule_config=json.loads(row[4]) if isinstance(row[4], str) else row[4],
                is_active=bool(row[5]),
                created_at=row[6]
            )
            for row in rows
        ]


@router.post("/projects/{project_id}/sampling-rules", response_model=SamplingRuleResponse, status_code=201)
async def create_sampling_rule(project_id: str, rule: SamplingRuleCreate):
    """创建抽凭规则"""
    with get_db_cursor() as cursor:
        # 验证项目存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        rule_id = str(uuid.uuid4())
        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO sampling_rules (id, project_id, name, rule_type, rule_config, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [rule_id, project_id, rule.name, rule.rule_type, json.dumps(rule.rule_config), True, now]
        )
        get_db().commit()

        return SamplingRuleResponse(
            id=rule_id,
            project_id=project_id,
            name=rule.name,
            rule_type=rule.rule_type,
            rule_config=rule.rule_config,
            is_active=True,
            created_at=now
        )


@router.post("/projects/{project_id}/sampling/execute", response_model=SamplingResultResponse)
async def execute_sampling(project_id: str, request: SamplingExecuteRequest):
    """执行抽凭"""
    with get_db_cursor() as cursor:
        # 验证项目存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 获取规则
        cursor.execute(
            "SELECT id, name, rule_type, rule_config FROM sampling_rules WHERE id = ? AND project_id = ?",
            [request.rule_id, project_id]
        )
        rule_row = cursor.fetchone()
        if not rule_row:
            raise HTTPException(status_code=404, detail="规则不存在")

        rule_id, rule_name, rule_type, rule_config_str = rule_row
        rule_config = json.loads(rule_config_str) if isinstance(rule_config_str, str) else rule_config_str

        # 获取凭证总数
        cursor.execute("SELECT COUNT(*) FROM vouchers WHERE project_id = ?", [project_id])
        total_population = cursor.fetchone()[0]

        if total_population == 0:
            raise HTTPException(status_code=400, detail="项目中没有凭证数据")

        # 根据规则类型执行抽样
        if rule_type == "random":
            # 随机抽样
            sample_pct = rule_config.get("percentage", 10)
            sample_size = request.sample_size or max(1, int(total_population * sample_pct / 100))

            cursor.execute(
                f"""
                SELECT id, voucher_no, amount, subject_name, description
                FROM vouchers
                WHERE project_id = ?
                ORDER BY RANDOM()
                LIMIT ?
                """,
                [project_id, sample_size]
            )

        elif rule_type == "amount":
            # 金额抽样
            min_amount = rule_config.get("min_amount", 0)
            max_amount = rule_config.get("max_amount")
            sample_pct = rule_config.get("percentage", 10)

            query = """
                SELECT id, voucher_no, amount, subject_name, description
                FROM vouchers
                WHERE project_id = ? AND amount >= ?
            """
            params = [project_id, min_amount]

            if max_amount:
                query += " AND amount <= ?"
                params.append(max_amount)

            query += " ORDER BY amount DESC"

            cursor.execute(query, params)
            all_matches = cursor.fetchall()

            # 计算样本量
            sample_size = request.sample_size or max(1, int(len(all_matches) * sample_pct / 100))
            selected = all_matches[:sample_size]

        elif rule_type == "subject":
            # 科目抽样
            subject_codes = rule_config.get("subject_codes", [])
            if not subject_codes:
                raise HTTPException(status_code=400, detail="科目抽样规则需要指定科目代码")

            placeholders = ",".join(["?" for _ in subject_codes])
            cursor.execute(
                f"""
                SELECT id, voucher_no, amount, subject_name, description
                FROM vouchers
                WHERE project_id = ? AND subject_code IN ({placeholders})
                """,
                [project_id] + subject_codes
            )
            all_matches = cursor.fetchall()
            sample_size = len(all_matches)
            selected = all_matches

        elif rule_type == "date":
            # 日期范围抽样
            start_date = rule_config.get("start_date")
            end_date = rule_config.get("end_date")

            if not start_date or not end_date:
                raise HTTPException(status_code=400, detail="日期抽样规则需要指定开始和结束日期")

            cursor.execute(
                """
                SELECT id, voucher_no, amount, subject_name, description
                FROM vouchers
                WHERE project_id = ? AND voucher_date BETWEEN ? AND ?
                """,
                [project_id, start_date, end_date]
            )
            all_matches = cursor.fetchall()
            sample_size = len(all_matches)
            selected = all_matches

        else:
            raise HTTPException(status_code=400, detail=f"不支持的规则类型: {rule_type}")

        # 如果是random类型，结果在cursor中
        if rule_type == "random":
            selected = cursor.fetchall()

        # 保存抽样结果
        samples = []
        now = datetime.now()

        for row in selected:
            sample_id = str(uuid.uuid4())
            voucher_id = row[0]

            cursor.execute(
                """
                INSERT INTO samples (id, project_id, rule_id, voucher_id, risk_score, reason, sampled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [sample_id, project_id, rule_id, voucher_id, None, f"规则【{rule_name}】抽取", now]
            )

            samples.append(SampleResponse(
                id=sample_id,
                voucher_id=voucher_id,
                voucher_no=row[1],
                amount=float(row[2]) if row[2] else None,
                subject_name=row[3],
                description=row[4],
                risk_score=None,
                reason=f"规则【{rule_name}】抽取"
            ))

        get_db().commit()

        return SamplingResultResponse(
            rule_id=rule_id,
            rule_name=rule_name,
            total_population=total_population,
            sample_size=len(samples),
            samples=samples
        )


@router.get("/projects/{project_id}/samples")
async def list_samples(
    project_id: str,
    rule_id: Optional[str] = Query(None, description="按规则筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """获取抽凭结果"""
    offset = (page - 1) * page_size

    with get_db_cursor() as cursor:
        # 验证项目存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 构建查询
        conditions = ["s.project_id = ?"]
        params = [project_id]

        if rule_id:
            conditions.append("s.rule_id = ?")
            params.append(rule_id)

        where_clause = " AND ".join(conditions)

        # 查询总数
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM samples s
            WHERE {where_clause}
            """,
            params
        )
        total = cursor.fetchone()[0]

        # 查询列表
        cursor.execute(
            f"""
            SELECT s.id, s.voucher_id, v.voucher_no, v.amount, v.subject_name,
                   v.description, s.risk_score, s.reason
            FROM samples s
            JOIN vouchers v ON s.voucher_id = v.id
            WHERE {where_clause}
            ORDER BY s.sampled_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset]
        )
        rows = cursor.fetchall()

        items = [
            SampleResponse(
                id=row[0],
                voucher_id=row[1],
                voucher_no=row[2],
                amount=float(row[3]) if row[3] else None,
                subject_name=row[4],
                description=row[5],
                risk_score=float(row[6]) if row[6] else None,
                reason=row[7]
            )
            for row in rows
        ]

        return {"total": total, "items": items}


@router.post("/projects/{project_id}/samples/export")
async def export_samples(
    project_id: str,
    rule_id: Optional[str] = Query(None, description="规则ID"),
    format: str = Query("excel", description="导出格式: excel/pdf")
):
    """
    导出抽凭结果

    Args:
        project_id: 项目ID
        rule_id: 规则ID（可选）
        format: 导出格式 (excel/pdf)
    """
    from fastapi.responses import Response
    from app.services.export_service import excel_exporter, pdf_exporter

    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    try:
        if format == "pdf":
            file_data = pdf_exporter.export_working_paper(project_id)
            filename = f"sampling_report_{project_id}.pdf"
            media_type = "application/pdf"
        else:
            file_data = excel_exporter.export_sampling_results(project_id, rule_id)
            filename = f"sampling_results_{project_id}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        return Response(
            content=file_data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")