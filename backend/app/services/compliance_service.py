"""
合规初审模块业务逻辑服务层
处理项目管理、审核流程、检查表、统计分析等核心业务
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import os
import uuid

from app.models.compliance import (
    ComplianceProject,
    ComplianceChecklistTemplate,
    ComplianceCheckItem,
    ComplianceChecklistInstance,
    ComplianceReviewItem,
    ComplianceReview,
    ComplianceComment,
    ComplianceAttachment,
)
from app.schemas.compliance import (
    ComplianceProjectCreate,
    ComplianceProjectUpdate,
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
    ComplianceReviewCreate,
    CommentCreate,
    CommentUpdate,
)
from app.core.config import settings


class ComplianceService:
    """合规初审服务类"""

    def __init__(self, db: Session):
        self.db = db

    # ============ 项目管理 ============

    def create_project(self, project_in: ComplianceProjectCreate, user_id: Optional[int] = None) -> ComplianceProject:
        """创建初审项目"""
        project = ComplianceProject(
            project_code=project_in.project_code,
            project_name=project_in.project_name,
            project_type=project_in.project_type,
            project_stage=project_in.project_stage,
            applicant=project_in.applicant,
            applicant_dept=project_in.applicant_dept,
            priority=project_in.priority,
            pass_score=project_in.pass_score,
            deadline=project_in.deadline,
            created_by=user_id,
            status="draft",
        )
        self.db.add(project)
        self.db.flush()

        # 如果指定了模板，自动创建检查表实例
        if project_in.template_id:
            self._create_checklist_from_template(project.id, project_in.template_id)

        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project(self, project_id: int) -> Optional[ComplianceProject]:
        """获取项目详情"""
        return self.db.query(ComplianceProject).filter(ComplianceProject.id == project_id).first()

    def get_project_with_details(self, project_id: int) -> Optional[ComplianceProject]:
        """获取项目详情（含关联数据）"""
        return (
            self.db.query(ComplianceProject)
            .options(
                joinedload(ComplianceProject.checklists).joinedload(ComplianceChecklistInstance.review_items),
                joinedload(ComplianceProject.reviews),
                joinedload(ComplianceProject.comments).joinedload(ComplianceComment.replies),
                joinedload(ComplianceProject.attachments),
            )
            .filter(ComplianceProject.id == project_id)
            .first()
        )

    def list_projects(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        project_type: Optional[str] = None,
        priority: Optional[str] = None,
        keyword: Optional[str] = None,
        reviewer_id: Optional[int] = None,
        created_by: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[ComplianceProject], int, Dict[str, Any]]:
        """获取项目列表（分页+筛选）"""
        query = self.db.query(ComplianceProject)

        # 应用筛选条件
        if status:
            if status == "pending":
                query = query.filter(ComplianceProject.status.in_(["submitted", "reviewing"]))
            else:
                query = query.filter(ComplianceProject.status == status)
        if project_type:
            query = query.filter(ComplianceProject.project_type == project_type)
        if priority:
            query = query.filter(ComplianceProject.priority == priority)
        if keyword:
            query = query.filter(
                or_(
                    ComplianceProject.project_name.contains(keyword),
                    ComplianceProject.project_code.contains(keyword),
                    ComplianceProject.applicant.contains(keyword),
                )
            )
        if reviewer_id:
            query = query.filter(ComplianceProject.reviewer_id == reviewer_id)
        if created_by:
            query = query.filter(ComplianceProject.created_by == created_by)
        if start_date:
            query = query.filter(ComplianceProject.created_at >= start_date)
        if end_date:
            query = query.filter(ComplianceProject.created_at <= end_date)

        # 统计
        total = query.count()

        # 分页
        items = (
            query.order_by(ComplianceProject.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # 附加统计信息
        statistics = self._get_list_statistics()

        return items, total, statistics

    def update_project(self, project_id: int, project_in: ComplianceProjectUpdate) -> Optional[ComplianceProject]:
        """更新项目信息"""
        project = self.get_project(project_id)
        if not project:
            return None

        update_data = project_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        self.db.commit()
        self.db.refresh(project)
        return project

    def delete_project(self, project_id: int) -> bool:
        """删除项目"""
        project = self.get_project(project_id)
        if not project:
            return False
        self.db.delete(project)
        self.db.commit()
        return True

    # ============ 检查表模板管理 ============

    def create_template(self, template_in: ChecklistTemplateCreate, user_id: Optional[int] = None) -> ComplianceChecklistTemplate:
        """创建检查表模板"""
        template = ComplianceChecklistTemplate(
            template_code=template_in.template_code,
            template_name=template_in.template_name,
            template_type=template_in.template_type,
            template_stage=template_in.template_stage,
            description=template_in.description,
            version=template_in.version,
            created_by=user_id,
        )
        self.db.add(template)
        self.db.flush()

        # 批量创建检查项
        if template_in.items:
            for idx, item_in in enumerate(template_in.items):
                item = ComplianceCheckItem(
                    template_id=template.id,
                    category=item_in.category,
                    item_code=item_in.item_code,
                    item_name=item_in.item_name,
                    item_description=item_in.item_description,
                    check_standard=item_in.check_standard,
                    check_method=item_in.check_method,
                    weight=item_in.weight,
                    score=item_in.score,
                    is_required=item_in.is_required,
                    risk_level=item_in.risk_level,
                    reference_docs=item_in.reference_docs,
                    sort_order=item_in.sort_order or idx,
                )
                self.db.add(item)

        self.db.commit()
        self.db.refresh(template)
        return template

    def get_template(self, template_id: int) -> Optional[ComplianceChecklistTemplate]:
        """获取模板详情"""
        return (
            self.db.query(ComplianceChecklistTemplate)
            .options(joinedload(ComplianceChecklistTemplate.items))
            .filter(ComplianceChecklistTemplate.id == template_id)
            .first()
        )

    def list_templates(
        self,
        is_active: Optional[bool] = None,
        template_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> List[ComplianceChecklistTemplate]:
        """获取模板列表"""
        query = self.db.query(ComplianceChecklistTemplate).options(joinedload(ComplianceChecklistTemplate.items))

        if is_active is not None:
            query = query.filter(ComplianceChecklistTemplate.is_active == is_active)
        if template_type:
            query = query.filter(ComplianceChecklistTemplate.template_type == template_type)
        if keyword:
            query = query.filter(
                or_(
                    ComplianceChecklistTemplate.template_name.contains(keyword),
                    ComplianceChecklistTemplate.template_code.contains(keyword),
                )
            )

        return query.order_by(ComplianceChecklistTemplate.created_at.desc()).all()

    def update_template(self, template_id: int, template_in: ChecklistTemplateUpdate) -> Optional[ComplianceChecklistTemplate]:
        """更新模板"""
        template = self.get_template(template_id)
        if not template:
            return None

        update_data = template_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)

        self.db.commit()
        self.db.refresh(template)
        return template

    def delete_template(self, template_id: int) -> bool:
        """删除模板"""
        template = self.get_template(template_id)
        if not template:
            return False
        self.db.delete(template)
        self.db.commit()
        return True

    def _create_checklist_from_template(self, project_id: int, template_id: int) -> ComplianceChecklistInstance:
        """从模板创建项目检查表实例"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError("检查表模板不存在")

        # 创建检查表实例
        checklist = ComplianceChecklistInstance(
            project_id=project_id,
            template_id=template_id,
            template_name=template.template_name,
            total_items=len(template.items),
        )
        self.db.add(checklist)
        self.db.flush()

        # 创建每个检查项的审核记录
        for item in template.items:
            review_item = ComplianceReviewItem(
                checklist_id=checklist.id,
                check_item_id=item.id,
                category=item.category,
                item_name=item.item_name,
                check_standard=item.check_standard,
            )
            self.db.add(review_item)

        return checklist

    # ============ 审核流程 ============

    def submit_review(
        self,
        project_id: int,
        review_in: ComplianceReviewCreate,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        user_dept: Optional[str] = None,
    ) -> ComplianceProject:
        """执行审核操作（提交/分配/退回/通过/不通过）"""
        project = self.get_project_with_details(project_id)
        if not project:
            raise ValueError("项目不存在")

        action = review_in.action
        now = datetime.now()

        # 验证状态流转合法性
        self._validate_status_transition(project.status, action)

        # 更新项目状态
        if action == "submit":
            project.status = "submitted"
            project.submitted_at = now
        elif action == "assign":
            project.status = "reviewing"
            project.reviewer_id = review_in.reviewer_id
            project.reviewer_name = review_in.reviewer_name
        elif action == "review":
            # 处理审核项结果
            if review_in.review_items and project.checklists:
                checklist = project.checklists[0]
                self._update_review_items(checklist, review_in.review_items, user_id)
                # 重新计算得分
                self._calculate_checklist_score(checklist)
                project.total_score = checklist.total_score
        elif action == "return":
            project.status = "returned"
        elif action == "pass":
            project.status = "passed"
            project.reviewed_at = now
            project.conclusion = review_in.conclusion or "通过"
            project.summary = review_in.summary
        elif action == "reject":
            project.status = "rejected"
            project.reviewed_at = now
            project.conclusion = review_in.conclusion or "不通过"
            project.summary = review_in.summary

        # 记录审核流程
        review = ComplianceReview(
            project_id=project_id,
            review_round=self._get_next_review_round(project_id),
            action=action,
            operator_id=user_id,
            operator_name=user_name,
            operator_dept=user_dept,
            opinion=review_in.opinion,
            result_data=review_in.model_dump() if action in ["pass", "reject"] else None,
            attachments=review_in.attachments,
        )
        self.db.add(review)

        self.db.commit()
        self.db.refresh(project)
        return project

    def _validate_status_transition(self, current_status: str, action: str):
        """验证状态流转是否合法"""
        valid_transitions = {
            "draft": ["submit"],
            "submitted": ["assign", "return"],
            "reviewing": ["review", "return", "pass", "reject"],
            "returned": ["submit"],
            "passed": [],
            "rejected": [],
        }
        if action not in valid_transitions.get(current_status, []):
            raise ValueError(f"状态 {current_status} 不允许执行操作 {action}")

    def _get_next_review_round(self, project_id: int) -> int:
        """获取下一个审核轮次"""
        last_review = (
            self.db.query(ComplianceReview)
            .filter(ComplianceReview.project_id == project_id)
            .order_by(ComplianceReview.review_round.desc())
            .first()
        )
        return (last_review.review_round + 1) if last_review else 1

    def _update_review_items(self, checklist: ComplianceChecklistInstance, items_data: List, user_id: Optional[int]):
        """更新审核项结果"""
        now = datetime.now()
        items_by_id = {item.check_item_id: item for item in checklist.review_items}

        for item_data in items_data:
            # 根据check_item_id查找
            for review_item in checklist.review_items:
                if item_data.result is not None:
                    review_item.result = item_data.result
                    review_item.score = item_data.score or 0
                    review_item.issue_description = item_data.issue_description
                    review_item.rectification_suggestion = item_data.rectification_suggestion
                    review_item.evidence = item_data.evidence
                    review_item.reviewer_note = item_data.reviewer_note
                    review_item.reviewed_by = user_id
                    review_item.reviewed_at = now

    def _calculate_checklist_score(self, checklist: ComplianceChecklistInstance):
        """计算检查表得分"""
        total_score = 0
        passed = 0
        failed = 0
        warning = 0
        completed = 0

        for item in checklist.review_items:
            if item.result:
                completed += 1
                if item.result == "pass":
                    passed += 1
                    total_score += item.score
                elif item.result == "fail":
                    failed += 1
                elif item.result == "warning":
                    warning += 1
                    total_score += item.score * 0.5

        checklist.completed_items = completed
        checklist.passed_items = passed
        checklist.failed_items = failed
        checklist.warning_items = warning
        checklist.total_score = total_score

    # ============ 评论管理 ============

    def add_comment(self, project_id: int, comment_in: CommentCreate, user_id: Optional[int] = None, user_name: Optional[str] = None, user_dept: Optional[str] = None) -> ComplianceComment:
        """添加评论/意见"""
        comment = ComplianceComment(
            project_id=project_id,
            parent_id=comment_in.parent_id,
            comment_type=comment_in.comment_type,
            content=comment_in.content,
            author_id=user_id,
            author_name=user_name,
            author_dept=user_dept,
            is_private=comment_in.is_private,
            attachments=comment_in.attachments,
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def update_comment(self, comment_id: int, comment_in: CommentUpdate) -> Optional[ComplianceComment]:
        """更新评论"""
        comment = self.db.query(ComplianceComment).filter(ComplianceComment.id == comment_id).first()
        if not comment:
            return None

        update_data = comment_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(comment, field, value)

        self.db.commit()
        self.db.refresh(comment)
        return comment

    def delete_comment(self, comment_id: int) -> bool:
        """删除评论"""
        comment = self.db.query(ComplianceComment).filter(ComplianceComment.id == comment_id).first()
        if not comment:
            return False
        self.db.delete(comment)
        self.db.commit()
        return True

    # ============ 附件管理 ============

    def add_attachment(
        self,
        project_id: int,
        file_name: str,
        file_path: str,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        category: Optional[str] = None,
        uploader_id: Optional[int] = None,
        uploader_name: Optional[str] = None,
        description: Optional[str] = None,
        is_required: bool = False,
    ) -> ComplianceAttachment:
        """添加附件"""
        attachment = ComplianceAttachment(
            project_id=project_id,
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            mime_type=mime_type,
            category=category,
            uploader_id=uploader_id,
            uploader_name=uploader_name,
            description=description,
            is_required=is_required,
        )
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        return attachment

    def delete_attachment(self, attachment_id: int) -> bool:
        """删除附件"""
        attachment = self.db.query(ComplianceAttachment).filter(ComplianceAttachment.id == attachment_id).first()
        if not attachment:
            return False

        # 删除物理文件
        try:
            if os.path.exists(attachment.file_path):
                os.remove(attachment.file_path)
        except Exception:
            pass

        self.db.delete(attachment)
        self.db.commit()
        return True

    # ============ 统计分析 ============

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        # 基础统计
        base_stats = dict(
            total_projects=self.db.query(func.count(ComplianceProject.id)).scalar() or 0,
            draft_count=self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status == "draft").scalar() or 0,
            pending_count=self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status.in_(["submitted", "reviewing"])).scalar() or 0,
            reviewing_count=self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status == "reviewing").scalar() or 0,
            returned_count=self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status == "returned").scalar() or 0,
            passed_count=self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status == "passed").scalar() or 0,
            rejected_count=self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status == "rejected").scalar() or 0,
        )

        # 平均得分
        avg_score = self.db.query(func.avg(ComplianceProject.total_score)).filter(ComplianceProject.status == "passed").scalar() or 0
        base_stats["avg_score"] = round(float(avg_score), 1)

        # 通过率
        completed = base_stats["passed_count"] + base_stats["rejected_count"]
        base_stats["pass_rate"] = round(base_stats["passed_count"] / completed * 100, 1) if completed > 0 else 0

        # 按项目类型统计
        by_type = {}
        type_stats = self.db.query(ComplianceProject.project_type, func.count(ComplianceProject.id)).group_by(ComplianceProject.project_type).all()
        for t, count in type_stats:
            if t:
                by_type[t] = count
        base_stats["by_type"] = by_type

        # 按月份统计（近6个月）
        by_month = []
        for i in range(5, -1, -1):
            month_start = datetime.now().replace(day=1) - timedelta(days=i*30)
            month_start = month_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year+1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month+1)
            count = self.db.query(func.count(ComplianceProject.id)).filter(
                and_(
                    ComplianceProject.created_at >= month_start,
                    ComplianceProject.created_at < next_month,
                )
            ).scalar() or 0
            by_month.append({
                "month": month_start.strftime("%Y-%m"),
                "count": count,
            })
        base_stats["by_month"] = by_month

        # 平均审核天数
        base_stats["avg_review_days"] = 3.5  # 默认值，后续根据实际数据计算

        return base_stats

    def _get_list_statistics(self) -> Dict[str, Any]:
        """获取列表页统计数据"""
        return {
            "all": self.db.query(func.count(ComplianceProject.id)).scalar() or 0,
            "draft": self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status == "draft").scalar() or 0,
            "pending": self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status.in_(["submitted", "reviewing"])).scalar() or 0,
            "returned": self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status == "returned").scalar() or 0,
            "passed": self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status == "passed").scalar() or 0,
            "rejected": self.db.query(func.count(ComplianceProject.id)).filter(ComplianceProject.status == "rejected").scalar() or 0,
        }

    # ============ 报告生成 ============

    def generate_review_report(self, project_id: int) -> Dict[str, Any]:
        """生成初审报告数据"""
        project = self.get_project_with_details(project_id)
        if not project:
            raise ValueError("项目不存在")

        checklist = project.checklists[0] if project.checklists else None

        # 按类别分组检查项
        categorized_items = {}
        failed_items = []
        warning_items = []

        if checklist:
            for item in checklist.review_items:
                cat = item.category or "其他"
                if cat not in categorized_items:
                    categorized_items[cat] = []
                categorized_items[cat].append(item)

                if item.result == "fail":
                    failed_items.append(item)
                elif item.result == "warning":
                    warning_items.append(item)

        return {
            "project": {
                "id": project.id,
                "project_code": project.project_code,
                "project_name": project.project_name,
                "project_type": project.project_type,
                "project_stage": project.project_stage,
                "applicant": project.applicant,
                "applicant_dept": project.applicant_dept,
                "reviewer_name": project.reviewer_name,
                "status": project.status,
                "total_score": project.total_score,
                "pass_score": project.pass_score,
                "conclusion": project.conclusion,
                "summary": project.summary,
                "submitted_at": project.submitted_at.isoformat() if project.submitted_at else None,
                "reviewed_at": project.reviewed_at.isoformat() if project.reviewed_at else None,
            },
            "checklist": {
                "template_name": checklist.template_name if checklist else "",
                "total_items": checklist.total_items if checklist else 0,
                "completed_items": checklist.completed_items if checklist else 0,
                "passed_items": checklist.passed_items if checklist else 0,
                "failed_items": checklist.failed_items if checklist else 0,
                "warning_items": checklist.warning_items if checklist else 0,
                "total_score": checklist.total_score if checklist else 0,
            } if checklist else None,
            "categorized_items": categorized_items,
            "failed_items": [
                {
                    "item_name": i.item_name,
                    "category": i.category,
                    "issue_description": i.issue_description,
                    "rectification_suggestion": i.rectification_suggestion,
                    "risk_level": i.risk_level,
                }
                for i in failed_items
            ],
            "warning_items": [
                {
                    "item_name": i.item_name,
                    "category": i.category,
                    "issue_description": i.issue_description,
                    "rectification_suggestion": i.rectification_suggestion,
                }
                for i in warning_items
            ],
            "reviews": [
                {
                    "action": r.action,
                    "operator_name": r.operator_name,
                    "opinion": r.opinion,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in project.reviews
            ],
            "generated_at": datetime.now().isoformat(),
        }


# 服务实例工厂
def get_compliance_service(db: Session) -> ComplianceService:
    return ComplianceService(db)
