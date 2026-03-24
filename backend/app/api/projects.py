"""
项目管理API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

from app.core.database import get_db_cursor, get_db

router = APIRouter()


# ==================== 数据模型 ====================

class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: Optional[str] = Field(None, max_length=500, description="项目描述")


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern="^(active|completed|archived)$")


class ProjectResponse(BaseModel):
    """项目响应"""
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    total: int
    items: List[ProjectResponse]


# ==================== API端点 ====================

@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[str] = Query(None, description="按状态筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取项目列表"""
    offset = (page - 1) * page_size

    with get_db_cursor() as cursor:
        # 构建查询条件
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if keyword:
            conditions.append("(name LIKE ? OR description LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询总数
        cursor.execute(f"SELECT COUNT(*) FROM projects WHERE {where_clause}", params)
        total = cursor.fetchone()[0]

        # 查询列表
        cursor.execute(
            f"""
            SELECT id, name, description, status, created_at, updated_at
            FROM projects
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset]
        )
        rows = cursor.fetchall()

        items = [
            ProjectResponse(
                id=row[0],
                name=row[1],
                description=row[2],
                status=row[3],
                created_at=row[4],
                updated_at=row[5]
            )
            for row in rows
        ]

        return ProjectListResponse(total=total, items=items)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate):
    """创建项目"""
    project_id = str(uuid.uuid4())
    now = datetime.now()

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO projects (id, name, description, status, created_at, updated_at)
            VALUES (?, ?, ?, 'active', ?, ?)
            """,
            [project_id, project.name, project.description, now, now]
        )
        get_db().commit()

        return ProjectResponse(
            id=project_id,
            name=project.name,
            description=project.description,
            status="active",
            created_at=now,
            updated_at=now
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """获取项目详情"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, description, status, created_at, updated_at
            FROM projects
            WHERE id = ?
            """,
            [project_id]
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="项目不存在")

        return ProjectResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            status=row[3],
            created_at=row[4],
            updated_at=row[5]
        )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project: ProjectUpdate):
    """更新项目"""
    now = datetime.now()

    with get_db_cursor() as cursor:
        # 检查项目是否存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 构建更新语句
        update_fields = []
        params = []

        if project.name is not None:
            update_fields.append("name = ?")
            params.append(project.name)

        if project.description is not None:
            update_fields.append("description = ?")
            params.append(project.description)

        if project.status is not None:
            update_fields.append("status = ?")
            params.append(project.status)

        if not update_fields:
            raise HTTPException(status_code=400, detail="没有要更新的字段")

        update_fields.append("updated_at = ?")
        params.append(now)
        params.append(project_id)

        cursor.execute(
            f"UPDATE projects SET {', '.join(update_fields)} WHERE id = ?",
            params
        )
        get_db().commit()

        # 返回更新后的数据
        cursor.execute(
            """
            SELECT id, name, description, status, created_at, updated_at
            FROM projects
            WHERE id = ?
            """,
            [project_id]
        )
        row = cursor.fetchone()

        return ProjectResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            status=row[3],
            created_at=row[4],
            updated_at=row[5]
        )


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """删除项目"""
    with get_db_cursor() as cursor:
        # 检查项目是否存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 删除关联数据
        cursor.execute("DELETE FROM samples WHERE project_id = ?", [project_id])
        cursor.execute("DELETE FROM vouchers WHERE project_id = ?", [project_id])
        cursor.execute("DELETE FROM sampling_rules WHERE project_id = ?", [project_id])
        cursor.execute("DELETE FROM risk_profiles WHERE project_id = ?", [project_id])
        cursor.execute("DELETE FROM audit_trail WHERE project_id = ?", [project_id])

        # 删除项目
        cursor.execute("DELETE FROM projects WHERE id = ?", [project_id])
        get_db().commit()

        return None