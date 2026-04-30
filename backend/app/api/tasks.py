"""
任务管理API
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import json
import logging

from app.core.database import get_db_cursor
from app.core.auth import get_current_user, UserInDB

logger = logging.getLogger(__name__)
from app.services.task_service import (
    task_manager, TaskStatus, TaskPriority, AuditTask, TeamMember
)

router = APIRouter()


# ==================== 数据模型 ====================

class TaskCreate(BaseModel):
    """创建任务请求"""
    title: str = Field(..., description="任务标题")
    description: str = Field(default="", description="任务描述")
    sample_ids: List[str] = Field(..., description="样本ID列表")
    assignee_id: str = Field(..., description="被分派人ID")
    assignee_name: str = Field(..., description="被分派人姓名")
    priority: str = Field(default="medium", description="优先级")
    deadline: Optional[datetime] = Field(None, description="截止时间")


class TaskStatusUpdate(BaseModel):
    """更新任务状态请求"""
    status: str = Field(..., description="新状态")
    progress: Optional[int] = Field(None, ge=0, le=100, description="进度")


class TaskNoteCreate(BaseModel):
    """添加任务备注请求"""
    content: str = Field(..., description="备注内容")


class TeamMemberCreate(BaseModel):
    """添加团队成员请求"""
    name: str = Field(..., description="姓名")
    role: str = Field(default="审计员", description="角色")
    email: Optional[str] = Field(None, description="邮箱")


class AutoAssignRequest(BaseModel):
    """自动分派请求"""
    sample_ids: List[str] = Field(..., description="样本ID列表")
    strategy: str = Field(default="balanced", description="分派策略")


# ==================== API端点 ====================

@router.post("/projects/{project_id}/tasks", status_code=201)
async def create_task(
    project_id: str,
    task: TaskCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    """创建任务"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    try:
        new_task = task_manager.create_task(
            project_id=project_id,
            title=task.title,
            description=task.description,
            sample_ids=task.sample_ids,
            assignee_id=task.assignee_id,
            assignee_name=task.assignee_name,
            priority=TaskPriority(task.priority),
            deadline=task.deadline
        )

        return {
            "message": "任务创建成功",
            "task_id": new_task.id
        }

    except Exception as e:
        logger.error(f"任务创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail="任务创建失败，请稍后重试")


@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: str,
    status: Optional[str] = Query(None, description="按状态筛选"),
    assignee_id: Optional[str] = Query(None, description="按被分派人筛选"),
    current_user: UserInDB = Depends(get_current_user)
):
    """获取任务列表"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    status_enum = TaskStatus(status) if status else None

    tasks = task_manager.get_project_tasks(
        project_id=project_id,
        status=status_enum,
        assignee_id=assignee_id
    )

    return {
        "total": len(tasks),
        "items": [
            {
                "id": t.id,
                "title": t.title,
                "assignee_name": t.assignee_name,
                "status": t.status.value,
                "priority": t.priority.value,
                "progress": t.progress,
                "sample_count": len(t.sample_ids),
                "deadline": str(t.deadline) if t.deadline else None,
                "created_at": str(t.created_at)
            }
            for t in tasks
        ]
    }


@router.get("/projects/{project_id}/tasks/{task_id}")
async def get_task(
    project_id: str,
    task_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取任务详情"""
    task = task_manager.get_task(task_id)

    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "sample_ids": task.sample_ids,
        "assignee_id": task.assignee_id,
        "assignee_name": task.assignee_name,
        "status": task.status.value,
        "priority": task.priority.value,
        "progress": task.progress,
        "deadline": str(task.deadline) if task.deadline else None,
        "notes": task.notes,
        "created_at": str(task.created_at),
        "started_at": str(task.started_at) if task.started_at else None,
        "completed_at": str(task.completed_at) if task.completed_at else None
    }


@router.put("/projects/{project_id}/tasks/{task_id}/status")
async def update_task_status(
    project_id: str,
    task_id: str,
    update: TaskStatusUpdate,
    current_user: UserInDB = Depends(get_current_user)
):
    """更新任务状态"""
    task = task_manager.get_task(task_id)

    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        updated_task = task_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus(update.status),
            progress=update.progress
        )

        return {
            "message": "状态更新成功",
            "status": updated_task.status.value,
            "progress": updated_task.progress
        }

    except Exception as e:
        logger.error(f"任务状态更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="任务状态更新失败，请稍后重试")


@router.post("/projects/{project_id}/tasks/{task_id}/notes")
async def add_task_note(
    project_id: str,
    task_id: str,
    note: TaskNoteCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    """添加任务备注"""
    task = task_manager.get_task(task_id)

    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_manager.add_task_note(
        task_id=task_id,
        user_id=current_user.id,
        user_name=current_user.username,
        content=note.content
    )

    return {"message": "备注添加成功"}


@router.post("/projects/{project_id}/tasks/auto-assign")
async def auto_assign_tasks(
    project_id: str,
    request: AutoAssignRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """自动分派任务"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    # 获取团队成员
    members = task_manager.get_team_members(project_id)

    if not members:
        raise HTTPException(status_code=400, detail="项目没有团队成员，请先添加成员")

    try:
        tasks = task_manager.auto_assign(
            project_id=project_id,
            sample_ids=request.sample_ids,
            team_members=members,
            strategy=request.strategy
        )

        return {
            "message": "自动分派成功",
            "task_count": len(tasks),
            "tasks": [
                {
                    "task_id": t.id,
                    "assignee_name": t.assignee_name,
                    "sample_count": len(t.sample_ids)
                }
                for t in tasks
            ]
        }

    except Exception as e:
        logger.error(f"任务自动分派失败: {str(e)}")
        raise HTTPException(status_code=500, detail="任务自动分派失败，请稍后重试")


@router.get("/projects/{project_id}/tasks/progress")
async def get_task_progress(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取任务进度"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    progress = task_manager.get_task_progress(project_id)

    return {
        "total_samples": progress.total_samples,
        "completed": progress.completed,
        "in_progress": progress.in_progress,
        "pending": progress.pending,
        "review": progress.review,
        "overdue": progress.overdue,
        "completion_rate": f"{progress.completion_rate * 100:.1f}%"
    }


@router.post("/projects/{project_id}/team-members", status_code=201)
async def add_team_member(
    project_id: str,
    member: TeamMemberCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    """添加团队成员"""
    # 验证项目存在
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    new_member = task_manager.add_team_member(
        project_id=project_id,
        name=member.name,
        role=member.role,
        email=member.email
    )

    return {
        "message": "成员添加成功",
        "member_id": new_member.id
    }


@router.get("/projects/{project_id}/team-members")
async def list_team_members(
    project_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取团队成员列表"""
    members = task_manager.get_team_members(project_id)

    return {
        "total": len(members),
        "items": [
            {
                "id": m.id,
                "name": m.name,
                "role": m.role,
                "email": m.email
            }
            for m in members
        ]
    }


@router.delete("/projects/{project_id}/tasks/{task_id}")
async def delete_task(
    project_id: str,
    task_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """删除任务"""
    task = task_manager.get_task(task_id)

    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_manager.delete_task(task_id)

    return {"message": "任务删除成功"}