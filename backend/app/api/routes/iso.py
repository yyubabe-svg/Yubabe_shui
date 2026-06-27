import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Optional
import json

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.iso import ISOGenerateResponse, ISOFillRequest
from app.services.iso_service import iso_service
from app.core.config import settings
from app.api.routes.usage import get_current_user, check_feature_access
from app.models.user_usage import UserUsage

router = APIRouter()


@router.post("/generate", summary="上传项目报告，自动生成ISO管理体系附表")
async def generate_iso_document(
    file: UploadFile = File(...),
    project_manager: Optional[str] = Form(None),
    supplementary_info: Optional[str] = Form(None),
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传项目设计报告，自动解析并填写ISO管理体系附表"""
    # 检查ISO权限（Mock模式不限制）
    if not settings.MOCK_MODE:
        check = check_feature_access(user, "iso", db=db)
        if not check.allowed:
            raise HTTPException(status_code=402, detail=check.reason)
    
    upload_dir = os.path.join(settings.UPLOAD_DIR, "iso_temp")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    
    try:
        contents = await file.read()
        with open(file_path, 'wb') as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    supp_info = {}
    if supplementary_info:
        try:
            supp_info = json.loads(supplementary_info)
        except:
            pass
    if project_manager:
        supp_info["project_manager"] = project_manager
    
    try:
        result = await iso_service.generate_document(
            file_path=file_path,
            filename=file.filename,
            supplementary_info=supp_info,
        )
        # 非Mock模式下计数+1
        if not settings.MOCK_MODE:
            user.iso_used_count += 1
            db.commit()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档生成失败: {str(e)}")


@router.post("/fill", summary="确认信息后重新生成文档")
async def fill_iso_document(
    request: ISOFillRequest,
    user: UserUsage = Depends(get_current_user),
):
    """人工确认/修改项目信息后，重新生成文档"""
    task = iso_service.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    output_path = iso_service.regenerate_with_confirmation(
        request.task_id,
        request.project_info.model_dump(),
    )
    
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="文档重新生成失败")
    
    return {
        "task_id": request.task_id,
        "status": "completed",
        "download_url": f"/api/iso/download/{request.task_id}",
        "message": "文档已更新",
    }


@router.get("/task/{task_id}")
async def get_iso_task(task_id: str, user: UserUsage = Depends(get_current_user)):
    """获取任务信息"""
    task = iso_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    result = task.copy()
    if result.get("project_info"):
        result["project_info"] = result["project_info"].model_dump()
    return result


@router.get("/download/{task_id}")
async def download_iso_document(task_id: str, user: UserUsage = Depends(get_current_user)):
    """下载生成的ISO文档"""
    file_path = iso_service.get_output_file(task_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    filename = os.path.basename(file_path)
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/majors")
async def get_majors():
    """获取专业列表"""
    from app.services.iso_service import ALL_MAJORS
    return {
        "majors": ALL_MAJORS,
        "quality_levels": ["A级", "B级", "C级"],
        "design_stages": ["初步设计", "可行性研究", "实施方案"],
    }


@router.get("/template-info")
async def get_template_info():
    """获取ISO模板信息"""
    return {
        "template_name": "管理体系附表-设计部分",
        "forms": [
            {"code": "TY01", "name": "项目任务书", "description": "项目立项基本信息、质量分级、顾客要求、风险要点"},
            {"code": "TY02-1", "name": "工程项目策划表", "description": "工程概况、设计依据、技术要点、风险、人员安排、评审计划"},
            {"code": "TY02-2", "name": "项目校审配置表", "description": "各专业的校审人员配置"},
            {"code": "TY03", "name": "互提资料单", "description": "专业间互提资料记录"},
            {"code": "TY04-1", "name": "产品运行卡（专业）", "description": "单专业设计产品的依据规范、校审意见"},
            {"code": "TY04-2", "name": "产品运行卡（项目）", "description": "项目级产品的合同要求完成情况、审批意见"},
        ],
        "notes": [
            "所有签名和日期字段需人工手动签署",
            "人员姓名需人工配置",
            "设计评审/验证/确认的具体时间需根据项目计划排期填写",
            "互提资料单(TY03)在设计过程中按需使用",
            "校审意见需在校审阶段填写",
        ]
    }
