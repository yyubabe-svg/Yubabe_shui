"""通用表格填报引擎 Pydantic 模型"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


# ------------------------------------------------------------------
# 枚举
# ------------------------------------------------------------------

class LocatorTypeEnum(str, Enum):
    """定位方式"""
    TABLE_CELL = "table_cell"
    BOOKMARK = "bookmark"
    LABEL_ADJACENT = "label_adjacent"


class FieldTypeEnum(str, Enum):
    """字段类型"""
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    CHECKBOX = "checkbox"
    DATE = "date"
    NUMBER = "number"


class TaskStatusEnum(str, Enum):
    """任务状态"""
    PENDING = "pending"
    EXTRACTING = "extracting"
    FILLING = "filling"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"


# ------------------------------------------------------------------
# 定位器配置
# ------------------------------------------------------------------

class TableCellLocator(BaseModel):
    """表格单元格定位 (table_idx, row, col)"""
    table_idx: int = Field(..., description="表格索引（从0开始）")
    row: int = Field(..., description="行索引（从0开始）")
    col: int = Field(..., description="列索引（从0开始）")


class BookmarkLocator(BaseModel):
    """Word 书签定位"""
    bookmark: str = Field(..., description="书签名称")


class LabelDirectionEnum(str, Enum):
    """标签相邻方向"""
    RIGHT = "right"
    LEFT = "left"
    BELOW = "below"
    ABOVE = "above"


class LabelAdjacentLocator(BaseModel):
    """标签相邻定位"""
    label_text: str = Field(..., description="标签文本")
    direction: LabelDirectionEnum = Field(LabelDirectionEnum.RIGHT, description="查找方向")
    # 可选：限定在某个表格内搜索
    table_idx: Optional[int] = Field(None, description="限定表格索引")


class FieldLocator(BaseModel):
    """通用字段定位器"""
    locator_type: LocatorTypeEnum
    table_cell: Optional[TableCellLocator] = None
    bookmark: Optional[BookmarkLocator] = None
    label_adjacent: Optional[LabelAdjacentLocator] = None


# ------------------------------------------------------------------
# 字段提取/填充值
# ------------------------------------------------------------------

class ExtractedFieldValue(BaseModel):
    """LLM 提取的单个字段值"""
    field_key: str
    value: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    source_text: Optional[str] = None
    source_section: Optional[str] = None


class FieldFillData(BaseModel):
    """待填充的字段数据（用户确认后）"""
    field_key: str
    value: str
    is_checked: Optional[bool] = None  # 用于 checkbox 类型


# ------------------------------------------------------------------
# 请求 / 响应
# ------------------------------------------------------------------

class CreateTaskRequest(BaseModel):
    """创建填报任务请求"""
    project_id: int
    template_id: int
    document_id: int
    created_by: Optional[str] = None


class CreateTaskResponse(BaseModel):
    """创建任务响应"""
    task_id: int
    status: str
    message: str = "任务创建成功"


class ExtractFieldsRequest(BaseModel):
    """提取字段请求"""
    task_id: int


class ExtractFieldsResponse(BaseModel):
    """提取字段响应"""
    task_id: int
    status: str
    fields: List[ExtractedFieldValue] = []
    warnings: List[str] = []
    message: Optional[str] = None


class FillTemplateRequest(BaseModel):
    """填充模板请求"""
    task_id: int
    confirmed_data: Dict[str, Any] = Field(
        ..., description="用户确认后的字段数据，key 为 field_key，value 为填充值或布尔值（checkbox）"
    )


class FillTemplateResponse(BaseModel):
    """填充模板响应"""
    task_id: int
    status: str
    output_file: Optional[str] = None
    download_url: Optional[str] = None
    filled_count: int = 0
    warnings: List[str] = []
    message: Optional[str] = None


class TaskDetailResponse(BaseModel):
    """任务详情"""
    id: int
    project_id: int
    template_id: int
    document_id: Optional[int] = None
    status: str
    progress: int = 0
    output_file_path: Optional[str] = None
    output_filename: Optional[str] = None
    error_message: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    confirmed_data: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class FieldValueItem(BaseModel):
    """字段值项（用于列表展示）"""
    field_id: int
    field_key: str
    field_label: str
    field_type: str
    required: bool = True
    extracted_value: Optional[str] = None
    confirmed_value: Optional[str] = None
    confidence: Optional[float] = None
    source_text: Optional[str] = None
    source_section: Optional[str] = None
