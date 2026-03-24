"""
凭证管理API
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Any

from datetime import datetime, date
import uuid
import json
import os

from app.core.database import get_db_cursor, get_db
from app.core.config import settings

router = APIRouter()


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
    errors: List[str]


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
    page_size: int = Query(50, ge=1, le=200)
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


@router.post("/projects/{project_id}/vouchers/import", response_model=ImportResult)
async def import_vouchers(
    project_id: str,
    file: UploadFile = File(..., description="Excel/CSV文件")
):
    """导入凭证数据(Excel/CSV)"""
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

    try:
        import pandas as pd
        import io

        # 读取文件
        content = await file.read()

        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

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
        }

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 必须有凭证编号列
        if 'voucher_no' not in df.columns:
            raise HTTPException(status_code=400, detail="文件缺少凭证编号列")

        # 批量插入
        with get_db_cursor() as cursor:
            for idx, row in df.iterrows():
                try:
                    voucher_id = str(uuid.uuid4())
                    now = datetime.now()

                    # 处理日期
                    voucher_date = None
                    if 'voucher_date' in row and pd.notna(row['voucher_date']):
                        if isinstance(row['voucher_date'], str):
                            voucher_date = datetime.strptime(row['voucher_date'], '%Y-%m-%d').date()
                        else:
                            voucher_date = pd.to_datetime(row['voucher_date']).date()

                    # 处理金额
                    amount = None
                    if 'amount' in row and pd.notna(row['amount']):
                        amount = float(row['amount'])

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
                            str(row['voucher_no']),
                            voucher_date,
                            amount,
                            str(row.get('subject_code', '')) if pd.notna(row.get('subject_code')) else None,
                            str(row.get('subject_name', '')) if pd.notna(row.get('subject_name')) else None,
                            str(row.get('description', '')) if pd.notna(row.get('description')) else None,
                            str(row.get('counterparty', '')) if pd.notna(row.get('counterparty')) else None,
                            now,
                            now
                        ]
                    )
                    success += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"第{idx + 2}行: {str(e)}")

            get_db().commit()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

    return ImportResult(success=success, failed=failed, errors=errors[:20])  # 最多返回20条错误


@router.get("/projects/{project_id}/vouchers/{voucher_id}", response_model=VoucherResponse)
async def get_voucher(project_id: str, voucher_id: str):
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


@router.post("/projects/{project_id}/vouchers/{voucher_id}/attachment")
async def upload_attachment(
    project_id: str,
    voucher_id: str,
    file: UploadFile = File(..., description="附件文件")
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


@router.post("/projects/{project_id}/vouchers/{voucher_id}/ocr")
async def ocr_voucher(
    project_id: str,
    voucher_id: str,
    preprocess: bool = Query(True, description="是否预处理图片")
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
            "SELECT attachment_path FROM vouchers WHERE id = ? AND project_id = ?",
            [voucher_id, project_id]
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="凭证不存在")

        attachment_path = row[0]

    if not attachment_path:
        raise HTTPException(status_code=400, detail="凭证没有附件")

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
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")


@router.get("/projects/{project_id}/vouchers/{voucher_id}/ocr")
async def get_ocr_result(project_id: str, voucher_id: str):
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