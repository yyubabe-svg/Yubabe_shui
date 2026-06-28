"""项目管理API路由 - 替换原Mock数据"""
import asyncio
import os
import uuid
from datetime import datetime
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.models.document import Document, ParseStatus, FileType
from app.models.project import DesignProject, ProjectType, DesignStage, PROJECT_TYPE_NAMES, DESIGN_STAGE_NAMES
from app.models.user_usage import UserUsage
from app.api.routes.usage import get_current_user, check_feature_access
from app.services.document_parser import document_parser


class ProjectCreate(BaseModel):
    project_name: str
    project_type: str
    design_stage: Optional[str] = None
    client: Optional[str] = None
    designer: Optional[str] = None
    location: Optional[str] = None

router = APIRouter(prefix="/api/projects", tags=["项目管理"])

UPLOAD_DIR = settings.UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("")
async def list_projects(
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
    project_type: Optional[str] = None,
    design_stage: Optional[str] = None,
    keyword: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    """获取项目列表"""
    query = db.query(DesignProject).filter(DesignProject.status == "active")
    
    if project_type:
        query = query.filter(DesignProject.project_type == project_type)
    if design_stage:
        query = query.filter(DesignProject.design_stage == design_stage)
    if keyword:
        query = query.filter(DesignProject.project_name.contains(keyword))
    
    total = query.count()
    projects = query.order_by(desc(DesignProject.updated_at)).offset(skip).limit(limit).all()
    
    # 批量统计文档数量
    from app.models.form_template import FormFillTask
    from app.models.report_section import ReportSectionTask
    from app.models.ai_review import AIReviewTask
    from app.models.expert_reply import ExpertReplyTask
    
    items = []
    for p in projects:
        doc_count = db.query(Document).filter(Document.project_id == p.id).count()
        form_count = db.query(FormFillTask).filter(FormFillTask.project_id == p.id).count()
        section_count = db.query(ReportSectionTask).filter(ReportSectionTask.project_id == p.id).count()
        review_count = db.query(AIReviewTask).filter(AIReviewTask.project_id == p.id).count()
        reply_count = db.query(ExpertReplyTask).filter(ExpertReplyTask.project_id == p.id).count()
        
        items.append({
            "id": p.id,
            "project_code": p.project_code,
            "project_name": p.project_name,
            "project_type": p.project_type,
            "project_type_name": PROJECT_TYPE_NAMES.get(ProjectType(p.project_type), p.project_type) if p.project_type else "",
            "design_stage": p.design_stage,
            "design_stage_name": DESIGN_STAGE_NAMES.get(DesignStage(p.design_stage), p.design_stage) if p.design_stage else "",
            "client": p.client,
            "designer": p.designer,
            "department": p.department,
            "location": p.location,
            "status": p.status,
            "total_investment": p.total_investment,
            "document_count": doc_count,
            "form_task_count": form_count,
            "section_task_count": section_count,
            "review_task_count": review_count,
            "reply_task_count": reply_count,
            # 前端兼容别名
            "name": p.project_name,
            "code": p.project_code,
            "stage": DESIGN_STAGE_NAMES.get(DesignStage(p.design_stage), p.design_stage) if p.design_stage else "",
            "doc_count": doc_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })
    
    return {
        "total": total,
        "items": items
    }


@router.post("")
async def create_project(
    data: ProjectCreate,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新项目"""
    project_code = f"PRJ-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    project = DesignProject(
        project_code=project_code,
        project_name=data.project_name,
        project_type=data.project_type,
        design_stage=data.design_stage,
        client=data.client,
        designer=data.designer,
        location=data.location,
        created_by=user.name
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return {
        "id": project.id,
        "project_code": project_code,
        "project_name": project.project_name,
        "message": "项目创建成功"
    }


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取项目详情"""
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 统计任务数量
    from app.models.form_template import FormFillTask
    from app.models.report_section import ReportSectionTask
    from app.models.ai_review import AIReviewTask
    from app.models.expert_reply import ExpertReplyTask
    
    form_count = db.query(FormFillTask).filter(FormFillTask.project_id == project_id).count()
    section_count = db.query(ReportSectionTask).filter(ReportSectionTask.project_id == project_id).count()
    review_count = db.query(AIReviewTask).filter(AIReviewTask.project_id == project_id).count()
    reply_count = db.query(ExpertReplyTask).filter(ExpertReplyTask.project_id == project_id).count()
    doc_count = db.query(Document).filter(Document.project_id == project_id).count()
    
    return {
        "id": project.id,
        "project_code": project.project_code,
        "project_name": project.project_name,
        "project_type": project.project_type,
        "project_type_name": PROJECT_TYPE_NAMES.get(ProjectType(project.project_type), project.project_type) if project.project_type else "",
        "design_stage": project.design_stage,
        "design_stage_name": DESIGN_STAGE_NAMES.get(DesignStage(project.design_stage), project.design_stage) if project.design_stage else "",
        "client": project.client,
        "designer": project.designer,
        "department": project.department,
        "location": project.location,
        "river_basin": project.river_basin,
        "status": project.status,
        # 工程参数
        "project_grade": project.project_grade,
        "scale_type": project.scale_type,
        "main_building_level": project.main_building_level,
        "flood_std_design": project.flood_std_design,
        "flood_std_check": project.flood_std_check,
        "catchment_area": project.catchment_area,
        "river_governance_length": project.river_governance_length,
        "embankment_length": project.embankment_length,
        "total_investment": project.total_investment,
        # 统计
        "document_count": doc_count,
        "form_task_count": form_count,
        "section_task_count": section_count,
        "review_task_count": review_count,
        "reply_task_count": reply_count,
        # 前端兼容别名
        "name": project.project_name,
        "code": project.project_code,
        "stage": DESIGN_STAGE_NAMES.get(DesignStage(project.design_stage), project.design_stage) if project.design_stage else "",
        "doc_count": doc_count,
        # 关联文档
        "report_file_id": project.report_file_id,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    data: dict,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新项目信息"""
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    update_fields = [
        "project_name", "project_type", "design_stage", "client", "designer",
        "department", "location", "river_basin", "project_grade", "scale_type",
        "main_building_level", "secondary_building_level", "temporary_building_level",
        "flood_std_design", "flood_std_check", "drainage_std", "seismic_intensity",
        "catchment_area", "river_governance_length", "embankment_length",
        "total_investment", "storage_capacity"
    ]
    
    for field in update_fields:
        if field in data:
            setattr(project, field, data[field])
    
    db.commit()
    return {"message": "更新成功"}


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除项目（软删除）"""
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    project.status = "archived"
    db.commit()
    return {"message": "项目已归档"}


def _parse_document_background(document_id: int, file_path: str):
    """后台解析文档（BackgroundTasks在线程池中运行，同步操作直接执行即可）"""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return
        
        doc.parse_status = ParseStatus.PARSING.value
        db.commit()
        
        try:
            # 解析文档
            parsed, chunks = document_parser.parse_and_chunk_enhanced(file_path)
            
            # 更新文档元数据
            doc.total_pages = parsed.total_pages
            doc.table_count = len(parsed.tables)
            doc.chapter_json = [{"number": c.number, "title": c.title, "level": c.level} for c in parsed.chapters]
            doc.parse_status = ParseStatus.COMPLETED.value
            
            # 存储chunks到数据库和向量库
            from app.services.vector_store import vector_store
            from app.models.document import Chunk
            from app.services.embedding import embedding_service
            
            for i, chunk in enumerate(chunks):
                db_chunk = Chunk(
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
            
            # 重新查询chunks以获取ID
            db_chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
            
            # 添加到向量库
            texts = [c.chunk_text for c in db_chunks]
            if texts:
                try:
                    embeddings = embedding_service.embed(texts)
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
                    vector_store.add_batch(vector_items)
                except Exception as ve:
                    print(f"向量化失败: {ve}")
            
            doc.chunk_count = len(db_chunks)
            db.commit()
            
        except Exception as e:
            print(f"文档解析失败: {e}")
            doc.parse_status = ParseStatus.FAILED.value
            db.commit()
    except Exception as e:
        print(f"后台解析任务异常: {e}")
    finally:
        db.close()


async def _safe_remove_file(path: str):
    """安全删除文件（异步）"""
    if os.path.exists(path):
        try:
            await asyncio.to_thread(os.remove, path)
        except Exception:
            pass


@router.post("/{project_id}/upload-report")
async def upload_project_report(
    project_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: Request = None,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传项目主报告（aiofiles异步分块写入，移除.doc支持）"""
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查文件格式
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {'.pdf', '.docx', '.txt', '.md', '.markdown', '.xlsx', '.xls'}
    if ext == '.doc':
        raise HTTPException(status_code=400, detail=".doc格式不支持，请转换为.docx后再上传")
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    
    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)
    
    # 先检查Content-Length头部
    content_length = 0
    if request and "content-length" in request.headers:
        try:
            content_length = int(request.headers["content-length"])
        except (ValueError, TypeError):
            pass
    
    max_allowed = settings.PRO_MAX_FILE_SIZE if user.is_pro_active() else settings.FREE_MAX_FILE_SIZE
    if content_length > 0 and content_length > max_allowed:
        limit_mb = max_allowed // 1024 // 1024
        raise HTTPException(status_code=400, detail=f"文件大小超过限制({limit_mb}MB)")
    
    file_size = 0
    try:
        # 使用aiofiles异步分块写入
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
                file_size += len(chunk)
                if file_size > max_allowed:
                    limit_mb = max_allowed // 1024 // 1024
                    raise HTTPException(status_code=400, detail=f"文件大小超过限制({limit_mb}MB)")
        
        # 检查存储额度
        if not settings.MOCK_MODE:
            check = check_feature_access(user, "upload", file_size=file_size, db=db)
            if not check.allowed:
                await _safe_remove_file(file_path)
                raise HTTPException(status_code=402, detail=check.reason)
        
        # 创建文档记录
        doc = Document(
            title=os.path.splitext(file.filename)[0],
            file_type=FileType.PROJECT_REPORT.value,
            file_path=file_path,
            original_filename=file.filename,
            file_size=file_size,
            parse_status=ParseStatus.PENDING.value,
            project_id=project_id,
            upload_user=user.name,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # 累加存储量
        if not settings.MOCK_MODE:
            user.total_upload_bytes += file_size
            db.commit()
        
        # 添加后台解析任务
        background_tasks.add_task(_parse_document_background, doc.id, file_path)
        
        return {
            "file_id": file_id,
            "document_id": doc.id,
            "original_filename": file.filename,
            "file_size": file_size,
            "message": "报告上传成功，正在后台解析"
        }
    except HTTPException:
        await _safe_remove_file(file_path)
        raise
    except Exception as e:
        await _safe_remove_file(file_path)
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")


@router.get("/{project_id}/documents")
async def list_project_documents(
    project_id: int,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取项目文档列表（不返回绝对file_path）"""
    docs = db.query(Document).filter(Document.project_id == project_id).order_by(desc(Document.created_at)).all()
    return {
        "items": [
            {
                "id": d.id,
                "title": d.title,
                "file_type": d.file_type,
                "original_filename": d.original_filename,
                "file_size": d.file_size,
                "parse_status": d.parse_status,
                "table_count": d.table_count,
                "total_pages": d.total_pages,
                "chunk_count": d.chunk_count or 0,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ]
    }


@router.get("/types/options")
async def get_project_type_options():
    """获取项目类型选项"""
    return {
        "project_types": [
            {"value": k.value, "label": v} for k, v in PROJECT_TYPE_NAMES.items()
        ],
        "design_stages": [
            {"value": k.value, "label": v} for k, v in DESIGN_STAGE_NAMES.items()
        ]
    }
