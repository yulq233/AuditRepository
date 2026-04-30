"""
凭证管理API
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Any

from datetime import datetime, date
import uuid
import json
import os
import logging

from app.core.database import get_db_cursor, get_db
from app.core.config import settings
from app.core.auth import get_current_user, UserInDB
from app.services.llm_service import llm_service, get_recognition_service

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

class VoucherCreate(BaseModel):
    """创建凭证请求"""
    voucher_no: str = Field(..., description="凭证编号")
    voucher_date: Optional[date] = Field(None, description="凭证日期")
    amount: Optional[float] = Field(None, ge=0, description="金额")
    subject_code: Optional[str] = Field(None, description="科目代码")
    subject_name: Optional[str] = Field(None, description="科目名称")
    description: Optional[str] = Field(None, description="摘要")
    counterparty: Optional[str] = Field(None, description="交易对手")
    raw_data: Optional[dict] = Field(None, description="原始数据")


class VoucherUpdate(BaseModel):
    """更新凭证请求"""
    voucher_no: Optional[str] = Field(None, description="凭证编号")
    voucher_date: Optional[date] = Field(None, description="凭证日期")
    amount: Optional[float] = Field(None, ge=0, description="金额")
    subject_code: Optional[str] = Field(None, description="科目代码")
    subject_name: Optional[str] = Field(None, description="科目名称")
    description: Optional[str] = Field(None, description="摘要")
    counterparty: Optional[str] = Field(None, description="交易对手")


class VoucherResponse(BaseModel):
    """凭证响应"""
    id: str
    project_id: str
    voucher_no: str
    voucher_date: Optional[date]
    amount: Optional[float]
    subject_code: Optional[str]
    subject_name: Optional[str]
    description: Optional[str]
    counterparty: Optional[str]
    attachment_path: Optional[str]
    created_at: datetime


class VoucherListResponse(BaseModel):
    """凭证列表响应"""
    total: int
    items: List[VoucherResponse]


class ImportResult(BaseModel):
    """导入结果"""
    success: int
    failed: int
    errors: List[str] = []
    imported_ids: List[str] = []  # 成功导入的凭证ID列表


# ==================== API端点 ====================

@router.get("/projects/{project_id}/vouchers", response_model=VoucherListResponse)
async def list_vouchers(
    project_id: str,
    subject_code: Optional[str] = Query(None, description="科目代码筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    min_amount: Optional[float] = Query(None, description="最小金额"),
    max_amount: Optional[float] = Query(None, description="最大金额"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: UserInDB = Depends(get_current_user)
):
    """获取凭证列表"""
    offset = (page - 1) * page_size

    with get_db_cursor() as cursor:
        # 验证项目存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 构建查询条件
        conditions = ["project_id = ?"]
        params = [project_id]

        if subject_code:
            conditions.append("subject_code = ?")
            params.append(subject_code)

        if start_date:
            conditions.append("voucher_date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("voucher_date <= ?")
            params.append(end_date)

        if min_amount is not None:
            conditions.append("amount >= ?")
            params.append(min_amount)

        if max_amount is not None:
            conditions.append("amount <= ?")
            params.append(max_amount)

        if keyword:
            conditions.append("(voucher_no LIKE ? OR description LIKE ? OR subject_name LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])

        where_clause = " AND ".join(conditions)

        # 查询总数
        cursor.execute(f"SELECT COUNT(*) FROM vouchers WHERE {where_clause}", params)
        total = cursor.fetchone()[0]

        # 查询列表
        cursor.execute(
            f"""
            SELECT id, project_id, voucher_no, voucher_date, amount,
                   subject_code, subject_name, description, counterparty,
                   attachment_path, created_at
            FROM vouchers
            WHERE {where_clause}
            ORDER BY voucher_date DESC, voucher_no
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset]
        )
        rows = cursor.fetchall()

        items = [
            VoucherResponse(
                id=row[0],
                project_id=row[1],
                voucher_no=row[2],
                voucher_date=row[3],
                amount=float(row[4]) if row[4] else None,
                subject_code=row[5],
                subject_name=row[6],
                description=row[7],
                counterparty=row[8],
                attachment_path=row[9],
                created_at=row[10]
            )
            for row in rows
        ]

        return VoucherListResponse(total=total, items=items)


class PopulationStatsResponse(BaseModel):
    """总体统计响应"""
    count: int = Field(..., description="凭证数量")
    total_amount: float = Field(..., description="总金额")
    min_amount: Optional[float] = Field(None, description="最小金额")
    max_amount: Optional[float] = Field(None, description="最大金额")
    avg_amount: Optional[float] = Field(None, description="平均金额")


@router.get("/projects/{project_id}/vouchers/population-stats", response_model=PopulationStatsResponse)
async def get_population_stats(
    project_id: str,
    subject_codes: Optional[str] = Query(None, description="科目代码筛选，多个用逗号分隔"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    min_amount: Optional[float] = Query(None, description="最小金额"),
    max_amount: Optional[float] = Query(None, description="最大金额"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    获取凭证总体统计

    用于抽样向导中计算总体规模，支持按科目、日期、金额范围筛选
    """
    with get_db_cursor() as cursor:
        # 验证项目存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 构建查询条件
        conditions = ["project_id = ?"]
        params = [project_id]

        if subject_codes:
            # 支持多个科目代码
            codes = [c.strip() for c in subject_codes.split(",") if c.strip()]
            if codes:
                placeholders = ",".join(["?" for _ in codes])
                conditions.append(f"subject_code IN ({placeholders})")
                params.extend(codes)

        if start_date:
            conditions.append("voucher_date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("voucher_date <= ?")
            params.append(end_date)

        if min_amount is not None:
            conditions.append("amount >= ?")
            params.append(min_amount)

        if max_amount is not None:
            conditions.append("amount <= ?")
            params.append(max_amount)

        where_clause = " AND ".join(conditions)

        # 查询统计数据
        cursor.execute(
            f"""
            SELECT
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as total_amount,
                MIN(amount) as min_amount,
                MAX(amount) as max_amount,
                AVG(amount) as avg_amount
            FROM vouchers
            WHERE {where_clause}
            """,
            params
        )
        row = cursor.fetchone()

        return PopulationStatsResponse(
            count=row[0],
            total_amount=float(row[1]) if row[1] else 0.0,
            min_amount=float(row[2]) if row[2] else None,
            max_amount=float(row[3]) if row[3] else None,
            avg_amount=float(row[4]) if row[4] else None
        )


@router.get("/projects/{project_id}/vouchers/import-template")
async def download_import_template(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """下载凭证导入模板"""
    import io
    from fastapi.responses import StreamingResponse

    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    # 创建模板内容
    template_content = """凭证编号,凭证日期,金额,科目代码,科目名称,摘要,交易对手
记-2024-0001,2024-01-15,15000.00,1002,银行存款,支付北京科技有限公司货款,北京科技有限公司
记-2024-0002,2024-01-16,8500.00,1122,应收账款,收到上海贸易有限公司回款,上海贸易有限公司
记-2024-0003,2024-01-18,23000.50,2202,应付账款,支付广州制造有限公司采购款,广州制造有限公司"""

    # 返回文件
    output = io.BytesIO(template_content.encode('utf-8-sig'))  # 添加BOM以支持Excel正确识别中文
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=voucher_template_{project_id[:8]}.csv"
        }
    )


@router.post("/projects/{project_id}/vouchers/import", response_model=ImportResult)
async def import_vouchers(
    project_id: str,
    file: UploadFile = File(..., description="Excel/CSV文件"),
    current_user: UserInDB = Depends(get_current_user)
):
    """导入凭证数据(Excel/CSV)

    支持的列名：
    - 凭证编号/凭证号（必填）
    - 凭证日期/日期（格式：YYYY-MM-DD）
    - 金额
    - 科目代码/科目编码
    - 科目名称
    - 摘要
    - 交易对手/对方单位
    """
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    # 验证文件类型
    filename = file.filename.lower()
    if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
        raise HTTPException(status_code=400, detail="只支持Excel(.xlsx/.xls)或CSV文件")

    success = 0
    failed = 0
    errors = []
    imported_ids = []  # 记录成功导入的ID

    try:
        import pandas as pd
        import io

        # 读取文件
        content = await file.read()

        if filename.endswith('.csv'):
            # 尝试多种编码
            for encoding in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise HTTPException(status_code=400, detail="无法识别文件编码，请使用UTF-8或GBK编码")
        else:
            df = pd.read_excel(io.BytesIO(content))

        # 检查是否为空文件
        if df.empty:
            raise HTTPException(status_code=400, detail="文件内容为空")

        # 标准化列名映射
        column_mapping = {
            '凭证编号': 'voucher_no',
            '凭证号': 'voucher_no',
            '日期': 'voucher_date',
            '凭证日期': 'voucher_date',
            '金额': 'amount',
            '科目代码': 'subject_code',
            '科目编码': 'subject_code',
            '科目名称': 'subject_name',
            '摘要': 'description',
            '交易对手': 'counterparty',
            '对方单位': 'counterparty',
            '往来单位': 'counterparty',
            '借方金额': 'debit_amount',
            '贷方金额': 'credit_amount',
        }

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 必须有凭证编号列
        if 'voucher_no' not in df.columns:
            raise HTTPException(status_code=400, detail="文件缺少凭证编号列（需要'凭证编号'或'凭证号'列）")

        # 检查是否有数据
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="文件没有数据行")

        # 批量插入
        with get_db_cursor() as cursor:
            for idx, row in df.iterrows():
                try:
                    voucher_id = str(uuid.uuid4())
                    now = datetime.now()

                    # 凭证编号必填
                    voucher_no = row['voucher_no']
                    if pd.isna(voucher_no) or str(voucher_no).strip() == '':
                        raise ValueError("凭证编号不能为空")

                    # 处理日期 - 支持多种格式
                    voucher_date = None
                    if 'voucher_date' in row and pd.notna(row['voucher_date']):
                        date_val = row['voucher_date']
                        if isinstance(date_val, str):
                            date_str = date_val.strip()
                            # 尝试多种日期格式
                            date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y年%m月%d日']
                            for fmt in date_formats:
                                try:
                                    voucher_date = datetime.strptime(date_str, fmt).date()
                                    break
                                except ValueError:
                                    continue
                            if voucher_date is None:
                                raise ValueError(f"日期格式错误: {date_val}，请使用 YYYY-MM-DD 格式")
                        elif hasattr(date_val, 'date'):
                            voucher_date = date_val.date()
                        else:
                            try:
                                voucher_date = pd.to_datetime(date_val).date()
                            except:
                                raise ValueError(f"日期格式错误: {date_val}")

                    # 处理金额 - 支持借方/贷方金额
                    amount = None
                    if 'amount' in row and pd.notna(row['amount']):
                        amount = float(row['amount'])
                    elif 'debit_amount' in row and pd.notna(row.get('debit_amount')):
                        amount = float(row['debit_amount'])
                    elif 'credit_amount' in row and pd.notna(row.get('credit_amount')):
                        amount = float(row['credit_amount'])

                    # 处理文本字段
                    def safe_str(val):
                        if pd.isna(val):
                            return None
                        return str(val).strip() if str(val).strip() else None

                    cursor.execute(
                        """
                        INSERT INTO vouchers
                        (id, project_id, voucher_no, voucher_date, amount,
                         subject_code, subject_name, description, counterparty,
                         created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            voucher_id,
                            project_id,
                            str(voucher_no).strip(),
                            voucher_date,
                            amount,
                            safe_str(row.get('subject_code')),
                            safe_str(row.get('subject_name')),
                            safe_str(row.get('description')),
                            safe_str(row.get('counterparty')),
                            now,
                            now
                        ]
                    )
                    success += 1
                    imported_ids.append(voucher_id)
                except ValueError as e:
                    failed += 1
                    errors.append(f"第{idx + 2}行: {str(e)}")
                except Exception as e:
                    failed += 1
                    errors.append(f"第{idx + 2}行: {str(e)}")

            get_db().commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"凭证导入失败: {str(e)}")
        raise HTTPException(status_code=500, detail="导入失败，请稍后重试")

    return ImportResult(
        success=success,
        failed=failed,
        errors=errors[:10],  # 最多返回10条错误
        imported_ids=imported_ids[:100]  # 返回前100个导入的ID
    )


@router.get("/projects/{project_id}/vouchers/{voucher_id}", response_model=VoucherResponse)
async def get_voucher(
    project_id: str,
    voucher_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取凭证详情"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, project_id, voucher_no, voucher_date, amount,
                   subject_code, subject_name, description, counterparty,
                   attachment_path, created_at
            FROM vouchers
            WHERE id = ? AND project_id = ?
            """,
            [voucher_id, project_id]
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="凭证不存在")

        return VoucherResponse(
            id=row[0],
            project_id=row[1],
            voucher_no=row[2],
            voucher_date=row[3],
            amount=float(row[4]) if row[4] else None,
            subject_code=row[5],
            subject_name=row[6],
            description=row[7],
            counterparty=row[8],
            attachment_path=row[9],
            created_at=row[10]
        )


@router.put("/projects/{project_id}/vouchers/{voucher_id}", response_model=VoucherResponse)
async def update_voucher(
    project_id: str,
    voucher_id: str,
    data: VoucherUpdate,
    current_user: UserInDB = Depends(get_current_user)
):
    """更新凭证信息"""
    with get_db_cursor() as cursor:
        # 验证凭证存在
        cursor.execute(
            "SELECT id FROM vouchers WHERE id = ? AND project_id = ?",
            [voucher_id, project_id]
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="凭证不存在")

        # 构建更新字段
        update_fields = []
        update_values = []

        if data.voucher_no is not None:
            update_fields.append("voucher_no = ?")
            update_values.append(data.voucher_no)
        if data.voucher_date is not None:
            update_fields.append("voucher_date = ?")
            update_values.append(data.voucher_date)
        if data.amount is not None:
            update_fields.append("amount = ?")
            update_values.append(data.amount)
        if data.subject_code is not None:
            update_fields.append("subject_code = ?")
            update_values.append(data.subject_code)
        if data.subject_name is not None:
            update_fields.append("subject_name = ?")
            update_values.append(data.subject_name)
        if data.description is not None:
            update_fields.append("description = ?")
            update_values.append(data.description)
        if data.counterparty is not None:
            update_fields.append("counterparty = ?")
            update_values.append(data.counterparty)

        if not update_fields:
            raise HTTPException(status_code=400, detail="没有要更新的字段")

        # 添加更新时间
        update_fields.append("updated_at = ?")
        update_values.append(datetime.now())

        # 执行更新
        update_values.extend([voucher_id, project_id])
        cursor.execute(
            f"UPDATE vouchers SET {', '.join(update_fields)} WHERE id = ? AND project_id = ?",
            update_values
        )
        get_db().commit()

        # 返回更新后的数据
        cursor.execute(
            """
            SELECT id, project_id, voucher_no, voucher_date, amount,
                   subject_code, subject_name, description, counterparty,
                   attachment_path, created_at
            FROM vouchers
            WHERE id = ? AND project_id = ?
            """,
            [voucher_id, project_id]
        )
        row = cursor.fetchone()

        return VoucherResponse(
            id=row[0],
            project_id=row[1],
            voucher_no=row[2],
            voucher_date=row[3],
            amount=float(row[4]) if row[4] else None,
            subject_code=row[5],
            subject_name=row[6],
            description=row[7],
            counterparty=row[8],
            attachment_path=row[9],
            created_at=row[10]
        )


@router.post("/projects/{project_id}/vouchers/{voucher_id}/attachment")
async def upload_attachment(
    project_id: str,
    voucher_id: str,
    file: UploadFile = File(..., description="附件文件"),
    current_user: UserInDB = Depends(get_current_user)
):
    """上传凭证附件"""
    with get_db_cursor() as cursor:
        # 验证凭证存在
        cursor.execute(
            "SELECT id FROM vouchers WHERE id = ? AND project_id = ?",
            [voucher_id, project_id]
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="凭证不存在")

    # 验证文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}"
        )

    # 创建存储目录
    upload_dir = os.path.join(settings.ATTACHMENT_PATH, project_id)
    os.makedirs(upload_dir, exist_ok=True)

    # 生成文件名
    attachment_id = str(uuid.uuid4())
    save_path = os.path.join(upload_dir, f"{attachment_id}{file_ext}")

    # 保存文件
    content = await file.read()
    with open(save_path, 'wb') as f:
        f.write(content)

    # 更新数据库
    relative_path = f"{project_id}/{attachment_id}{file_ext}"
    with get_db_cursor() as cursor:
        cursor.execute(
            "UPDATE vouchers SET attachment_path = ?, updated_at = ? WHERE id = ?",
            [relative_path, datetime.now(), voucher_id]
        )
        get_db().commit()

    return {"message": "附件上传成功", "path": relative_path}


@router.get("/projects/{project_id}/vouchers/{voucher_id}/attachments")
async def list_attachments(
    project_id: str,
    voucher_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取凭证附件列表"""
    with get_db_cursor() as cursor:
        # 验证凭证存在
        cursor.execute(
            "SELECT id FROM vouchers WHERE id = ? AND project_id = ?",
            [voucher_id, project_id]
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="凭证不存在")

        # 查询附件列表（包含识别结果）
        cursor.execute(
            """
            SELECT id, file_name, file_path, file_size, file_type, uploaded_at, recognition_result
            FROM voucher_attachments
            WHERE voucher_id = ?
            ORDER BY uploaded_at DESC
            """,
            [voucher_id]
        )
        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "file_name": row[1],
                "file_path": row[2],
                "file_size": row[3],
                "file_type": row[4],
                "uploaded_at": row[5],
                "recognition_result": json.loads(row[6]) if row[6] else None
            }
            for row in rows
        ]


@router.post("/projects/{project_id}/vouchers/{voucher_id}/attachments")
async def upload_attachments(
    project_id: str,
    voucher_id: str,
    files: List[UploadFile] = File(..., description="附件文件列表"),
    current_user: UserInDB = Depends(get_current_user)
):
    """批量上传凭证附件"""
    with get_db_cursor() as cursor:
        # 验证凭证存在
        cursor.execute(
            "SELECT id FROM vouchers WHERE id = ? AND project_id = ?",
            [voucher_id, project_id]
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="凭证不存在")

    # 创建存储目录
    upload_dir = os.path.join(settings.ATTACHMENT_PATH, project_id)
    os.makedirs(upload_dir, exist_ok=True)

    uploaded = []
    for file in files:
        # 验证文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            continue  # 跳过不支持的文件类型

        # 生成文件名
        attachment_id = str(uuid.uuid4())
        save_path = os.path.join(upload_dir, f"{attachment_id}{file_ext}")

        # 保存文件
        content = await file.read()
        with open(save_path, 'wb') as f:
            f.write(content)

        # 获取文件大小
        file_size = len(content)

        # 保存到数据库
        relative_path = f"{project_id}/{attachment_id}{file_ext}"
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO voucher_attachments (id, voucher_id, file_name, file_path, file_size, file_type, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [attachment_id, voucher_id, file.filename, relative_path, file_size, file_ext, datetime.now()]
            )
            get_db().commit()

        uploaded.append({
            "id": attachment_id,
            "file_name": file.filename,
            "file_path": relative_path,
            "file_size": file_size
        })

    return {"message": f"成功上传 {len(uploaded)} 个附件", "attachments": uploaded}


@router.delete("/projects/{project_id}/vouchers/{voucher_id}/attachments/{attachment_id}")
async def delete_attachment(
    project_id: str,
    voucher_id: str,
    attachment_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """删除附件"""
    with get_db_cursor() as cursor:
        # 查询附件
        cursor.execute(
            """
            SELECT a.file_path
            FROM voucher_attachments a
            JOIN vouchers v ON a.voucher_id = v.id
            WHERE a.id = ? AND v.project_id = ? AND a.voucher_id = ?
            """,
            [attachment_id, project_id, voucher_id]
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="附件不存在")

        file_path = row[0]

        # 删除文件
        full_path = os.path.join(settings.ATTACHMENT_PATH, file_path)
        if os.path.exists(full_path):
            os.remove(full_path)

        # 删除数据库记录
        cursor.execute("DELETE FROM voucher_attachments WHERE id = ?", [attachment_id])
        get_db().commit()

    return {"message": "附件删除成功"}


@router.post("/projects/{project_id}/vouchers/{voucher_id}/attachments/{attachment_id}/recognize")
async def recognize_attachment(
    project_id: str,
    voucher_id: str,
    attachment_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    AI识别附件内容

    使用AI视觉模型识别附件中的内容信息（使用图片/PDF识别专用模型配置）
    """
    from app.services.llm_service import ChatMessage, get_recognition_service
    import base64

    # 使用识别专用服务
    recognition_service = get_recognition_service()

    with get_db_cursor() as cursor:
        # 验证凭证存在
        cursor.execute(
            "SELECT id FROM vouchers WHERE id = ? AND project_id = ?",
            [voucher_id, project_id]
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="凭证不存在")

        # 获取附件信息
        cursor.execute(
            "SELECT file_path, file_name, file_type FROM voucher_attachments WHERE id = ? AND voucher_id = ?",
            [attachment_id, voucher_id]
        )
        attachment_row = cursor.fetchone()

        if not attachment_row:
            raise HTTPException(status_code=404, detail="附件不存在")

        file_path, file_name, file_type = attachment_row

    # 获取附件完整路径
    full_path = os.path.join(settings.ATTACHMENT_PATH, file_path)

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="附件文件不存在")

    # 判断文件类型
    file_ext = file_type if file_type else os.path.splitext(file_path)[1].lower()

    try:
        if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            # 读取图片并编码为base64
            with open(full_path, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # 构建AI识别提示 - 只识别内容，不分析风险
            prompt = """请识别这张图片中的所有文字内容，提取关键信息并以JSON格式返回。

请识别并返回以下信息（仅返回JSON格式）：
{
    "voucher_no": "凭证编号（如能识别）",
    "voucher_date": "凭证日期(YYYY-MM-DD格式)",
    "amount": "金额数字（仅数字）",
    "counterparty": "交易对手/单位名称",
    "description": "业务摘要",
    "subject_suggestion": "建议会计科目",
    "key_info": "图片中的主要文字内容摘要",
    "confidence": 0.85
}"""

            messages = [
                ChatMessage(role="system", content="你是一个专业的凭证内容识别助手。请仔细识别图片中的所有文字，仅返回JSON格式的识别结果，不要包含任何分析或建议。"),
                ChatMessage(role="user", content=prompt, images=[image_base64])
            ]

            response = await recognition_service.chat_with_images(messages, temperature=0.3)
            result_text = response.content

        elif file_ext == '.pdf':
            # PDF文件 - 提取文本后用AI识别
            extracted_text = ""
            try:
                import PyPDF2
                with open(full_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        extracted_text += page.extract_text() + "\n"
            except Exception as e:
                extracted_text = f"[PDF文本提取失败: {str(e)}]"

            prompt = f"""请识别以下PDF文档内容，提取关键信息并以JSON格式返回：

提取的内容：
{extracted_text[:3000] if extracted_text else '(无提取内容)'}

请返回以下JSON格式：
{{
    "voucher_no": "凭证编号",
    "voucher_date": "凭证日期(YYYY-MM-DD)",
    "amount": "金额数字",
    "counterparty": "交易对手",
    "description": "业务摘要",
    "subject_suggestion": "建议科目",
    "key_info": "文档主要内容摘要",
    "confidence": 0.85
}}"""

            messages = [
                ChatMessage(role="system", content="你是一个专业的凭证内容识别助手。仅返回JSON格式的识别结果。"),
                ChatMessage(role="user", content=prompt)
            ]

            response = await recognition_service.chat(messages, temperature=0.3)
            result_text = response.content

        else:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")

        # 解析结果
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except:
                result = {"key_info": result_text, "confidence": 0.5}
        else:
            result = {"key_info": result_text, "confidence": 0.5}

        # 添加识别时间
        result["recognized_at"] = datetime.now().isoformat()

        # 保存识别结果到数据库
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE voucher_attachments
                SET recognition_result = ?
                WHERE id = ?
                """,
                [json.dumps(result, ensure_ascii=False), attachment_id]
            )
            get_db().commit()

        return {
            "message": "识别完成",
            "attachment_id": attachment_id,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"附件识别失败: {str(e)}")
        raise HTTPException(status_code=500, detail="识别失败，请稍后重试")


@router.get("/projects/{project_id}/vouchers/{voucher_id}/attachments/{attachment_id}/recognition-result")
async def get_recognition_result(
    project_id: str,
    voucher_id: str,
    attachment_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取附件识别结果"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT recognition_result FROM voucher_attachments
            WHERE id = ? AND voucher_id = ?
            """,
            [attachment_id, voucher_id]
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="附件不存在")

        result = row[0]
        if result:
            return {"result": json.loads(result)}
        else:
            return {"result": None}


@router.post("/projects/{project_id}/vouchers/{voucher_id}/ocr")
async def ocr_voucher(
    project_id: str,
    voucher_id: str,
    preprocess: bool = Query(True, description="是否预处理图片"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    OCR识别凭证

    Args:
        project_id: 项目ID
        voucher_id: 凭证ID
        preprocess: 是否预处理图片
    """
    from app.services.ocr_service import ocr_service

    with get_db_cursor() as cursor:
        # 验证凭证存在
        cursor.execute(
            "SELECT id FROM vouchers WHERE id = ? AND project_id = ?",
            [voucher_id, project_id]
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="凭证不存在")

        # 从附件表获取第一个图片附件
        cursor.execute(
            "SELECT file_path FROM voucher_attachments WHERE voucher_id = ? AND file_type IN ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.pdf') ORDER BY uploaded_at DESC LIMIT 1",
            [voucher_id]
        )
        attachment_row = cursor.fetchone()

    if not attachment_row:
        raise HTTPException(status_code=400, detail="凭证没有可识别的附件")

    attachment_path = attachment_row[0]

    # 获取附件完整路径
    full_path = os.path.join(settings.ATTACHMENT_PATH, attachment_path)

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="附件文件不存在")

    try:
        # 执行OCR识别
        result = ocr_service.recognize(full_path, preprocess=preprocess)

        # 保存结果
        result_id = ocr_service.save_result(voucher_id, result)

        return {
            "message": "OCR识别完成",
            "result_id": result_id,
            "voucher_no": result.voucher_no,
            "voucher_date": result.voucher_date,
            "amount": result.amount,
            "counterparty": result.counterparty,
            "description": result.description,
            "confidence": result.confidence,
            "provider": result.provider
        }

    except Exception as e:
        logger.error(f"OCR识别失败: {str(e)}")
        raise HTTPException(status_code=500, detail="OCR识别失败，请稍后重试")


@router.get("/projects/{project_id}/vouchers/{voucher_id}/ocr")
async def get_ocr_result(
    project_id: str,
    voucher_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取凭证OCR结果"""
    from app.services.ocr_service import ocr_service

    with get_db_cursor() as cursor:
        # 验证凭证存在
        cursor.execute(
            "SELECT id FROM vouchers WHERE id = ? AND project_id = ?",
            [voucher_id, project_id]
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="凭证不存在")

    result = ocr_service.get_cached_result(voucher_id)

    if not result:
        raise HTTPException(status_code=404, detail="尚未进行OCR识别")

    return {
        "voucher_no": result.voucher_no,
        "voucher_date": result.voucher_date,
        "amount": result.amount,
        "counterparty": result.counterparty,
        "description": result.description,
        "raw_text": result.raw_text,
        "confidence": result.confidence,
        "provider": result.provider
    }


@router.delete("/projects/{project_id}/vouchers/{voucher_id}")
async def delete_voucher(
    project_id: str,
    voucher_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """删除单个凭证"""
    with get_db_cursor() as cursor:
        # 查询凭证（不强制要求project_id匹配，因为voucher_id已是主键）
        cursor.execute(
            "SELECT id, attachment_path FROM vouchers WHERE id = ?",
            [voucher_id]
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="凭证不存在")

        attachment_path = row[1]

        # 获取附件文件路径列表（用于删除物理文件）
        cursor.execute(
            "SELECT file_path FROM voucher_attachments WHERE voucher_id = ?",
            [voucher_id]
        )
        attachment_paths = [r[0] for r in cursor.fetchall()]

        # 删除关联数据
        cursor.execute("DELETE FROM voucher_attachments WHERE voucher_id = ?", [voucher_id])
        cursor.execute("DELETE FROM voucher_ocr_results WHERE voucher_id = ?", [voucher_id])
        cursor.execute("DELETE FROM voucher_categories WHERE voucher_id = ?", [voucher_id])
        cursor.execute("DELETE FROM samples WHERE voucher_id = ?", [voucher_id])
        cursor.execute("DELETE FROM vouchers WHERE id = ?", [voucher_id])

        get_db().commit()

    # 删除旧的附件文件（兼容旧数据）
    if attachment_path:
        full_path = os.path.join(settings.ATTACHMENT_PATH, attachment_path)
        if os.path.exists(full_path):
            os.remove(full_path)

    # 删除voucher_attachments表中的物理文件
    for file_path in attachment_paths:
        full_path = os.path.join(settings.ATTACHMENT_PATH, file_path)
        if os.path.exists(full_path):
            os.remove(full_path)

    return {"message": "删除成功", "voucher_id": voucher_id}


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    voucher_ids: List[str] = Field(..., description="凭证ID列表")


@router.post("/projects/{project_id}/vouchers/batch-delete")
async def batch_delete_vouchers(
    project_id: str,
    request: BatchDeleteRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """批量删除凭证"""
    if not request.voucher_ids:
        raise HTTPException(status_code=400, detail="请选择要删除的凭证")

    deleted_count = 0
    errors = []

    with get_db_cursor() as cursor:
        for voucher_id in request.voucher_ids:
            try:
                # 获取凭证信息（不强制要求project_id匹配，因为voucher_id已是主键）
                cursor.execute(
                    "SELECT attachment_path, project_id FROM vouchers WHERE id = ?",
                    [voucher_id]
                )
                row = cursor.fetchone()
                if not row:
                    errors.append(f"凭证 {voucher_id} 不存在")
                    continue

                attachment_path = row[0]

                # 获取附件文件路径列表
                cursor.execute(
                    "SELECT file_path FROM voucher_attachments WHERE voucher_id = ?",
                    [voucher_id]
                )
                attachment_paths = [r[0] for r in cursor.fetchall()]

                # 删除关联数据
                cursor.execute("DELETE FROM voucher_attachments WHERE voucher_id = ?", [voucher_id])
                cursor.execute("DELETE FROM voucher_ocr_results WHERE voucher_id = ?", [voucher_id])
                cursor.execute("DELETE FROM voucher_categories WHERE voucher_id = ?", [voucher_id])
                cursor.execute("DELETE FROM samples WHERE voucher_id = ?", [voucher_id])
                cursor.execute("DELETE FROM vouchers WHERE id = ?", [voucher_id])

                deleted_count += 1

                # 删除旧的附件文件
                if attachment_path:
                    full_path = os.path.join(settings.ATTACHMENT_PATH, attachment_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)

                # 删除voucher_attachments表中的物理文件
                for file_path in attachment_paths:
                    full_path = os.path.join(settings.ATTACHMENT_PATH, file_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)

            except Exception as e:
                logger.error(f"删除凭证 {voucher_id} 失败: {str(e)}")
                errors.append(f"删除凭证 {voucher_id} 失败")

        get_db().commit()

    return {
        "message": f"成功删除 {deleted_count} 条凭证",
        "deleted_count": deleted_count,
        "errors": errors[:10]  # 最多返回10条错误
    }


@router.post("/projects/{project_id}/vouchers/{voucher_id}/ai-recognize")
async def ai_recognize_voucher(
    project_id: str,
    voucher_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    AI识别凭证附件内容

    使用AI模型识别上传的文档或图片内容（使用图片/PDF识别专用模型配置）
    """
    from app.services.llm_service import ChatMessage, get_recognition_service
    from app.services.ocr_service import ocr_service

    # 使用识别专用服务
    recognition_service = get_recognition_service()

    with get_db_cursor() as cursor:
        # 验证凭证存在
        cursor.execute(
            "SELECT voucher_no, subject_name, description FROM vouchers WHERE id = ? AND project_id = ?",
            [voucher_id, project_id]
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="凭证不存在")

        voucher_no, subject_name, description = row

        # 从附件表获取第一个附件
        cursor.execute(
            "SELECT file_path, file_name, file_type FROM voucher_attachments WHERE voucher_id = ? ORDER BY uploaded_at DESC LIMIT 1",
            [voucher_id]
        )
        attachment_row = cursor.fetchone()

    if not attachment_row:
        raise HTTPException(status_code=400, detail="凭证没有附件，请先上传附件")

    attachment_path, file_name, file_type = attachment_row

    # 获取附件完整路径
    full_path = os.path.join(settings.ATTACHMENT_PATH, attachment_path)

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="附件文件不存在")

    # 判断文件类型
    file_ext = file_type if file_type else os.path.splitext(attachment_path)[1].lower()

    try:
        # 对于图片文件，直接使用AI视觉模型识别
        if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            # 读取图片并编码为base64
            import base64
            with open(full_path, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # 构建AI分析提示
            prompt = f"""请仔细分析这张凭证附件图片，提取关键信息并以JSON格式返回。

现有凭证信息：
- 凭证号: {voucher_no or '未知'}
- 科目: {subject_name or '未知'}
- 摘要: {description or '未知'}

请识别图片中的内容，分析并返回以下JSON格式（仅返回JSON，不要其他内容）：
{{
    "voucher_no": "凭证编号（如能识别）",
    "voucher_date": "凭证日期(YYYY-MM-DD格式，如能识别)",
    "amount": "金额数字（如能识别，仅数字）",
    "counterparty": "交易对手/单位（如能识别）",
    "description": "业务摘要（如能识别）",
    "subject_suggestion": "建议科目",
    "risk_points": ["风险点1", "风险点2"],
    "key_info": "关键信息摘要",
    "confidence": 0.85
}}"""

            messages = [
                ChatMessage(role="system", content="你是一位资深审计专家，专注于凭证内容识别和分析。请仔细识别图片中的文字和内容，仅返回JSON格式的结果。"),
                ChatMessage(role="user", content=prompt, images=[image_base64])
            ]

            response = await recognition_service.chat_with_images(messages, temperature=0.3)
            result_text = response.content

        elif file_ext == '.pdf':
            # PDF文件 - 提取文本后用AI分析
            extracted_text = ""
            try:
                import PyPDF2
                with open(full_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        extracted_text += page.extract_text() + "\n"
            except Exception as e:
                extracted_text = f"[PDF文本提取失败: {str(e)}]"

            prompt = f"""请分析以下凭证PDF附件内容，提取关键信息并以JSON格式返回：

现有凭证信息：
- 凭证号: {voucher_no or '未知'}
- 科目: {subject_name or '未知'}
- 摘要: {description or '未知'}

附件文件名: {file_name}
提取的内容：
{extracted_text[:3000] if extracted_text else '(无提取内容)'}

请分析并返回以下JSON格式（仅返回JSON，不要其他内容）：
{{
    "voucher_no": "凭证编号（如能识别）",
    "voucher_date": "凭证日期(YYYY-MM-DD格式，如能识别)",
    "amount": "金额数字（如能识别）",
    "counterparty": "交易对手/单位（如能识别）",
    "description": "业务摘要（如能识别）",
    "subject_suggestion": "建议科目",
    "risk_points": ["风险点1", "风险点2"],
    "key_info": "关键信息摘要",
    "confidence": 0.85
}}"""

            messages = [
                ChatMessage(role="system", content="你是一位资深审计专家，专注于凭证内容识别和分析。请仅返回JSON格式的结果，不要包含任何其他文字。"),
                ChatMessage(role="user", content=prompt)
            ]

            response = await recognition_service.chat(messages, temperature=0.3)
            result_text = response.content

        else:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")

        # 解析结果
        # 尝试提取JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except:
                result = {"key_info": result_text, "confidence": 0.5}
        else:
            result = {"key_info": result_text, "confidence": 0.5}

        return {
            "message": "AI识别完成",
            "voucher_id": voucher_id,
            "file_type": file_ext.replace('.', ''),
            "file_name": file_name,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI识别失败: {str(e)}")
        raise HTTPException(status_code=500, detail="AI识别失败，请稍后重试")