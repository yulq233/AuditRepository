"""
API路由模块
"""
from app.api import projects, vouchers, sampling, ai, auth, files, tasks, papers, audit_trail, crawler, compliance, risk, matching

__all__ = [
    "projects",
    "vouchers",
    "sampling",
    "ai",
    "auth",
    "files",
    "tasks",
    "papers",
    "audit_trail",
    "crawler",
    "compliance",
    "risk",
    "matching"
]