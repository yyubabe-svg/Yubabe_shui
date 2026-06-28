"""
合规初审模块 API 路由
提供项目管理、检查表模板、审核流程、评论、附件、统计等接口
"""
import asyncio
import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.user_usage import UserUsage
from app.api.routes.usage import get_current_user
from app.services.compliance_service import ComplianceService
from app.schemas.compliance import (
    ComplianceProjectCreate,
    ComplianceProjectUpdate,
    ComplianceProjectResponse,
    ComplianceProjectDetail,
    ComplianceProjectListResponse,
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
    ChecklistTemplateResponse,
    ComplianceReviewCreate,
    ComplianceReviewResponse,
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    AttachmentResponse,
    ComplianceStatistics,
    BatchAssignRequest,
)

router = APIRouter(prefix="/api/compliance", tags=["合规初审"])


def get_service(db: Session = Depends(get_db)) -> ComplianceService:
    """依赖注入：获取合规初审服务"""
    return ComplianceService(db)


# ============ 统计看板 ============

@router.get("/statistics", response_model=ComplianceStatistics, summary="获取合规初审统计数据")
async def get_statistics(
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """获取统计看板数据，包括项目数量、状态分布、通过率、趋势等"""
    return await asyncio.to_thread(service.get_statistics)


# ============ 项目管理 ============

@router.post("/projects", response_model=ComplianceProjectResponse, summary="创建初审项目")
async def create_project(
    project_in: ComplianceProjectCreate,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """
    创建新的合规初审项目
    - 可选择检查表模板，自动初始化检查表
    - 项目初始状态为草稿(draft)
    """
    try:
        project = await asyncio.to_thread(service.create_project, project_in)
        return project
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects", response_model=ComplianceProjectListResponse, summary="获取项目列表")
async def list_projects(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选：draft/submitted/reviewing/returned/passed/rejected/pending"),
    project_type: Optional[str] = Query(None, description="项目类型筛选"),
    priority: Optional[str] = Query(None, description="优先级筛选：low/normal/high/urgent"),
    keyword: Optional[str] = Query(None, description="关键词搜索（项目名称、编号、申报单位）"),
    reviewer_id: Optional[int] = Query(None, description="审核人ID"),
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """
    获取初审项目列表，支持分页和多条件筛选
    - pending状态表示待审核（包含submitted和reviewing）
    - 返回结果包含各状态的统计数量
    """
    items, total, statistics = await asyncio.to_thread(
        service.list_projects,
        page=page,
        page_size=page_size,
        status=status,
        project_type=project_type,
        priority=priority,
        keyword=keyword,
        reviewer_id=reviewer_id,
    )

    # 附加关联数量
    result_items = []
    for item in items:
        item.checklist_count = len(item.checklists) if hasattr(item, 'checklists') else 0
        item.attachment_count = len(item.attachments) if hasattr(item, 'attachments') else 0
        item.comment_count = len(item.comments) if hasattr(item, 'comments') else 0
        result_items.append(item)

    return ComplianceProjectListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        statistics=statistics,
    )


@router.get("/projects/{project_id}", response_model=ComplianceProjectDetail, summary="获取项目详情")
async def get_project(
    project_id: int,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """获取项目详情，包含检查表、审核记录、评论、附件等全部关联数据"""
    project = await asyncio.to_thread(service.get_project_with_details, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/projects/{project_id}", response_model=ComplianceProjectResponse, summary="更新项目信息")
async def update_project(
    project_id: int,
    project_in: ComplianceProjectUpdate,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """更新项目基本信息"""
    project = await asyncio.to_thread(service.update_project, project_id, project_in)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.delete("/projects/{project_id}", summary="删除项目")
async def delete_project(
    project_id: int,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """删除项目（级联删除所有关联数据）"""
    success = await asyncio.to_thread(service.delete_project, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"message": "删除成功"}


@router.post("/projects/{project_id}/submit-checklist", summary="为项目关联检查表模板")
async def apply_checklist_template(
    project_id: int,
    template_id: int = Form(...),
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """为已有项目应用检查表模板，创建检查表实例"""
    project = await asyncio.to_thread(service.get_project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        await asyncio.to_thread(service._create_checklist_from_template, project_id, template_id)
        service.db.commit()
        return {"message": "检查表模板应用成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ 审核流程 ============

@router.post("/projects/{project_id}/review", response_model=ComplianceProjectDetail, summary="执行审核操作")
async def process_review(
    project_id: int,
    review_in: ComplianceReviewCreate,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """
    执行审核流程操作：
    - submit: 提交审核（草稿→待审）
    - assign: 分配审核人（待审→审核中）
    - review: 填写审核结果（保存检查项评分）
    - return: 退回修改（审核中→退回）
    - pass: 审核通过（审核中→通过）
    - reject: 审核不通过（审核中→不通过）
    """
    try:
        user_id = None
        user_name = user.name
        user_dept = None

        await asyncio.to_thread(
            service.submit_review,
            project_id=project_id,
            review_in=review_in,
            user_id=user_id,
            user_name=user_name,
            user_dept=user_dept,
        )
        return await asyncio.to_thread(service.get_project_with_details, project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.get("/projects/{project_id}/reviews", response_model=List[ComplianceReviewResponse], summary="获取审核流程记录")
async def get_review_history(
    project_id: int,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """获取项目的审核操作历史记录"""
    project = await asyncio.to_thread(service.get_project_with_details, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project.reviews


@router.post("/projects/batch-assign", summary="批量分配审核人")
async def batch_assign(
    batch_in: BatchAssignRequest,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """批量为多个项目分配审核人"""
    success_count = 0
    for project_id in batch_in.project_ids:
        try:
            review_in = ComplianceReviewCreate(
                action="assign",
                reviewer_id=batch_in.reviewer_id,
                reviewer_name=batch_in.reviewer_name,
            )
            await asyncio.to_thread(service.submit_review, project_id, review_in)
            success_count += 1
        except Exception:
            pass
    return {"message": f"成功分配 {success_count}/{len(batch_in.project_ids)} 个项目"}


# ============ 检查表模板管理 ============

@router.post("/templates", response_model=ChecklistTemplateResponse, summary="创建检查表模板")
async def create_template(
    template_in: ChecklistTemplateCreate,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """创建检查表模板，可同时创建检查项"""
    template = await asyncio.to_thread(service.create_template, template_in)
    return template


@router.get("/templates", response_model=List[ChecklistTemplateResponse], summary="获取检查表模板列表")
async def list_templates(
    is_active: Optional[bool] = Query(None, description="是否仅返回启用的模板"),
    template_type: Optional[str] = Query(None, description="按项目类型筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """获取检查表模板列表"""
    templates = await asyncio.to_thread(
        service.list_templates, is_active=is_active, template_type=template_type, keyword=keyword
    )
    # 添加检查项数量
    for t in templates:
        t.item_count = len(t.items) if t.items else 0
    return templates


@router.get("/templates/{template_id}", response_model=ChecklistTemplateResponse, summary="获取检查表模板详情")
async def get_template(
    template_id: int,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """获取检查表模板详情（包含所有检查项）"""
    template = await asyncio.to_thread(service.get_template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    template.item_count = len(template.items) if template.items else 0
    return template


@router.put("/templates/{template_id}", response_model=ChecklistTemplateResponse, summary="更新检查表模板")
async def update_template(
    template_id: int,
    template_in: ChecklistTemplateUpdate,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """更新检查表模板基本信息"""
    template = await asyncio.to_thread(service.update_template, template_id, template_in)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.delete("/templates/{template_id}", summary="删除检查表模板")
async def delete_template(
    template_id: int,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """删除检查表模板（注意：已被项目使用的模板删除不影响已有项目数据）"""
    success = await asyncio.to_thread(service.delete_template, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"message": "删除成功"}


# ============ 评论/意见管理 ============

@router.post("/projects/{project_id}/comments", response_model=CommentResponse, summary="添加评论/意见")
async def add_comment(
    project_id: int,
    comment_in: CommentCreate,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """添加审核意见或沟通评论，支持回复功能"""
    project = await asyncio.to_thread(service.get_project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    user_id = None
    user_name = user.name
    user_dept = None

    comment = await asyncio.to_thread(
        service.add_comment, project_id, comment_in, user_id, user_name, user_dept
    )
    return comment


@router.get("/projects/{project_id}/comments", response_model=List[CommentResponse], summary="获取评论列表")
async def list_comments(
    project_id: int,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """获取项目的所有评论（树形结构）"""
    project = await asyncio.to_thread(service.get_project_with_details, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 过滤掉回复，只返回顶级评论
    top_comments = [c for c in project.comments if c.parent_id is None]
    return top_comments


@router.put("/comments/{comment_id}", response_model=CommentResponse, summary="更新评论")
async def update_comment(
    comment_id: int,
    comment_in: CommentUpdate,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """更新评论内容"""
    comment = await asyncio.to_thread(service.update_comment, comment_id, comment_in)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    return comment


@router.delete("/comments/{comment_id}", summary="删除评论")
async def delete_comment(
    comment_id: int,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """删除评论"""
    success = await asyncio.to_thread(service.delete_comment, comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="评论不存在")
    return {"message": "删除成功"}


# ============ 附件管理 ============

@router.post("/projects/{project_id}/attachments", response_model=AttachmentResponse, summary="上传附件")
async def upload_attachment(
    project_id: int,
    file: UploadFile = File(...),
    file_type: Optional[str] = Form(None, description="文件类型：申报文件/资质证明/技术资料/审核报告/其他"),
    category: Optional[str] = Form(None, description="附件分类"),
    description: Optional[str] = Form(None, description="附件说明"),
    is_required: bool = Form(False, description="是否必备文件"),
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """上传项目相关附件（aiofiles异步分块写入，UUID文件名，路径遍历防护）"""
    project = await asyncio.to_thread(service.get_project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 创建上传目录
    upload_dir = os.path.join(settings.UPLOAD_DIR, "compliance", str(project_id))
    os.makedirs(upload_dir, exist_ok=True)

    # 生成唯一文件名（UUID，防路径遍历）
    file_ext = os.path.splitext(file.filename or "")[1]
    # 禁止.doc格式
    if file_ext.lower() == ".doc":
        raise HTTPException(status_code=400, detail="不支持.doc格式，请转换为.docx或PDF后上传")
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    # 路径遍历防护
    upload_dir_real = os.path.realpath(upload_dir)
    file_path_real = os.path.realpath(file_path)
    if not file_path_real.startswith(upload_dir_real + os.sep):
        raise HTTPException(status_code=400, detail="非法文件路径")

    # aiofiles异步分块写入
    file_size = 0
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)
            file_size += len(chunk)
            if file_size > 50 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="文件大小超过限制(50MB)")

    uploader_id = None
    uploader_name = user.name

    attachment = await asyncio.to_thread(
        service.add_attachment,
        project_id=project_id,
        file_name=file.filename or unique_filename,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
        mime_type=file.content_type,
        category=category,
        uploader_id=uploader_id,
        uploader_name=uploader_name,
        description=description,
        is_required=is_required,
    )

    return attachment


@router.delete("/attachments/{attachment_id}", summary="删除附件")
async def delete_attachment(
    attachment_id: int,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """删除附件（同时删除物理文件）"""
    success = await asyncio.to_thread(service.delete_attachment, attachment_id)
    if not success:
        raise HTTPException(status_code=404, detail="附件不存在")
    return {"message": "删除成功"}


# ============ 报告生成 ============

@router.get("/projects/{project_id}/report", summary="生成初审报告")
async def generate_report(
    project_id: int,
    service: ComplianceService = Depends(get_service),
    user: UserUsage = Depends(get_current_user),
):
    """生成合规初审报告数据（用于前端展示或导出）"""
    try:
        report_data = await asyncio.to_thread(service.generate_review_report, project_id)
        return report_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")
