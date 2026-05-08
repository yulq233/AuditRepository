"""
爬虫API路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import uuid

from app.services.crawler_service import crawler_service
from app.core.auth import get_current_user, UserInDB
from app.core.config import settings
from app.core.database import get_db_cursor, get_db

router = APIRouter()


class CrawlStartRequest(BaseModel):
    """启动爬虫请求"""
    project_id: str
    platform: str = 'mock_platform'
    count: int = 100
    year: int = 2024


class ExcelImportRequest(BaseModel):
    """Excel导入请求"""
    project_id: str
    file_path: str = Field(..., description="上传的文件路径")


class CrawlTaskResponse(BaseModel):
    """爬虫任务响应"""
    id: str
    project_id: str
    platform: str
    status: str
    total_count: int
    success_count: int
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ConfigFieldResponse(BaseModel):
    """配置字段响应"""
    name: str
    label: str
    type: str
    default: Optional[Any] = None
    required: Optional[bool] = False


class PlatformResponse(BaseModel):
    """平台信息响应"""
    id: str
    name: str
    description: str
    supports_attachments: bool
    config_fields: Optional[List[ConfigFieldResponse]] = None
    status: Optional[str] = None


@router.get("/platforms", response_model=List[PlatformResponse])
async def get_platforms(current_user: UserInDB = Depends(get_current_user)):
    """获取可用平台列表"""
    platforms = crawler_service.get_available_platforms()
    return [
        PlatformResponse(
            id=p['id'],
            name=p['name'],
            description=p['description'],
            supports_attachments=p.get('supports_attachments', False),
            config_fields=[
                ConfigFieldResponse(**f) for f in p.get('config_fields', [])
            ] if p.get('config_fields') else None,
            status=p.get('status')
        )
        for p in platforms
    ]


@router.post("/start", response_model=CrawlTaskResponse)
async def start_crawler(
    request: CrawlStartRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    启动爬虫任务

    - **project_id**: 项目ID
    - **platform**: 平台ID（默认为mock_platform）
    - **count**: 爬取数量（默认100）
    - **year**: 数据年份（默认2024）
    """
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [request.project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    # 创建任务
    task_id = crawler_service.create_task(
        project_id=request.project_id,
        platform=request.platform,
        count=request.count
    )

    # 启动后台爬取任务
    crawler_service.start_crawl(
        task_id=task_id,
        project_id=request.project_id,
        platform=request.platform,
        count=request.count,
        year=request.year
    )

    # 返回初始状态
    status = crawler_service.get_task_status(task_id)
    return CrawlTaskResponse(**status)


@router.post("/import-excel", response_model=CrawlTaskResponse)
async def import_from_excel(
    project_id: str,
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    从Excel文件导入凭证数据

    Excel文件应包含以下列（列名可变）：
    - 凭证号/凭证编号
    - 日期/凭证日期
    - 金额
    - 科目代码/科目编码（可选）
    - 科目名称（可选）
    - 摘要（可选）
    - 交易对手/对方单位（可选）
    """
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    # 检查文件类型
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="只支持Excel文件(.xlsx, .xls)或CSV文件")

    # 保存上传文件
    upload_dir = os.path.join(settings.ATTACHMENT_PATH, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(upload_dir, f"{file_id}{file_ext}")

    # 写入文件
    content = await file.read()
    with open(file_path, 'wb') as f:
        f.write(content)

    # 创建任务
    task_id = crawler_service.create_task(
        project_id=project_id,
        platform='excel_import',
        count=0
    )

    # 启动后台导入任务
    crawler_service.start_excel_import(
        task_id=task_id,
        project_id=project_id,
        file_path=file_path
    )

    # 返回初始状态
    status = crawler_service.get_task_status(task_id)
    return CrawlTaskResponse(**status)


@router.get("/status/{task_id}", response_model=CrawlTaskResponse)
async def get_crawler_status(
    task_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    获取爬虫任务状态

    - **task_id**: 任务ID
    """
    status = crawler_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    return CrawlTaskResponse(**status)


@router.post("/stop", response_model=CrawlTaskResponse)
async def stop_crawler(
    task_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    停止爬虫任务

    - **task_id**: 任务ID
    """
    status = crawler_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")

    if status['status'] not in ['pending', 'running']:
        raise HTTPException(status_code=400, detail="任务已完成，无法停止")

    crawler_service.stop_task(task_id)
    status = crawler_service.get_task_status(task_id)
    return CrawlTaskResponse(**status)


@router.get("/tasks/{project_id}", response_model=List[CrawlTaskResponse])
async def get_project_tasks(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    获取项目的所有爬虫任务

    - **project_id**: 项目ID
    """
    tasks = crawler_service.get_project_tasks(project_id)
    return [CrawlTaskResponse(**t) for t in tasks]


@router.get("/template")
async def download_import_template():
    """
    下载Excel导入模板

    返回一个包含示例数据的Excel模板文件
    """
    import pandas as pd
    from fastapi.responses import StreamingResponse
    import io

    # 创建示例数据
    data = {
        '凭证号': ['记-2024-0001', '记-2024-0002', '记-2024-0003'],
        '凭证日期': ['2024-01-15', '2024-02-20', '2024-03-10'],
        '金额': [50000.00, 125000.50, 8500.00],
        '科目代码': ['1002', '1122', '6602'],
        '科目名称': ['银行存款', '应收账款', '管理费用'],
        '摘要': ['收到货款', '销售商品款', '办公费'],
        '交易对手': ['北京科技有限公司', '上海贸易有限公司', '深圳电子有限公司']
    }

    df = pd.DataFrame(data)

    # 写入Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='凭证数据')

    output.seek(0)

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=voucher_import_template.xlsx'}
    )
