"""项目管理API路由 - 替换原Mock数据"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
import os
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.project import DesignProject, ProjectType, DesignStage, PROJECT_TYPE_NAMES, DESIGN_STAGE_NAMES
from app.models.document import Document, ParseStatus
from app.services.document_parser import document_parser


class ProjectCreate(BaseModel):
    project_name: str
    project_type: str
    design_stage: Optional[str] = None
    client: Optional[str] = None
    designer: Optional[str] = None
    location: Optional[str] = None

router = APIRouter(prefix="/api/projects", tags=["项目管理"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("")
async def list_projects(
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
        created_by="system"
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
async def get_project(project_id: int, db: Session = Depends(get_db)):
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
async def update_project(project_id: int, data: dict, db: Session = Depends(get_db)):
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
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """删除项目（软删除）"""
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    project.status = "archived"
    db.commit()
    return {"message": "项目已归档"}


def _parse_document_background(document_id: int, file_path: str):
    """后台解析文档"""
    try:
        db = SessionLocal()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            db.close()
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
            from app.services.embedding import embedding_service
            texts = [c.chunk_text for c in db_chunks]
            if texts:
                try:
                    embeddings = embedding_service.embed(texts)
                    vector_items = []
                    for i, (db_chunk, emb) in enumerate(zip(db_chunks, embeddings)):
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
            
        except Exception as e:
            print(f"文档解析失败: {e}")
            doc.parse_status = ParseStatus.FAILED.value
            db.commit()
        
        db.close()
    except Exception as e:
        print(f"后台解析任务异常: {e}")


@router.post("/{project_id}/upload-report")
async def upload_project_report(
    project_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传项目主报告"""
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 保存文件
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 创建文档记录
    from app.models.document import FileType
    doc = Document(
        title=file.filename,
        file_type=FileType.PROJECT_REPORT.value,
        file_path=file_path,
        original_filename=file.filename,
        file_size=len(content),
        parse_status=ParseStatus.PENDING.value,
        project_id=project_id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # 添加后台解析任务
    background_tasks.add_task(_parse_document_background, doc.id, file_path)
    
    return {"document_id": doc.id, "message": "报告上传成功，正在后台解析"}


@router.get("/{project_id}/documents")
async def list_project_documents(project_id: int, db: Session = Depends(get_db)):
    """获取项目文档列表"""
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
