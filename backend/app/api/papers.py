"""
工作底稿 API
"""
import logging
import urllib.parse

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db_cursor
from app.core.auth import get_current_user, UserInDB
from app.services.working_paper_service import (
    working_paper_generator, PaperType, WorkingPaper
)
from app.services.export_service import excel_exporter, pdf_exporter

router = APIRouter()

logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

class PaperGenerateRequest(BaseModel):
    """生成底稿请求"""
    paper_type: str = Field(..., description="底稿类型")
    subject_code: Optional[str] = Field(None, description="科目代码 (实质性测试需要)")
    include_ai_description: bool = Field(default=True, description="是否包含 AI 描述")


class PaperUpdateRequest(BaseModel):
    """更新底稿请求"""
    title: Optional[str] = Field(None, description="标题")
    ai_description: Optional[str] = Field(None, description="AI 描述")


# ==================== API 端点 ====================

@router.post("/projects/{project_id}/papers/generate")
async def generate_paper(
    project_id: str,
    request: PaperGenerateRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """生成工作底稿"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    try:
        paper_type = PaperType(request.paper_type)

        if paper_type == PaperType.SAMPLING_SUMMARY:
            paper = working_paper_generator.generate_sampling_summary(
                project_id=project_id,
                include_ai_description=request.include_ai_description
            )

        elif paper_type == PaperType.SUBSTANTIVE_TEST:
            if not request.subject_code:
                raise HTTPException(status_code=400, detail="实质性测试需要指定科目代码")

            paper = working_paper_generator.generate_substantive_test(
                project_id=project_id,
                subject_code=request.subject_code
            )

        else:
            raise HTTPException(status_code=400, detail=f"暂不支持生成{request.paper_type}类型底稿")

        return {
            "message": "底稿生成成功",
            "paper_id": paper.id,
            "title": paper.title,
            "paper_type": paper.paper_type.value,
            "section_count": len(paper.sections)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"底稿生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail="底稿生成失败，请稍后重试")


@router.get("/projects/{project_id}/papers")
async def list_papers(
    project_id: str,
    paper_type: Optional[str] = Query(None, description="按类型筛选"),
    current_user: UserInDB = Depends(get_current_user)
):
    """获取底稿列表"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

    papers = working_paper_generator.get_project_papers(project_id)

    if paper_type:
        papers = [p for p in papers if p.paper_type.value == paper_type]

    return {
        "total": len(papers),
        "items": [
            {
                "id": p.id,
                "title": p.title,
                "paper_type": p.paper_type.value,
                "created_at": str(p.created_at),
                "updated_at": str(p.updated_at)
            }
            for p in papers
        ]
    }


@router.get("/projects/{project_id}/papers/{paper_id}")
async def get_paper(
    project_id: str,
    paper_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """获取底稿详情"""
    paper = working_paper_generator.get_paper(paper_id)

    if not paper or paper.project_id != project_id:
        raise HTTPException(status_code=404, detail="底稿不存在")

    return {
        "id": paper.id,
        "project_id": paper.project_id,
        "paper_type": paper.paper_type.value,
        "title": paper.title,
        "sections": [
            {
                "title": s.title,
                "content": s.content,
                "order": s.order
            }
            for s in paper.sections
        ],
        "ai_description": paper.ai_description,
        "created_at": str(paper.created_at),
        "updated_at": str(paper.updated_at)
    }


@router.put("/projects/{project_id}/papers/{paper_id}")
async def update_paper(
    project_id: str,
    paper_id: str,
    update: PaperUpdateRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """更新底稿"""
    paper = working_paper_generator.get_paper(paper_id)

    if not paper or paper.project_id != project_id:
        raise HTTPException(status_code=404, detail="底稿不存在")

    if update.title:
        paper.title = update.title

    if update.ai_description is not None:
        paper.ai_description = update.ai_description

    working_paper_generator.update_paper(paper)

    return {"message": "底稿更新成功"}


@router.delete("/projects/{project_id}/papers/{paper_id}")
async def delete_paper(
    project_id: str,
    paper_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """删除底稿"""
    paper = working_paper_generator.get_paper(paper_id)

    if not paper or paper.project_id != project_id:
        raise HTTPException(status_code=404, detail="底稿不存在")

    working_paper_generator.delete_paper(paper_id)

    return {"message": "底稿删除成功"}


def _make_content_disposition(filename: str) -> str:
    """构建安全的 Content-Disposition 头值"""
    encoded = urllib.parse.quote(filename)
    return f"attachment; filename*=UTF-8''{encoded}"


@router.get("/projects/{project_id}/papers/{paper_id}/export")
async def export_paper(
    project_id: str,
    paper_id: str,
    format: str = Query("pdf", description="导出格式：pdf/excel"),
    current_user: UserInDB = Depends(get_current_user)
):
    """导出底稿"""
    paper = working_paper_generator.get_paper(paper_id)

    if not paper or paper.project_id != project_id:
        raise HTTPException(status_code=404, detail="底稿不存在")

    try:
        if format == "pdf":
            if not pdf_exporter.available:
                raise RuntimeError("PDF 导出库未安装，请安装 reportlab: pip install reportlab")

            with get_db_cursor() as cursor:
                cursor.execute(
                    "SELECT id, name FROM projects WHERE id = ?",
                    [project_id]
                )
                project = cursor.fetchone()

            sections_data = []
            for s in paper.sections:
                sections_data.append({
                    "title": s.title,
                    "content": s.content or "",
                    "order": s.order
                })

            paper_data = {
                "title": paper.title,
                "paper_type": paper.paper_type.value,
                "sections": sections_data,
                "ai_description": paper.ai_description or ""
            }
            project_info = {"id": project[0], "name": project[1]} if project else None

            logger.info(f"Exporting paper: title={paper.title}, sections={len(sections_data)}")

            file_data = pdf_exporter.export_working_paper(
                paper=paper_data,
                project_info=project_info
            )
            filename = f"{paper.title}.pdf"
            media_type = "application/pdf"
            logger.info(f"PDF exported successfully: {len(file_data)} bytes")
        else:
            file_data = excel_exporter.export_project_summary(project_id)
            filename = f"{paper.title}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        return Response(
            content=file_data,
            media_type=media_type,
            headers={
                "Content-Disposition": _make_content_disposition(filename)
            }
        )

    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"Export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Export error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="导出失败，请稍后重试")


@router.get("/paper-types")
async def list_paper_types(current_user: UserInDB = Depends(get_current_user)):
    """获取底稿类型列表"""
    return {
        "items": [
            {"value": "sampling_summary", "label": "抽样情况汇总表"},
            {"value": "substantive_test", "label": "实质性程序测试底稿"},
            {"value": "compliance_test", "label": "合规性测试底稿"},
            {"value": "risk_assessment", "label": "风险评估底稿"},
            {"value": "three_way_match", "label": "三单匹配核对底稿"},
            {"value": "audit_adjustment", "label": "审计调整底稿"},
            {"value": "management_letter", "label": "管理建议书"}
        ]
    }
