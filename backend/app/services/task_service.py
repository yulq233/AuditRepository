"""
任务分派与追踪服务
将抽样样本分派给项目组成员，实时追踪抽凭进度
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import uuid

from app.core.database import get_db_cursor, get_db


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"            # 待分派
    ASSIGNED = "assigned"          # 已分派
    IN_PROGRESS = "in_progress"    # 进行中
    REVIEW = "review"              # 待复核
    COMPLETED = "completed"        # 已完成
    BLOCKED = "blocked"            # 阻塞
    OVERDUE = "overdue"            # 超时


class TaskPriority(str, Enum):
    """任务优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AuditTask:
    """审计任务"""
    id: str
    project_id: str
    title: str
    description: str
    sample_ids: List[str]
    assignee_id: str
    assignee_name: str
    reviewer_id: Optional[str]
    reviewer_name: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    deadline: Optional[datetime]
    progress: int
    notes: List[Dict[str, Any]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


@dataclass
class TaskProgress:
    """任务进度"""
    project_id: str
    total_samples: int
    completed: int
    in_progress: int
    pending: int
    review: int
    overdue: int
    completion_rate: float


@dataclass
class TeamMember:
    """团队成员"""
    id: str
    name: str
    role: str
    email: Optional[str]


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """确保必要的表存在"""
        with get_db_cursor() as cursor:
            # 团队成员表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS team_members (
                    id VARCHAR PRIMARY KEY,
                    project_id VARCHAR,
                    name VARCHAR NOT NULL,
                    role VARCHAR,
                    email VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 任务备注表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_notes (
                    id VARCHAR PRIMARY KEY,
                    task_id VARCHAR,
                    user_id VARCHAR,
                    user_name VARCHAR,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            get_db().commit()

    def create_task(
        self,
        project_id: str,
        title: str,
        description: str,
        sample_ids: List[str],
        assignee_id: str,
        assignee_name: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        deadline: datetime = None,
        reviewer_id: str = None,
        reviewer_name: str = None
    ) -> AuditTask:
        """
        创建审计任务

        Args:
            project_id: 项目ID
            title: 任务标题
            description: 任务描述
            sample_ids: 样本ID列表
            assignee_id: 被分派人ID
            assignee_name: 被分派人姓名
            priority: 优先级
            deadline: 截止时间
            reviewer_id: 复核人ID
            reviewer_name: 复核人姓名

        Returns:
            AuditTask: 创建的任务
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_tasks
                (id, project_id, sample_ids, assignee_id, assignee_name,
                 status, deadline, priority, progress, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    task_id,
                    project_id,
                    json.dumps(sample_ids),
                    assignee_id,
                    assignee_name,
                    TaskStatus.ASSIGNED.value,
                    deadline,
                    priority.value,
                    0,
                    now
                ]
            )
            get_db().commit()

        return AuditTask(
            id=task_id,
            project_id=project_id,
            title=title,
            description=description,
            sample_ids=sample_ids,
            assignee_id=assignee_id,
            assignee_name=assignee_name,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            status=TaskStatus.ASSIGNED,
            priority=priority,
            deadline=deadline,
            progress=0,
            notes=[],
            created_at=now,
            started_at=None,
            completed_at=None
        )

    def assign_samples(
        self,
        project_id: str,
        sample_ids: List[str],
        assignee_id: str,
        assignee_name: str,
        deadline: datetime = None
    ) -> AuditTask:
        """
        分派样本给审计人员

        Args:
            project_id: 项目ID
            sample_ids: 样本ID列表
            assignee_id: 被分派人ID
            assignee_name: 被分派人姓名
            deadline: 截止时间

        Returns:
            AuditTask: 创建的任务
        """
        title = f"抽凭任务 - {len(sample_ids)}个样本"
        description = f"请完成{len(sample_ids)}个样本的审计抽查工作"

        return self.create_task(
            project_id=project_id,
            title=title,
            description=description,
            sample_ids=sample_ids,
            assignee_id=assignee_id,
            assignee_name=assignee_name,
            deadline=deadline
        )

    def auto_assign(
        self,
        project_id: str,
        sample_ids: List[str],
        team_members: List[TeamMember],
        strategy: str = "balanced"
    ) -> List[AuditTask]:
        """
        自动分派任务

        Args:
            project_id: 项目ID
            sample_ids: 样本ID列表
            team_members: 团队成员列表
            strategy: 分派策略 (balanced/round_robin/workload)

        Returns:
            List[AuditTask]: 创建的任务列表
        """
        tasks = []

        if strategy == "balanced":
            # 平均分配
            chunk_size = len(sample_ids) // len(team_members)
            remainder = len(sample_ids) % len(team_members)

            start = 0
            for i, member in enumerate(team_members):
                # 最后一个成员分配剩余样本
                end = start + chunk_size + (remainder if i == len(team_members) - 1 else 0)
                member_samples = sample_ids[start:end]

                if member_samples:
                    task = self.assign_samples(
                        project_id=project_id,
                        sample_ids=member_samples,
                        assignee_id=member.id,
                        assignee_name=member.name
                    )
                    tasks.append(task)

                start = end

        elif strategy == "round_robin":
            # 轮询分配
            member_samples = {m.id: [] for m in team_members}
            member_names = {m.id: m.name for m in team_members}

            for i, sample_id in enumerate(sample_ids):
                member = team_members[i % len(team_members)]
                member_samples[member.id].append(sample_id)

            for member in team_members:
                if member_samples[member.id]:
                    task = self.assign_samples(
                        project_id=project_id,
                        sample_ids=member_samples[member.id],
                        assignee_id=member.id,
                        assignee_name=member.name
                    )
                    tasks.append(task)

        elif strategy == "workload":
            # 按工作量分配（假设成员有权重）
            # 简化实现：与balanced相同
            tasks = self.auto_assign(project_id, sample_ids, team_members, "balanced")

        return tasks

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int = None
    ) -> Optional[AuditTask]:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度百分比

        Returns:
            AuditTask: 更新后的任务
        """
        now = datetime.now()

        with get_db_cursor() as cursor:
            # 获取当前任务
            cursor.execute(
                "SELECT id, project_id, sample_ids, assignee_id, assignee_name, status FROM audit_tasks WHERE id = ?",
                [task_id]
            )
            row = cursor.fetchone()
            if not row:
                return None

            old_status = TaskStatus(row[5])

            # 更新状态
            updates = ["status = ?"]
            params = [status.value]

            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)

            if status == TaskStatus.IN_PROGRESS and old_status != TaskStatus.IN_PROGRESS:
                updates.append("started_at = ?")
                params.append(now)

            if status == TaskStatus.COMPLETED:
                updates.append("completed_at = ?")
                params.append(now)

            params.append(task_id)

            cursor.execute(
                f"UPDATE audit_tasks SET {', '.join(updates)} WHERE id = ?",
                params
            )
            get_db().commit()

        return self.get_task(task_id)

    def add_task_note(
        self,
        task_id: str,
        user_id: str,
        user_name: str,
        content: str
    ):
        """
        添加任务备注

        Args:
            task_id: 任务ID
            user_id: 用户ID
            user_name: 用户名
            content: 备注内容
        """
        note_id = str(uuid.uuid4())

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO task_notes (id, task_id, user_id, user_name, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                [note_id, task_id, user_id, user_name, content]
            )
            get_db().commit()

    def get_task(self, task_id: str) -> Optional[AuditTask]:
        """获取任务详情"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, sample_ids, assignee_id, assignee_name,
                       status, deadline, priority, progress, created_at, started_at, completed_at
                FROM audit_tasks
                WHERE id = ?
                """,
                [task_id]
            )
            row = cursor.fetchone()

            if not row:
                return None

            # 获取备注
            cursor.execute(
                """
                SELECT user_id, user_name, content, created_at
                FROM task_notes
                WHERE task_id = ?
                ORDER BY created_at DESC
                """,
                [task_id]
            )
            notes = [
                {
                    "user_id": n[0],
                    "user_name": n[1],
                    "content": n[2],
                    "created_at": str(n[3])
                }
                for n in cursor.fetchall()
            ]

            return AuditTask(
                id=row[0],
                project_id=row[1],
                title="",
                description="",
                sample_ids=json.loads(row[2]) if isinstance(row[2], str) else row[2],
                assignee_id=row[3],
                assignee_name=row[4],
                reviewer_id=None,
                reviewer_name=None,
                status=TaskStatus(row[5]),
                priority=TaskPriority(row[7]) if row[7] else TaskPriority.MEDIUM,
                deadline=row[6],
                progress=row[8] or 0,
                notes=notes,
                created_at=row[9],
                started_at=row[10],
                completed_at=row[11]
            )

    def get_project_tasks(
        self,
        project_id: str,
        status: TaskStatus = None,
        assignee_id: str = None
    ) -> List[AuditTask]:
        """获取项目任务列表"""
        with get_db_cursor() as cursor:
            conditions = ["project_id = ?"]
            params = [project_id]

            if status:
                conditions.append("status = ?")
                params.append(status.value)

            if assignee_id:
                conditions.append("assignee_id = ?")
                params.append(assignee_id)

            where_clause = " AND ".join(conditions)

            cursor.execute(
                f"""
                SELECT id, project_id, sample_ids, assignee_id, assignee_name,
                       status, deadline, priority, progress, created_at, started_at, completed_at
                FROM audit_tasks
                WHERE {where_clause}
                ORDER BY
                    CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                    END,
                    deadline ASC
                """,
                params
            )
            rows = cursor.fetchall()

            return [
                AuditTask(
                    id=row[0],
                    project_id=row[1],
                    title="",
                    description="",
                    sample_ids=json.loads(row[2]) if isinstance(row[2], str) else row[2],
                    assignee_id=row[3],
                    assignee_name=row[4],
                    reviewer_id=None,
                    reviewer_name=None,
                    status=TaskStatus(row[5]),
                    priority=TaskPriority(row[7]) if row[7] else TaskPriority.MEDIUM,
                    deadline=row[6],
                    progress=row[8] or 0,
                    notes=[],
                    created_at=row[9],
                    started_at=row[10],
                    completed_at=row[11]
                )
                for row in rows
            ]

    def get_task_progress(self, project_id: str) -> TaskProgress:
        """获取项目任务进度"""
        with get_db_cursor() as cursor:
            # 统计各状态任务数
            cursor.execute(
                """
                SELECT status, COUNT(*)
                FROM audit_tasks
                WHERE project_id = ?
                GROUP BY status
                """,
                [project_id]
            )
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # 统计样本总数
            cursor.execute(
                "SELECT COUNT(*) FROM samples WHERE project_id = ?",
                [project_id]
            )
            total_samples = cursor.fetchone()[0] or 0

            # 统计已完成样本数
            cursor.execute(
                """
                SELECT SUM(JSON_ARRAY_LENGTH(sample_ids))
                FROM audit_tasks
                WHERE project_id = ? AND status = 'completed'
                """,
                [project_id]
            )
            completed_samples = cursor.fetchone()[0] or 0

            # 统计超时任务
            cursor.execute(
                """
                SELECT COUNT(*) FROM audit_tasks
                WHERE project_id = ?
                  AND status NOT IN ('completed')
                  AND deadline < ?
                """,
                [project_id, datetime.now()]
            )
            overdue = cursor.fetchone()[0] or 0

            completion_rate = completed_samples / total_samples if total_samples > 0 else 0

            return TaskProgress(
                project_id=project_id,
                total_samples=total_samples,
                completed=completed_samples,
                in_progress=status_counts.get("in_progress", 0),
                pending=status_counts.get("pending", 0) + status_counts.get("assigned", 0),
                review=status_counts.get("review", 0),
                overdue=overdue,
                completion_rate=completion_rate
            )

    def get_user_tasks(
        self,
        user_id: str,
        status: TaskStatus = None
    ) -> List[AuditTask]:
        """获取用户的任务列表"""
        with get_db_cursor() as cursor:
            conditions = ["assignee_id = ?"]
            params = [user_id]

            if status:
                conditions.append("status = ?")
                params.append(status.value)

            where_clause = " AND ".join(conditions)

            cursor.execute(
                f"""
                SELECT id, project_id, sample_ids, assignee_id, assignee_name,
                       status, deadline, priority, progress, created_at, started_at, completed_at
                FROM audit_tasks
                WHERE {where_clause}
                ORDER BY deadline ASC
                """,
                params
            )
            rows = cursor.fetchall()

            return [
                AuditTask(
                    id=row[0],
                    project_id=row[1],
                    title="",
                    description="",
                    sample_ids=json.loads(row[2]) if isinstance(row[2], str) else row[2],
                    assignee_id=row[3],
                    assignee_name=row[4],
                    reviewer_id=None,
                    reviewer_name=None,
                    status=TaskStatus(row[5]),
                    priority=TaskPriority(row[7]) if row[7] else TaskPriority.MEDIUM,
                    deadline=row[6],
                    progress=row[8] or 0,
                    notes=[],
                    created_at=row[9],
                    started_at=row[10],
                    completed_at=row[11]
                )
                for row in rows
            ]

    def add_team_member(
        self,
        project_id: str,
        name: str,
        role: str,
        email: str = None
    ) -> TeamMember:
        """添加团队成员"""
        member_id = str(uuid.uuid4())

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO team_members (id, project_id, name, role, email)
                VALUES (?, ?, ?, ?, ?)
                """,
                [member_id, project_id, name, role, email]
            )
            get_db().commit()

        return TeamMember(
            id=member_id,
            name=name,
            role=role,
            email=email
        )

    def get_team_members(self, project_id: str) -> List[TeamMember]:
        """获取项目团队成员"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, role, email
                FROM team_members
                WHERE project_id = ?
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            return [
                TeamMember(
                    id=row[0],
                    name=row[1],
                    role=row[2],
                    email=row[3]
                )
                for row in rows
            ]

    def reassign_task(
        self,
        task_id: str,
        new_assignee_id: str,
        new_assignee_name: str
    ) -> Optional[AuditTask]:
        """重新分派任务"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE audit_tasks
                SET assignee_id = ?, assignee_name = ?
                WHERE id = ?
                """,
                [new_assignee_id, new_assignee_name, task_id]
            )
            get_db().commit()

        return self.get_task(task_id)

    def delete_task(self, task_id: str):
        """删除任务"""
        with get_db_cursor() as cursor:
            # 删除相关备注
            cursor.execute("DELETE FROM task_notes WHERE task_id = ?", [task_id])
            # 删除任务
            cursor.execute("DELETE FROM audit_tasks WHERE id = ?", [task_id])
            get_db().commit()

    def check_overdue_tasks(self, project_id: str) -> List[AuditTask]:
        """检查超时任务"""
        now = datetime.now()

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, sample_ids, assignee_id, assignee_name,
                       status, deadline, priority, progress, created_at, started_at, completed_at
                FROM audit_tasks
                WHERE project_id = ?
                  AND status NOT IN ('completed')
                  AND deadline < ?
                """,
                [project_id, now]
            )
            rows = cursor.fetchall()

            tasks = []
            for row in rows:
                # 更新状态为超时
                cursor.execute(
                    "UPDATE audit_tasks SET status = ? WHERE id = ?",
                    [TaskStatus.OVERDUE.value, row[0]]
                )

                tasks.append(AuditTask(
                    id=row[0],
                    project_id=row[1],
                    title="",
                    description="",
                    sample_ids=json.loads(row[2]) if isinstance(row[2], str) else row[2],
                    assignee_id=row[3],
                    assignee_name=row[4],
                    reviewer_id=None,
                    reviewer_name=None,
                    status=TaskStatus.OVERDUE,
                    priority=TaskPriority(row[7]) if row[7] else TaskPriority.MEDIUM,
                    deadline=row[6],
                    progress=row[8] or 0,
                    notes=[],
                    created_at=row[9],
                    started_at=row[10],
                    completed_at=row[11]
                ))

            get_db().commit()

        return tasks


# 全局服务实例
task_manager = TaskManager()