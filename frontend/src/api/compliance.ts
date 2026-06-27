/**
 * 合规初审模块 API 客户端
 */
import api from './client'

// ============ 类型定义 ============

export type ProjectStatus = 'draft' | 'submitted' | 'reviewing' | 'returned' | 'passed' | 'rejected'
export type ReviewResult = 'pass' | 'fail' | 'warning' | 'na'
export type PriorityLevel = 'low' | 'normal' | 'high' | 'urgent'
export type ReviewAction = 'submit' | 'assign' | 'review' | 'return' | 'pass' | 'reject'

export interface ExtractedParam {
  param_name: string
  param_value: string
  source_text?: string
  confidence: string
}

export interface ReviewIssue {
  issue_type: string
  description: string
  severity: string
  source_ref?: string
}

export interface ReviewSuggestion {
  suggestion: string
  related_param?: string
  standard_ref?: string
}

export interface CheckItem {
  id: number
  template_id: number
  category?: string
  item_code?: string
  item_name: string
  item_description?: string
  check_standard?: string
  check_method?: string
  weight: number
  score: number
  is_required: boolean
  risk_level: string
  reference_docs?: any[]
  sort_order: number
  is_active: boolean
  created_at: string
}

export interface ChecklistTemplate {
  id: number
  template_code: string
  template_name: string
  template_type?: string
  template_stage?: string
  description?: string
  version: string
  is_active: boolean
  created_by?: number
  created_at: string
  updated_at: string
  items?: CheckItem[]
  item_count?: number
}

export interface ReviewItem {
  id: number
  checklist_id: number
  check_item_id: number
  category?: string
  item_name: string
  check_standard?: string
  weight: number
  full_score: number
  is_required: boolean
  risk_level: string
  result?: ReviewResult
  score: number
  issue_description?: string
  rectification_suggestion?: string
  evidence?: any[]
  reviewer_note?: string
  reviewed_by?: number
  reviewed_at?: string
  created_at: string
}

export interface ChecklistInstance {
  id: number
  project_id: number
  template_id: number
  template_name: string
  total_items: number
  completed_items: number
  passed_items: number
  failed_items: number
  warning_items: number
  total_score: number
  created_at: string
  review_items?: ReviewItem[]
}

export interface ComplianceReview {
  id: number
  project_id: number
  review_round: number
  action: ReviewAction
  operator_id?: number
  operator_name?: string
  operator_dept?: string
  opinion?: string
  result_data?: any
  attachments?: any[]
  created_at: string
}

export interface Comment {
  id: number
  project_id: number
  parent_id?: number
  comment_type: string
  content: string
  author_id?: number
  author_name?: string
  author_dept?: string
  is_private: boolean
  attachments?: any[]
  created_at: string
  updated_at: string
  replies?: Comment[]
}

export interface Attachment {
  id: number
  project_id: number
  file_name: string
  file_path: string
  file_type?: string
  file_size?: number
  mime_type?: string
  category?: string
  uploader_id?: number
  uploader_name?: string
  description?: string
  is_required: boolean
  created_at: string
}

export interface ComplianceProject {
  id: number
  project_code: string
  project_name: string
  project_type?: string
  project_stage?: string
  applicant?: string
  applicant_dept?: string
  reviewer_id?: number
  reviewer_name?: string
  status: ProjectStatus
  priority: PriorityLevel
  total_score: number
  pass_score: number
  conclusion?: string
  summary?: string
  submitted_at?: string
  reviewed_at?: string
  deadline?: string
  created_by?: number
  created_at: string
  updated_at: string
  checklist_count?: number
  attachment_count?: number
  comment_count?: number
}

export interface ComplianceProjectDetail extends ComplianceProject {
  checklists?: ChecklistInstance[]
  reviews?: ComplianceReview[]
  comments?: Comment[]
  attachments?: Attachment[]
}

export interface ProjectListResponse {
  items: ComplianceProject[]
  total: number
  page: number
  page_size: number
  statistics: {
    all: number
    draft: number
    pending: number
    returned: number
    passed: number
    rejected: number
  }
}

export interface ComplianceStatistics {
  total_projects: number
  draft_count: number
  pending_count: number
  reviewing_count: number
  returned_count: number
  passed_count: number
  rejected_count: number
  avg_score: number
  avg_review_days: number
  pass_rate: number
  by_type: Record<string, number>
  by_month: { month: string; count: number }[]
}

export interface ProjectCreateData {
  project_code: string
  project_name: string
  project_type?: string
  project_stage?: string
  applicant?: string
  applicant_dept?: string
  priority?: PriorityLevel
  pass_score?: number
  deadline?: string
  template_id?: number
}

export interface ProjectUpdateData {
  project_name?: string
  project_type?: string
  project_stage?: string
  applicant?: string
  applicant_dept?: string
  reviewer_id?: number
  reviewer_name?: string
  priority?: PriorityLevel
  pass_score?: number
  deadline?: string
  status?: ProjectStatus
}

export interface ReviewSubmitData {
  action: ReviewAction
  opinion?: string
  reviewer_id?: number
  reviewer_name?: string
  attachments?: any[]
  review_items?: Array<{
    result?: ReviewResult
    score?: number
    issue_description?: string
    rectification_suggestion?: string
    evidence?: any[]
    reviewer_note?: string
  }>
  conclusion?: string
  summary?: string
}

export interface CommentCreateData {
  content: string
  comment_type?: string
  is_private?: boolean
  attachments?: any[]
  parent_id?: number
}

export interface BatchAssignData {
  project_ids: number[]
  reviewer_id: number
  reviewer_name: string
}

// ============ API 函数 ============

// 统计
export const getStatistics = () =>
  api.get<ComplianceStatistics>('/compliance/statistics').then(r => r.data)

// 项目管理
export const createProject = (data: ProjectCreateData) =>
  api.post<ComplianceProject>('/compliance/projects', data).then(r => r.data)

export const getProjects = (params?: {
  page?: number
  page_size?: number
  status?: string
  project_type?: string
  priority?: string
  keyword?: string
  reviewer_id?: number
}) =>
  api.get<ProjectListResponse>('/compliance/projects', { params }).then(r => r.data)

export const getProject = (id: number) =>
  api.get<ComplianceProjectDetail>(`/compliance/projects/${id}`).then(r => r.data)

export const updateProject = (id: number, data: ProjectUpdateData) =>
  api.put<ComplianceProject>(`/compliance/projects/${id}`, data).then(r => r.data)

export const deleteProject = (id: number) =>
  api.delete(`/compliance/projects/${id}`).then(r => r.data)

export const applyChecklistTemplate = (projectId: number, templateId: number) =>
  api.post(`/compliance/projects/${projectId}/submit-checklist`, null, {
    params: { template_id: templateId }
  }).then(r => r.data)

// 审核流程
export const submitReview = (projectId: number, data: ReviewSubmitData) =>
  api.post<ComplianceProjectDetail>(`/compliance/projects/${projectId}/review`, data).then(r => r.data)

export const getReviewHistory = (projectId: number) =>
  api.get<ComplianceReview[]>(`/compliance/projects/${projectId}/reviews`).then(r => r.data)

export const batchAssign = (data: BatchAssignData) =>
  api.post('/compliance/projects/batch-assign', data).then(r => r.data)

// 检查表模板
export const createTemplate = (data: Partial<ChecklistTemplate> & { items?: Partial<CheckItem>[] }) =>
  api.post<ChecklistTemplate>('/compliance/templates', data).then(r => r.data)

export const getTemplates = (params?: {
  is_active?: boolean
  template_type?: string
  keyword?: string
}) =>
  api.get<ChecklistTemplate[]>('/compliance/templates', { params }).then(r => r.data)

export const getTemplate = (id: number) =>
  api.get<ChecklistTemplate>(`/compliance/templates/${id}`).then(r => r.data)

export const updateTemplate = (id: number, data: Partial<ChecklistTemplate>) =>
  api.put<ChecklistTemplate>(`/compliance/templates/${id}`, data).then(r => r.data)

export const deleteTemplate = (id: number) =>
  api.delete(`/compliance/templates/${id}`).then(r => r.data)

// 评论
export const addComment = (projectId: number, data: CommentCreateData) =>
  api.post<Comment>(`/compliance/projects/${projectId}/comments`, data).then(r => r.data)

export const getComments = (projectId: number) =>
  api.get<Comment[]>(`/compliance/projects/${projectId}/comments`).then(r => r.data)

export const updateComment = (commentId: number, data: { content?: string; comment_type?: string; is_private?: boolean }) =>
  api.put<Comment>(`/compliance/comments/${commentId}`, data).then(r => r.data)

export const deleteComment = (commentId: number) =>
  api.delete(`/compliance/comments/${commentId}`).then(r => r.data)

// 附件
export const uploadAttachment = (
  projectId: number,
  file: File,
  options?: {
    file_type?: string
    category?: string
    description?: string
    is_required?: boolean
    onProgress?: (percent: number) => void
  }
) => {
  const formData = new FormData()
  formData.append('file', file)
  if (options?.file_type) formData.append('file_type', options.file_type)
  if (options?.category) formData.append('category', options.category)
  if (options?.description) formData.append('description', options.description)
  if (options?.is_required !== undefined) formData.append('is_required', String(options.is_required))

  return api.post<Attachment>(`/compliance/projects/${projectId}/attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: options?.onProgress
      ? (e) => {
          if (e.total) options.onProgress!(Math.round((e.loaded * 100) / e.total))
        }
      : undefined,
  }).then(r => r.data)
}

export const deleteAttachment = (attachmentId: number) =>
  api.delete(`/compliance/attachments/${attachmentId}`).then(r => r.data)

// 报告
export const generateReport = (projectId: number) =>
  api.get(`/compliance/projects/${projectId}/report`).then(r => r.data)

// ============ 辅助函数 ============

export const getStatusLabel = (status: ProjectStatus): string => {
  const labels: Record<ProjectStatus, string> = {
    draft: '草稿',
    submitted: '待审核',
    reviewing: '审核中',
    returned: '已退回',
    passed: '已通过',
    rejected: '不通过',
  }
  return labels[status]
}

export const getStatusColor = (status: ProjectStatus): string => {
  const colors: Record<ProjectStatus, string> = {
    draft: 'bg-gray-100 text-gray-700',
    submitted: 'bg-blue-100 text-blue-700',
    reviewing: 'bg-yellow-100 text-yellow-700',
    returned: 'bg-orange-100 text-orange-700',
    passed: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
  }
  return colors[status]
}

export const getPriorityLabel = (priority: PriorityLevel): string => {
  const labels: Record<PriorityLevel, string> = {
    low: '低',
    normal: '普通',
    high: '高',
    urgent: '紧急',
  }
  return labels[priority]
}

export const getPriorityColor = (priority: PriorityLevel): string => {
  const colors: Record<PriorityLevel, string> = {
    low: 'text-gray-500',
    normal: 'text-blue-600',
    high: 'text-orange-600',
    urgent: 'text-red-600 font-semibold',
  }
  return colors[priority]
}

export const getResultLabel = (result: ReviewResult): string => {
  const labels: Record<ReviewResult, string> = {
    pass: '通过',
    fail: '不通过',
    warning: '警告',
    na: '不适用',
  }
  return labels[result]
}

export const getResultColor = (result: ReviewResult): string => {
  const colors: Record<ReviewResult, string> = {
    pass: 'bg-green-100 text-green-700 border-green-200',
    fail: 'bg-red-100 text-red-700 border-red-200',
    warning: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    na: 'bg-gray-100 text-gray-600 border-gray-200',
  }
  return colors[result]
}
