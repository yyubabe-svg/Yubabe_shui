"""工作台API路由 - 整合表单填报、AI初审、章节生成、专家回复"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.params import Body
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel
import json
import os
import uuid

from app.core.database import get_db, SessionLocal
from app.models.form_template import FormTemplate, FormFillTask, FormFillStatus, FormFillFieldValue, FormField
from app.models.report_section import ReportSectionTemplate, ReportSectionTask, ReportSectionDraft, SectionTaskStatus
from app.models.ai_review import AIReviewTask, AIReviewIssue, ReviewStatus, IssueStatus
from app.models.expert_reply import ExpertReplyTask, ExpertOpinion, ExpertReplyItem, ReplyTaskStatus
from app.models.document import Document

router = APIRouter(prefix="/api/workspace", tags=["项目工作台"])


# ========== 请求体模型 ==========

class CreateFormTaskRequest(BaseModel):
    template_id: int
    document_id: int


class CreateReviewTaskRequest(BaseModel):
    document_id: int
    dimensions: Optional[List[str]] = None


class CreateSectionTaskRequest(BaseModel):
    template_id: int
    document_ids: Optional[List[int]] = None
    params: Optional[dict] = None


class CreateExpertReplyTaskRequest(BaseModel):
    opinion_document_id: int
    report_document_id: Optional[int] = None
    meeting_name: Optional[str] = None
    meeting_date: Optional[str] = None


class UpdateFormFieldsRequest(BaseModel):
    fields: dict


# ========== 表单填报 ==========

@router.get("/form-templates")
async def list_form_templates(
    project_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取表单模板列表"""
    query = db.query(FormTemplate).filter(FormTemplate.is_active == True)
    templates = query.order_by(FormTemplate.sort_order, FormTemplate.id).all()
    return {
        "items": [
            {
                "id": t.id,
                "template_code": t.template_code,
                "template_name": t.template_name,
                "template_type": t.template_type,
                "description": t.description,
                "version": t.version,
                "field_count": len(t.fields)
            }
            for t in templates
        ]
    }


@router.post("/projects/{project_id}/form-tasks")
async def create_form_task(
    project_id: int,
    data: CreateFormTaskRequest,
    db: Session = Depends(get_db)
):
    """创建表单填报任务"""
    from app.services.form_fill_engine import form_fill_engine
    task = form_fill_engine.create_task(
        project_id=project_id,
        template_id=data.template_id,
        document_id=data.document_id,
        created_by="system"
    )
    return {"task_id": task.id, "status": task.status}


@router.post("/form-tasks/{task_id}/extract")
async def extract_form_fields(task_id: int, db: Session = Depends(get_db)):
    """执行字段提取"""
    from app.services.form_fill_engine import form_fill_engine
    result = await form_fill_engine.extract_fields(task_id)
    return result


@router.get("/form-tasks/{task_id}")
async def get_form_task(task_id: int, db: Session = Depends(get_db)):
    """获取填报任务详情"""
    task = db.query(FormFillTask).filter(FormFillTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    field_values = db.query(FormFillFieldValue).filter(FormFillFieldValue.task_id == task_id).all()
    fields = db.query(FormField).filter(FormField.template_id == task.template_id).order_by(FormField.sort_order).all()
    
    field_map = {f.id: f for f in fields}
    
    return {
        "id": task.id,
        "project_id": task.project_id,
        "template_id": task.template_id,
        "template_name": task.template.template_name if task.template else "",
        "document_id": task.document_id,
        "status": task.status,
        "progress": task.progress,
        "error_message": task.error_message,
        "output_filename": task.output_filename,
        "fields": [
            {
                "id": fv.id,
                "field_id": fv.field_id,
                "field_key": field_map.get(fv.field_id).field_key if field_map.get(fv.field_id) else "",
                "field_label": field_map.get(fv.field_id).field_label if field_map.get(fv.field_id) else "",
                "field_type": field_map.get(fv.field_id).field_type if field_map.get(fv.field_id) else "text",
                "required": field_map.get(fv.field_id).required if field_map.get(fv.field_id) else True,
                "extracted_value": fv.extracted_value,
                "confirmed_value": fv.confirmed_value or fv.extracted_value,
                "confidence": fv.confidence,
                "source_page": fv.source_page,
                "source_section": fv.source_section,
                "source_text": fv.source_text,
            }
            for fv in field_values
        ],
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.put("/form-tasks/{task_id}/fields")
async def update_form_fields(task_id: int, data: UpdateFormFieldsRequest, db: Session = Depends(get_db)):
    """更新确认后的字段值"""
    task = db.query(FormFillTask).filter(FormFillTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    fields_data = data.fields or {}
    for field_id_str, value in fields_data.items():
        field_id = int(field_id_str)
        fv = db.query(FormFillFieldValue).filter(
            FormFillFieldValue.task_id == task_id,
            FormFillFieldValue.field_id == field_id
        ).first()
        if fv:
            fv.confirmed_value = value
    
    db.commit()
    return {"message": "字段已更新"}


@router.post("/form-tasks/{task_id}/fill")
async def fill_form_template(task_id: int, db: Session = Depends(get_db)):
    """执行模板填充"""
    from app.services.form_fill_engine import form_fill_engine
    
    task = db.query(FormFillTask).filter(FormFillTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取确认数据
    field_values = db.query(FormFillFieldValue).filter(FormFillFieldValue.task_id == task_id).all()
    confirmed_data = {}
    fields = db.query(FormField).filter(FormField.template_id == task.template_id).all()
    field_map = {f.id: f for f in fields}
    
    for fv in field_values:
        field = field_map.get(fv.field_id)
        if field:
            confirmed_data[field.field_key] = fv.confirmed_value or fv.extracted_value
    
    result = await asyncio.to_thread(form_fill_engine.fill_template, task_id, confirmed_data)
    result["download_url"] = f"/api/workspace/form-tasks/{task_id}/download"
    return result


@router.get("/form-tasks/{task_id}/download")
async def download_form_result(task_id: int, db: Session = Depends(get_db)):
    """下载生成的表格"""
    task = db.query(FormFillTask).filter(FormFillTask.id == task_id).first()
    if not task or not task.output_file_path:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not os.path.exists(task.output_file_path):
        raise HTTPException(status_code=404, detail="文件已删除")
    
    return FileResponse(
        task.output_file_path,
        filename=task.output_filename or "generated.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@router.get("/projects/{project_id}/form-tasks")
async def list_project_form_tasks(project_id: int, db: Session = Depends(get_db)):
    """获取项目的表单填报任务列表"""
    tasks = db.query(FormFillTask).filter(FormFillTask.project_id == project_id).order_by(desc(FormFillTask.created_at)).all()
    return {
        "items": [
            {
                "id": t.id,
                "template_name": t.template.template_name if t.template else "",
                "status": t.status,
                "progress": t.progress,
                "output_filename": t.output_filename,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]
    }


# ========== AI初审 ==========

@router.post("/projects/{project_id}/review-tasks")
async def create_review_task(
    project_id: int,
    data: CreateReviewTaskRequest,
    db: Session = Depends(get_db)
):
    """创建AI初审任务"""
    doc = db.query(Document).filter(Document.id == data.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    task = AIReviewTask(
        project_id=project_id,
        document_id=data.document_id,
        review_dimensions=data.dimensions or ["param_completeness", "code_compliance", "chapter_completeness", "value_consistency", "format_standard"],
        status=ReviewStatus.PENDING.value,
        progress=0,
        created_by="system"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"task_id": task.id}


@router.post("/review-tasks/{task_id}/run")
async def run_review(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """执行AI初审（后台任务）"""
    def _run_review_sync():
        asyncio.run(_run_review_bg())
    
    async def _run_review_bg():
        db_session = SessionLocal()
        try:
            from app.services.ai_review_engine import AIReviewEngine
            engine = AIReviewEngine(db_session)
            async for event in engine.run_review(task_id):
                pass  # 后台运行，事件不推送
        except Exception as e:
            print(f"审查任务失败: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(_run_review_sync)
    
    task = db.query(AIReviewTask).filter(AIReviewTask.id == task_id).first()
    if task:
        task.status = ReviewStatus.REVIEWING.value
        db.commit()
    
    return {"message": "审查已开始"}


@router.get("/review-tasks/{task_id}/stream")
async def stream_review_progress(task_id: int, db: Session = Depends(get_db)):
    """SSE流式审查进度（轮询模拟）"""
    async def event_generator():
        while True:
            db_session = SessionLocal()
            try:
                task = db_session.query(AIReviewTask).filter(AIReviewTask.id == task_id).first()
                if not task:
                    yield f"data: {json.dumps({'event': 'error', 'message': '任务不存在'})}\n\n"
                    break
                
                yield f"data: {json.dumps({'event': 'progress', 'progress': task.progress or 0, 'current_chapter': task.current_chapter})}\n\n"
                
                if task.status in [ReviewStatus.COMPLETED.value, ReviewStatus.FAILED.value]:
                    if task.status == ReviewStatus.COMPLETED.value:
                        yield f"data: {json.dumps({'event': 'done', 'total_score': task.total_score, 'summary': task.summary})}\n\n"
                    else:
                        yield f"data: {json.dumps({'event': 'error', 'message': task.error_message})}\n\n"
                    break
            finally:
                db_session.close()
            
            await asyncio.sleep(1)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/review-tasks/{task_id}")
async def get_review_task(task_id: int, db: Session = Depends(get_db)):
    """获取AI初审结果"""
    task = db.query(AIReviewTask).filter(AIReviewTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    issues = db.query(AIReviewIssue).filter(AIReviewIssue.review_task_id == task_id).order_by(AIReviewIssue.severity_order, AIReviewIssue.id).all()
    
    return {
        "id": task.id,
        "project_id": task.project_id,
        "document_id": task.document_id,
        "document_title": task.document.title if task.document else "",
        "status": task.status,
        "progress": task.progress,
        "total_score": task.total_score,
        "summary": task.summary,
        "issue_count_critical": task.issue_count_critical,
        "issue_count_major": task.issue_count_major,
        "issue_count_minor": task.issue_count_minor,
        "issue_count_suggestion": task.issue_count_suggestion,
        "issues": [
            {
                "id": i.id,
                "severity": i.severity,
                "category": i.category,
                "chapter_path": i.chapter_path,
                "page_number": i.page_number,
                "location_desc": i.location_desc,
                "description": i.description,
                "basis_code": i.basis_code,
                "suggestion": i.suggestion,
                "original_text": i.original_text,
                "status": i.status,
                "note": i.note,
            }
            for i in issues
        ],
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.patch("/review-issues/{issue_id}")
async def update_review_issue(issue_id: int, data: dict, db: Session = Depends(get_db)):
    """更新问题状态"""
    issue = db.query(AIReviewIssue).filter(AIReviewIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="问题不存在")
    
    if "status" in data:
        issue.status = data["status"]
    if "note" in data:
        issue.note = data["note"]
    
    db.commit()
    return {"message": "更新成功"}


@router.post("/review-tasks/{task_id}/export")
async def export_review_report(task_id: int, db: Session = Depends(get_db)):
    """导出审查意见Word"""
    from app.services.ai_review_engine import AIReviewEngine
    engine = AIReviewEngine(db)
    result = engine.export_report(task_id)
    
    return FileResponse(
        result["file_path"],
        filename=result["file_name"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# ========== 报告章节生成 ==========

@router.get("/section-templates")
async def list_section_templates(
    project_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取章节模板列表"""
    templates = db.query(ReportSectionTemplate).filter(ReportSectionTemplate.is_active == True).order_by(ReportSectionTemplate.sort_order, ReportSectionTemplate.chapter_number).all()
    
    # 构建树形结构
    root_templates = [t for t in templates if t.level == 1]
    
    def build_tree(parent):
        children = [t for t in templates if t.parent_id == parent.id]
        return {
            "id": parent.id,
            "chapter_number": parent.chapter_number,
            "title": parent.title,
            "level": parent.level,
            "description": parent.description,
            "children": [build_tree(c) for c in children]
        }
    
    return {"items": [build_tree(t) for t in root_templates]}


@router.post("/projects/{project_id}/section-tasks")
async def create_section_task(
    project_id: int,
    data: CreateSectionTaskRequest,
    db: Session = Depends(get_db)
):
    """创建章节生成任务"""
    from app.services.section_generator import SectionGenerator
    engine = SectionGenerator(db)
    task = engine.create_task(
        project_id=project_id,
        template_id=data.template_id,
        doc_ids=data.document_ids or [],
        params=data.params or {},
        created_by="system"
    )
    db.commit()
    db.refresh(task)
    return {"task_id": task.id}


@router.post("/section-tasks/{task_id}/generate-outline")
async def generate_section_outline(task_id: int, db: Session = Depends(get_db)):
    """生成章节大纲"""
    from app.services.section_generator import SectionGenerator
    engine = SectionGenerator(db)
    outline = await engine.generate_outline(task_id)
    return outline.model_dump()


@router.get("/section-tasks/{task_id}")
async def get_section_task(task_id: int, db: Session = Depends(get_db)):
    """获取章节生成任务详情"""
    task = db.query(ReportSectionTask).filter(ReportSectionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    drafts = db.query(ReportSectionDraft).filter(ReportSectionDraft.task_id == task_id).order_by(ReportSectionDraft.sort_order).all()
    
    return {
        "id": task.id,
        "project_id": task.project_id,
        "template_id": task.template_id,
        "template_title": task.template.title if task.template else "",
        "status": task.status,
        "progress": task.progress,
        "outline_json": task.outline_json,
        "assembled_content": task.assembled_content,
        "output_filename": task.output_filename,
        "drafts": [
            {
                "id": d.id,
                "paragraph_id": d.paragraph_id,
                "parent_paragraph_id": d.parent_paragraph_id,
                "paragraph_type": d.paragraph_type,
                "level": d.level,
                "content": d.content,
                "status": d.status,
                "sort_order": d.sort_order,
            }
            for d in drafts
        ],
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.post("/section-tasks/{task_id}/generate")
async def generate_section_content(task_id: int, start_from: Optional[str] = None, db: Session = Depends(get_db)):
    """SSE流式生成章节内容"""
    from app.services.section_generator import SectionGenerator
    engine = SectionGenerator(db)
    
    async def event_generator():
        try:
            async for event in engine.generate_section(task_id, start_from):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.patch("/section-drafts/{draft_id}")
async def update_section_draft(draft_id: int, data: dict, db: Session = Depends(get_db)):
    """编辑段落"""
    draft = db.query(ReportSectionDraft).filter(ReportSectionDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="段落不存在")
    
    if "content" in data:
        draft.content = data["content"]
        draft.status = "edited"
    
    db.commit()
    return {"message": "更新成功"}


@router.post("/section-drafts/{draft_id}/accept")
async def accept_section_draft(draft_id: int, db: Session = Depends(get_db)):
    """接受段落"""
    draft = db.query(ReportSectionDraft).filter(ReportSectionDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="段落不存在")
    
    from app.services.section_generator import SectionGenerator
    engine = SectionGenerator(db)
    engine.accept_paragraph(draft.task_id, draft.paragraph_id)
    return {"message": "已接受"}


@router.post("/section-tasks/{task_id}/export")
async def export_section_docx(task_id: int, db: Session = Depends(get_db)):
    """导出章节Word"""
    from app.services.section_generator import SectionGenerator
    engine = SectionGenerator(db)
    result = engine.export_docx(task_id)
    
    return FileResponse(
        result["file_path"],
        filename=result["file_name"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# ========== 专家意见回复 ==========

@router.post("/projects/{project_id}/expert-reply-tasks")
async def create_expert_reply_task(
    project_id: int,
    data: CreateExpertReplyTaskRequest,
    db: Session = Depends(get_db)
):
    """创建专家意见回复任务"""
    from app.services.expert_reply_service import ExpertReplyService
    engine = ExpertReplyService(db)
    task = engine.create_task(
        project_id=project_id,
        opinion_doc_id=data.opinion_document_id,
        report_doc_id=data.report_document_id,
        meeting_name=data.meeting_name,
        meeting_date=data.meeting_date,
        created_by="system"
    )
    db.commit()
    db.refresh(task)
    return {"task_id": task.id}


@router.post("/expert-reply-tasks/{task_id}/parse-opinions")
async def parse_expert_opinions(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """解析专家意见（后台任务）"""
    def _parse_sync():
        asyncio.run(_parse_bg())
    
    async def _parse_bg():
        db_session = SessionLocal()
        try:
            from app.services.expert_reply_service import ExpertReplyService
            engine = ExpertReplyService(db_session)
            async for event in engine.parse_opinions(task_id):
                pass
        except Exception as e:
            print(f"意见解析失败: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(_parse_sync)
    
    task = db.query(ExpertReplyTask).filter(ExpertReplyTask.id == task_id).first()
    if task:
        task.status = ReplyTaskStatus.PARSING.value
        db.commit()
    
    return {"message": "解析已开始"}


@router.get("/expert-reply-tasks/{task_id}")
async def get_expert_reply_task(task_id: int, db: Session = Depends(get_db)):
    """获取专家回复任务详情"""
    task = db.query(ExpertReplyTask).filter(ExpertReplyTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    opinions = db.query(ExpertOpinion).filter(ExpertOpinion.reply_task_id == task_id).order_by(ExpertOpinion.order_index).all()
    
    return {
        "id": task.id,
        "project_id": task.project_id,
        "status": task.status,
        "progress": task.progress,
        "meeting_name": task.meeting_name,
        "meeting_date": task.meeting_date,
        "opinion_count": task.opinion_count,
        "output_filename": task.output_filename,
        "opinions": [
            {
                "id": o.id,
                "opinion_index": o.opinion_index,
                "expert_name": o.expert_name,
                "major_category": o.major_category,
                "major_category_name": o.major_category_name,
                "opinion_type": o.opinion_type,
                "content": o.content,
                "page_number": o.page_number,
                "chapter_path": o.chapter_path,
                "reply": {
                    "reply_content": o.reply_item.reply_content if o.reply_item else "",
                    "modify_status": o.reply_item.modify_status if o.reply_item else "",
                    "modify_location": o.reply_item.modify_location if o.reply_item else "",
                    "modify_page": o.reply_item.modify_page if o.reply_item else "",
                    "status": o.reply_item.status if o.reply_item else "draft",
                } if o.reply_item else None
            }
            for o in opinions
        ],
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.post("/expert-opinions/{opinion_id}/generate-reply")
async def generate_opinion_reply(opinion_id: int, db: Session = Depends(get_db)):
    """生成单条意见回复"""
    from app.services.expert_reply_service import ExpertReplyService
    engine = ExpertReplyService(db)
    result = await engine.generate_reply(opinion_id)
    return {
        "reply_id": result.id,
        "opinion_id": result.opinion_id,
        "reply_content": result.reply_content,
        "modify_status": result.modify_status,
        "modify_location": result.modify_location,
        "modify_page": result.modify_page,
        "status": result.status,
    }


@router.post("/expert-reply-tasks/{task_id}/generate-all")
async def generate_all_replies(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """批量生成所有回复（后台任务）"""
    def _gen_sync():
        asyncio.run(_gen_bg())
    
    async def _gen_bg():
        db_session = SessionLocal()
        try:
            from app.services.expert_reply_service import ExpertReplyService
            engine = ExpertReplyService(db_session)
            opinions = db_session.query(ExpertOpinion).filter(ExpertOpinion.reply_task_id == task_id).all()
            opinion_ids = [o.id for o in opinions]
            async for event in engine.generate_all_replies(task_id, opinion_ids):
                pass
        except Exception as e:
            print(f"批量生成失败: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(_gen_sync)
    
    task = db.query(ExpertReplyTask).filter(ExpertReplyTask.id == task_id).first()
    if task:
        task.status = ReplyTaskStatus.GENERATING.value
        db.commit()
    
    return {"message": "批量生成已开始"}


@router.patch("/expert-opinions/{opinion_id}")
async def update_opinion_reply(opinion_id: int, data: dict, db: Session = Depends(get_db)):
    """更新意见回复"""
    from app.services.expert_reply_service import ExpertReplyService
    engine = ExpertReplyService(db)
    engine.update_reply(
        opinion_id=opinion_id,
        reply_content=data.get("reply_content"),
        modify_status=data.get("modify_status"),
        modify_location=data.get("modify_location"),
        modify_page=data.get("modify_page")
    )
    return {"message": "更新成功"}


@router.post("/expert-reply-tasks/{task_id}/export")
async def export_reply_table(task_id: int, db: Session = Depends(get_db)):
    """导出回复表Word"""
    from app.services.expert_reply_service import ExpertReplyService
    engine = ExpertReplyService(db)
    result = engine.export_reply_table(task_id)
    
    return FileResponse(
        result["file_path"],
        filename=result["file_name"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# ========== 资料检索与问答 ==========

@router.get("/search")
async def unified_search(
    q: str,
    project_id: Optional[int] = None,
    file_types: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """统一检索接口 - 搜索规范、历史项目、项目文档"""
    from app.services.retrieval_service import retrieval_service
    
    # 解析文件类型过滤
    ft_list = file_types.split(",") if file_types else None
    
    results = retrieval_service.search(
        query=q,
        project_id=project_id,
        file_types=ft_list,
        top_k=limit
    )
    
    # 转换为字典
    items = [c.to_dict() for c in results]
    return {"items": items, "total": len(items)}


@router.post("/ask")
async def ask_question(
    data: dict,
    db: Session = Depends(get_db)
):
    """水利规范问答接口（RAG）"""
    from app.services.llm_service import llm_service
    from app.services.retrieval_service import retrieval_service
    
    question = data.get("question", "")
    project_id = data.get("project_id")
    
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    # 检索相关文档
    contexts = retrieval_service.search(
        query=question,
        project_id=project_id,
        top_k=5
    )
    
    # 构建prompt
    context_text = "\n\n".join([
        f"[来源: {ctx.document_title} 页码: {ctx.page_number or '?'}]\n{ctx.chunk_text}"
        for ctx in contexts
    ])
    
    system_prompt = f"""你是水利工程设计专家助手，请基于以下参考资料回答问题。
如果参考资料中没有相关信息，请明确说明。回答要专业、准确，引用规范条文时注明规范编号。

参考资料：
{context_text}
"""
    
    # 调用LLM
    answer = llm_service.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    )
    
    return {
        "answer": answer,
        "sources": [
            {
                "document_id": ctx.document_id,
                "title": ctx.document_title,
                "page_number": ctx.page_number,
                "section": ctx.section_title,
                "snippet": (ctx.chunk_text or "")[:200]
            }
            for ctx in contexts
        ]
    }


# ========== 项目概览 ==========

@router.get("/projects/{project_id}/overview")
async def get_project_overview(project_id: int, db: Session = Depends(get_db)):
    """获取项目概览统计"""
    from app.models.project import DesignProject
    
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 统计各模块任务数
    doc_count = db.query(Document).filter(Document.project_id == project_id).count()
    form_count = db.query(FormFillTask).filter(FormFillTask.project_id == project_id).count()
    form_completed = db.query(FormFillTask).filter(
        FormFillTask.project_id == project_id,
        FormFillTask.status == "completed"
    ).count()
    section_count = db.query(ReportSectionTask).filter(ReportSectionTask.project_id == project_id).count()
    review_count = db.query(AIReviewTask).filter(AIReviewTask.project_id == project_id).count()
    reply_count = db.query(ExpertReplyTask).filter(ExpertReplyTask.project_id == project_id).count()
    
    # 获取最近任务
    recent_tasks = []
    
    # 最近填报任务
    recent_forms = db.query(FormFillTask).filter(FormFillTask.project_id == project_id)\
        .order_by(desc(FormFillTask.created_at)).limit(3).all()
    for t in recent_forms:
        recent_tasks.append({
            "type": "form_fill",
            "name": t.template.template_name if t.template else "表格填报",
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    
    # 最近审查任务
    recent_reviews = db.query(AIReviewTask).filter(AIReviewTask.project_id == project_id)\
        .order_by(desc(AIReviewTask.created_at)).limit(2).all()
    for t in recent_reviews:
        recent_tasks.append({
            "type": "ai_review",
            "name": f"AI初审 - {t.document.title if t.document else ''}",
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    
    return {
        "project": {
            "id": project.id,
            "name": project.project_name,
            "code": project.project_code,
            "type": project.project_type,
            "stage": project.design_stage,
        },
        "statistics": {
            "documents": doc_count,
            "form_tasks": form_count,
            "form_completed": form_completed,
            "section_tasks": section_count,
            "review_tasks": review_count,
            "reply_tasks": reply_count,
        },
        "recent_tasks": recent_tasks
    }


# ========== 项目文档管理 ==========

WORKSPACE_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads")
os.makedirs(WORKSPACE_UPLOAD_DIR, exist_ok=True)


def _infer_file_type(filename: str) -> str:
    """根据文件名推断文档类型"""
    from app.models.document import FileType
    name = filename.lower()
    if '规范' in filename or '标准' in filename or '规程' in filename:
        return FileType.STANDARD.value
    if '审查意见' in filename or '专家意见' in filename or '评审' in filename:
        return FileType.REVIEW_OPINION.value
    if '防汛' in filename or '预案' in filename:
        return FileType.FLOOD_PLAN.value
    if '报告' in filename or '设计' in filename or '说明' in filename:
        return FileType.PROJECT_REPORT.value
    return FileType.OTHER.value


def _parse_workspace_document_background(document_id: int, file_path: str):
    """工作台文档后台解析（与projects.py中逻辑一致，但独立以避免循环依赖）"""
    try:
        from app.services.document_parser import document_parser
        from app.services.embedding import embedding_service as emb_svc
        from app.services.vector_store import vector_store as vs
        
        db = SessionLocal()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            db.close()
            return
        
        doc.parse_status = "解析中"
        db.commit()
        
        try:
            parsed, chunks = document_parser.parse_and_chunk_enhanced(file_path)
            
            doc.total_pages = parsed.total_pages
            doc.table_count = len(parsed.tables)
            doc.chapter_json = [{"number": c.number, "title": c.title, "level": c.level} for c in parsed.chapters]
            doc.parse_status = "已完成"
            
            from app.models.document import Chunk as DBChunk
            for i, chunk in enumerate(chunks):
                db_chunk = DBChunk(
                    document_id=document_id,
                    chunk_text=chunk["text"],
                    page_number=chunk.get("page_number"),
                    section_title=chunk.get("section_title", ""),
                    chapter_path=chunk.get("chapter_path", ""),
                    tables_json=chunk.get("tables_json"),
                    chunk_index=i
                )
                db.add(db_chunk)
            
            db.commit()
            
            # 向量化
            db_chunks = db.query(DBChunk).filter(DBChunk.document_id == document_id).order_by(DBChunk.chunk_index).all()
            texts = [c.chunk_text for c in db_chunks]
            if texts:
                try:
                    embeddings = emb_svc.embed(texts)
                    vector_items = []
                    for db_chunk, emb in zip(db_chunks, embeddings):
                        vector_items.append({
                            "id": f"chunk_{document_id}_{db_chunk.chunk_index}",
                            "embedding": emb,
                            "metadata": {
                                "document_id": document_id,
                                "project_id": doc.project_id,
                                "file_type": doc.file_type,
                                "chunk_id": db_chunk.id,
                                "file_name": doc.title,
                                "page_number": db_chunk.page_number,
                                "section_title": db_chunk.section_title,
                                "chapter_path": db_chunk.chapter_path,
                                "text": db_chunk.chunk_text[:200],
                            }
                        })
                    vs.add_batch(vector_items)
                except Exception as ve:
                    print(f"[Workspace] 向量化失败: {ve}")
            
            doc.chunk_count = len(db_chunks)
            db.commit()
            
        except Exception as e:
            print(f"[Workspace] 文档解析失败: {e}")
            doc.parse_status = "失败"
            db.commit()
        
        db.close()
    except Exception as e:
        print(f"[Workspace] 后台解析任务异常: {e}")


@router.post("/projects/{project_id}/documents")
async def workspace_upload_document(
    project_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    is_report: bool = False,
    is_expert_opinion: bool = False,
    db: Session = Depends(get_db)
):
    """工作台上传项目文档"""
    from app.models.project import DesignProject
    from app.models.document import ParseStatus as DocParseStatus
    
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = {'.pdf', '.docx', '.doc', '.txt', '.xlsx', '.xls'}
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(WORKSPACE_UPLOAD_DIR, filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    file_type = _infer_file_type(file.filename)
    
    doc = Document(
        title=file.filename,
        file_type=file_type,
        file_path=file_path,
        original_filename=file.filename,
        file_size=len(content),
        parse_status=DocParseStatus.PENDING.value,
        project_id=project_id,
        is_report=is_report,
        is_expert_opinion=is_expert_opinion,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    if background_tasks:
        background_tasks.add_task(_parse_workspace_document_background, doc.id, file_path)
    
    return {
        "document_id": doc.id,
        "message": "文档上传成功，正在后台解析",
        "parse_status": doc.parse_status
    }


@router.get("/projects/{project_id}/documents")
async def workspace_list_documents(project_id: int, db: Session = Depends(get_db)):
    """获取项目文档列表"""
    docs = db.query(Document).filter(Document.project_id == project_id).order_by(desc(Document.created_at)).all()
    return {
        "items": [
            {
                "id": d.id,
                "project_id": d.project_id,
                "title": d.title,
                "file_type": d.file_type,
                "original_filename": d.original_filename,
                "file_size": d.file_size,
                "file_path": d.file_path,
                "parse_status": d.parse_status,
                "chunk_count": d.chunk_count or 0,
                "table_count": d.table_count or 0,
                "total_pages": d.total_pages,
                "is_report": d.is_report or False,
                "is_expert_opinion": d.is_expert_opinion or False,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ]
    }


@router.get("/projects/{project_id}/documents/{document_id}")
async def workspace_get_document(project_id: int, document_id: int, db: Session = Depends(get_db)):
    """获取文档详情"""
    doc = db.query(Document).filter(Document.id == document_id, Document.project_id == project_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {
        "id": doc.id,
        "project_id": doc.project_id,
        "title": doc.title,
        "file_type": doc.file_type,
        "original_filename": doc.original_filename,
        "file_size": doc.file_size,
        "parse_status": doc.parse_status,
        "chunk_count": doc.chunk_count or 0,
        "table_count": doc.table_count or 0,
        "total_pages": doc.total_pages,
        "chapter_json": doc.chapter_json,
        "is_report": doc.is_report or False,
        "is_expert_opinion": doc.is_expert_opinion or False,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.put("/projects/{project_id}/documents/{document_id}/set-report")
async def workspace_set_report(project_id: int, document_id: int, db: Session = Depends(get_db)):
    """标记文档为主报告（同时取消其他文档的主报告标记）"""
    doc = db.query(Document).filter(Document.id == document_id, Document.project_id == project_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 取消其他文档的主报告标记
    db.query(Document).filter(Document.project_id == project_id, Document.is_report == True).update({"is_report": False})
    
    doc.is_report = True
    db.commit()
    return {"message": "已标记为主报告"}


@router.put("/projects/{project_id}/documents/{document_id}/set-expert-opinion")
async def workspace_set_expert_opinion(project_id: int, document_id: int, db: Session = Depends(get_db)):
    """标记文档为专家意见"""
    doc = db.query(Document).filter(Document.id == document_id, Document.project_id == project_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    doc.is_expert_opinion = True
    db.commit()
    return {"message": "已标记为专家意见"}


@router.delete("/projects/{project_id}/documents/{document_id}")
async def workspace_delete_document(project_id: int, document_id: int, db: Session = Depends(get_db)):
    """删除文档（同时删除向量库中的chunks和文件）"""
    from app.services.vector_store import vector_store as vs
    
    doc = db.query(Document).filter(Document.id == document_id, Document.project_id == project_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 删除向量
    try:
        vs.delete_by_document(document_id)
    except Exception:
        pass
    
    # 删除文件
    try:
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception:
        pass
    
    db.delete(doc)
    db.commit()
    return {"message": "文档已删除"}


@router.get("/projects/{project_id}/tasks")
async def workspace_list_tasks(project_id: int, db: Session = Depends(get_db)):
    """获取项目所有任务列表（5种任务类型汇总）"""
    tasks = []
    
    # 表单填报任务
    form_tasks = db.query(FormFillTask).filter(FormFillTask.project_id == project_id)\
        .order_by(desc(FormFillTask.created_at)).all()
    for t in form_tasks:
        tasks.append({
            "id": t.id,
            "task_type": "form_fill",
            "task_name": t.template.template_name if t.template else "表格填报",
            "status": t.status,
            "progress": t.progress or 0,
            "output_filename": t.output_filename,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    
    # 报告章节任务
    section_tasks = db.query(ReportSectionTask).filter(ReportSectionTask.project_id == project_id)\
        .order_by(desc(ReportSectionTask.created_at)).all()
    for t in section_tasks:
        tasks.append({
            "id": t.id,
            "task_type": "section_gen",
            "task_name": t.template.title if t.template else "报告生成",
            "status": t.status,
            "progress": t.progress or 0,
            "output_filename": t.output_filename,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    
    # AI审查任务
    review_tasks = db.query(AIReviewTask).filter(AIReviewTask.project_id == project_id)\
        .order_by(desc(AIReviewTask.created_at)).all()
    for t in review_tasks:
        tasks.append({
            "id": t.id,
            "task_type": "ai_review",
            "task_name": f"AI初审 - {t.document.title if t.document else ''}",
            "status": t.status,
            "progress": t.progress or 0,
            "output_filename": None,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    
    # 专家回复任务
    reply_tasks = db.query(ExpertReplyTask).filter(ExpertReplyTask.project_id == project_id)\
        .order_by(desc(ExpertReplyTask.created_at)).all()
    for t in reply_tasks:
        tasks.append({
            "id": t.id,
            "task_type": "expert_reply",
            "task_name": f"专家回复 - {t.meeting_name or ''}",
            "status": t.status,
            "progress": t.progress or 0,
            "output_filename": t.output_filename,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    
    # 按创建时间排序（最新在前）
    tasks.sort(key=lambda x: x["created_at"] or "", reverse=True)
    
    return {"items": tasks}
