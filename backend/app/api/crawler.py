"""
爬虫API路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.services.crawler_service import crawler_service
from app.core.auth import get_current_user, UserInDB

router = APIRouter()


class CrawlStartRequest(BaseModel):
    """启动爬虫请求"""
    project_id: str
    platform: str = 'mock_platform'
    count: int = 100
    year: int = 2024


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


class PlatformResponse(BaseModel):
    """平台信息响应"""
    id: str
    name: str
    description: str
    supports_attachments: bool


@router.get("/platforms", response_model=List[PlatformResponse])
async def get_platforms(current_user: UserInDB = Depends(get_current_user)):
    """获取可用平台列表"""
    platforms = crawler_service.get_available_platforms()
    return platforms


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