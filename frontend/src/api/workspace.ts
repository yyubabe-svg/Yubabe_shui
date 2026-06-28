import api, { STORAGE_KEY } from './client'

// 辅助函数：获取认证Headers（URL编码中文用户名）
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const data = JSON.parse(raw)
      if (data.name && typeof data.name === 'string') {
        const encodedName = encodeURIComponent(data.name.trim())
        headers['X-User-Name'] = encodedName
        headers['X-Username'] = encodedName
      }
    }
  } catch {}
  return headers
}

// ==================== 类型定义 ====================

// 表单模板
export interface FormTemplate {
  id: number
  template_code: string
  template_name: string
  template_type: string
  description: string
  version: string
  field_count: number
}

export interface FormField {
  id: number
  field_id: number
  field_key: string
  field_label: string
  field_type: string
  required: boolean
  extracted_value?: string
  confirmed_value?: string
  confidence?: number
  source_page?: number
  source_section?: string
  source_text?: string
}

export interface FormFillTaskDetail {
  id: number
  project_id: number
  template_id: number
  template_name: string
  document_id?: number
  status: string
  progress: number
  error_message?: string
  output_filename?: string
  fields: FormField[]
  created_at: string
}

export interface FormFillTaskItem {
  id: number
  template_name: string
  status: string
  progress: number
  output_filename?: string
  created_at: string
}

// 章节模板（树形）
export interface SectionTemplate {
  id: number
  chapter_number: string
  title: string
  level: number
  description?: string
  children: SectionTemplate[]
}

export interface SectionDraft {
  id: number
  paragraph_id: string
  parent_paragraph_id?: string
  paragraph_type: string
  level?: number
  content: string
  status: string
  sort_order: number
}

export interface SectionTaskDetail {
  id: number
  project_id: number
  template_id: number
  template_title: string
  status: string
  progress: number
  outline_json?: any
  assembled_content?: string
  output_filename?: string
  drafts: SectionDraft[]
  created_at: string
}

// AI初审
export type IssueSeverity = 'critical' | 'major' | 'minor' | 'suggestion'
export type IssueCategory = 'param_completeness' | 'code_compliance' | 'chapter_completeness' | 'value_consistency' | 'format_standard'
export type IssueStatus = 'open' | 'accepted' | 'ignored' | 'resolved'

export interface ReviewIssue {
  id: number
  severity: IssueSeverity
  category: IssueCategory
  chapter_path?: string
  page_number?: number
  location_desc?: string
  description: string
  basis_code?: string
  suggestion?: string
  original_text?: string
  status: IssueStatus
  note?: string
}

export interface ReviewTaskDetail {
  id: number
  project_id: number
  document_id: number
  document_title: string
  status: string
  progress: number
  total_score?: number
  summary?: string
  issue_count_critical: number
  issue_count_major: number
  issue_count_minor: number
  issue_count_suggestion: number
  issues: ReviewIssue[]
  created_at: string
}

// 专家意见回复
export interface ExpertOpinionItem {
  id: number
  opinion_index: number
  expert_name?: string
  major_category: string
  major_category_name?: string
  opinion_type?: string
  content: string
  page_number?: number
  chapter_path?: string
  reply?: {
    reply_content: string
    modify_status?: string
    modify_location?: string
    modify_page?: string
    status: string
  }
}

export interface ExpertReplyTaskDetail {
  id: number
  project_id: number
  status: string
  progress: number
  meeting_name?: string
  meeting_date?: string
  opinion_count: number
  output_filename?: string
  opinions: ExpertOpinionItem[]
  created_at: string
}

// 资料检索
export interface SearchResult {
  document_id?: number
  title: string
  page_number?: number
  section_title?: string
  chapter_path?: string
  text: string
  score?: number
}

export interface AskResponse {
  answer: string
  sources: Array<{
    document_id?: number
    title: string
    page_number?: number
    section?: string
    snippet: string
  }>
}

// 项目概览
export interface ProjectOverview {
  project: {
    id: number
    name: string
    code: string
    type: string
    stage: string
  }
  statistics: {
    documents: number
    form_tasks: number
    form_completed: number
    section_tasks: number
    review_tasks: number
    reply_tasks: number
  }
  recent_tasks: Array<{
    type: string
    name: string
    status: string
    created_at: string
  }>
}

// 文档
export interface ProjectDocument {
  id: number
  project_id: number
  title: string
  file_type: string
  original_filename: string
  file_size: number
  file_path: string
  parse_status: string
  chunk_count: number
  table_count: number
  total_pages?: number
  is_report: boolean
  is_expert_opinion: boolean
  created_at: string
}

// 任务列表项
export interface WorkspaceTask {
  id: number
  task_type: string
  task_name: string
  status: string
  progress: number
  output_filename?: string
  error_message?: string
  created_at: string
}

// 工具函数：POST下载Blob
export async function downloadPost(url: string, data?: any): Promise<Blob> {
  const fullUrl = `/api${url}`
  const response = await fetch(fullUrl, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: data ? JSON.stringify(data) : undefined,
  })
  if (!response.ok) throw new Error('下载失败')
  return response.blob()
}

// 工具函数：触发浏览器下载Blob
export function triggerBlobDownload(blob: Blob, defaultFilename: string, contentDisposition?: string | null) {
  // 尝试从 Content-Disposition 中提取文件名
  let filename = defaultFilename
  if (contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
    const plainMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
    const match = utf8Match || plainMatch
    if (match) {
      try {
        filename = decodeURIComponent(match[1])
      } catch {
        filename = match[1]
      }
    }
  }
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000)
}

// ==================== API 封装 ====================

export const workspaceApi = {
  // ========== 项目概览 ==========
  getProjectOverview: (projectId: number | string) =>
    api.get<ProjectOverview>(`/workspace/projects/${projectId}/overview`).then(r => r.data),

  // ========== 资料检索与问答 ==========
  search: (params: { q: string; project_id?: number | string; file_types?: string; limit?: number }) =>
    api.get<{ items: SearchResult[]; total: number }>('/workspace/search', { params }).then(r => r.data),

  ask: (data: { question: string; project_id?: number | string }) =>
    api.post<AskResponse>('/workspace/ask', data).then(r => r.data),

  // ========== 表单填报 ==========
  listFormTemplates: (projectType?: string) =>
    api.get<{ items: FormTemplate[] }>('/workspace/form-templates', { params: { project_type: projectType } }).then(r => r.data),

  createFormTask: (projectId: number | string, data: { template_id: number; document_id?: number }) =>
    api.post<{ task_id: number; status: string }>(`/workspace/projects/${projectId}/form-tasks`, data).then(r => r.data),

  extractFormFields: (taskId: number | string) =>
    api.post<{ status: string; progress: number }>(`/workspace/form-tasks/${taskId}/extract`).then(r => r.data),

  getFormTask: (taskId: number | string) =>
    api.get<FormFillTaskDetail>(`/workspace/form-tasks/${taskId}`).then(r => r.data),

  updateFormFields: (taskId: number | string, fields: Record<string, string>) =>
    api.put<{ message: string }>(`/workspace/form-tasks/${taskId}/fields`, { fields }).then(r => r.data),

  fillFormTemplate: (taskId: number | string) =>
    api.post<{ status: string; output_file: string }>(`/workspace/form-tasks/${taskId}/fill`).then(r => r.data),

  downloadFormResult: (taskId: number | string) =>
    `/api/workspace/form-tasks/${taskId}/download`,

  listProjectFormTasks: (projectId: number | string) =>
    api.get<{ items: FormFillTaskItem[] }>(`/workspace/projects/${projectId}/form-tasks`).then(r => r.data),

  // ========== 报告章节生成 ==========
  getSectionTemplates: (projectType?: string) =>
    api.get<{ items: SectionTemplate[] }>('/workspace/section-templates', { params: { project_type: projectType } }).then(r => r.data),

  createSectionTask: (projectId: number | string, data: { template_id: number; document_ids?: number[]; params?: any }) =>
    api.post<{ task_id: number }>(`/workspace/projects/${projectId}/section-tasks`, data).then(r => r.data),

  generateSectionOutline: (taskId: number | string) =>
    api.post<{ outline: any }>(`/workspace/section-tasks/${taskId}/generate-outline`).then(r => r.data),

  getSectionTask: (taskId: number | string) =>
    api.get<SectionTaskDetail>(`/workspace/section-tasks/${taskId}`).then(r => r.data),

  // 流式生成（返回fetch Promise，SSE由调用方处理）
  streamSectionGenerate: (taskId: number | string, startFrom?: string, signal?: AbortSignal): Promise<Response> => {
    const url = new URL(`/api/workspace/section-tasks/${taskId}/generate`, window.location.origin)
    if (startFrom) url.searchParams.set('start_from', startFrom)
    return fetch(url.toString(), {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ start_from: startFrom }),
      signal,
    })
  },

  updateSectionDraft: (draftId: number | string, data: { content: string }) =>
    api.patch<{ message: string }>(`/workspace/section-drafts/${draftId}`, data).then(r => r.data),

  acceptSectionDraft: (draftId: number | string) =>
    api.post<{ message: string }>(`/workspace/section-drafts/${draftId}/accept`).then(r => r.data),

  exportSection: async (taskId: number | string): Promise<{ blob: Blob; contentDisposition: string | null }> => {
    const response = await api.post(`/workspace/section-tasks/${taskId}/export`, {}, {
      responseType: 'blob',
      timeout: 300000,
    })
    return {
      blob: response.data as Blob,
      contentDisposition: response.headers['content-disposition'] || null,
    }
  },

  // ========== AI初审 ==========
  createReviewTask: (projectId: number | string, data: { document_id: number; dimensions?: string[] }) =>
    api.post<{ task_id: number }>(`/workspace/projects/${projectId}/review-tasks`, data).then(r => r.data),

  runReview: (taskId: number | string) =>
    api.post<{ message: string }>(`/workspace/review-tasks/${taskId}/run`).then(r => r.data),

  getReviewTask: (taskId: number | string) =>
    api.get<ReviewTaskDetail>(`/workspace/review-tasks/${taskId}`).then(r => r.data),

  // SSE进度流
  getReviewStreamUrl: (taskId: number | string) =>
    `/api/workspace/review-tasks/${taskId}/stream`,

  updateReviewIssue: (issueId: number | string, data: { status?: IssueStatus; note?: string }) =>
    api.patch<{ message: string }>(`/workspace/review-issues/${issueId}`, data).then(r => r.data),

  exportReviewReport: async (taskId: number | string): Promise<{ blob: Blob; contentDisposition: string | null }> => {
    const response = await api.post(`/workspace/review-tasks/${taskId}/export`, {}, {
      responseType: 'blob',
      timeout: 300000,
    })
    return {
      blob: response.data as Blob,
      contentDisposition: response.headers['content-disposition'] || null,
    }
  },

  // ========== 专家意见回复 ==========
  createExpertReplyTask: (projectId: number | string, data: {
    opinion_document_id: number;
    report_document_id?: number;
    meeting_name?: string;
    meeting_date?: string;
  }) =>
    api.post<{ task_id: number }>(`/workspace/projects/${projectId}/expert-reply-tasks`, data).then(r => r.data),

  parseExpertOpinions: (taskId: number | string) =>
    api.post<{ message: string }>(`/workspace/expert-reply-tasks/${taskId}/parse-opinions`).then(r => r.data),

  getExpertReplyTask: (taskId: number | string) =>
    api.get<ExpertReplyTaskDetail>(`/workspace/expert-reply-tasks/${taskId}`).then(r => r.data),

  generateOpinionReply: (opinionId: number | string) =>
    api.post<{ reply_content: string }>(`/workspace/expert-opinions/${opinionId}/generate-reply`).then(r => r.data),

  generateAllReplies: (taskId: number | string) =>
    api.post<{ message: string }>(`/workspace/expert-reply-tasks/${taskId}/generate-all`).then(r => r.data),

  updateOpinionReply: (opinionId: number | string, data: {
    reply_content?: string;
    modify_status?: string;
    modify_location?: string;
    modify_page?: string;
  }) =>
    api.patch<{ message: string }>(`/workspace/expert-opinions/${opinionId}`, data).then(r => r.data),

  exportReplyTable: async (taskId: number | string): Promise<{ blob: Blob; contentDisposition: string | null }> => {
    const response = await api.post(`/workspace/expert-reply-tasks/${taskId}/export`, {}, {
      responseType: 'blob',
      timeout: 300000,
    })
    return {
      blob: response.data as Blob,
      contentDisposition: response.headers['content-disposition'] || null,
    }
  },

  // ========== 文档管理 ==========
  listDocuments: (projectId: number | string) =>
    api.get<{ items: ProjectDocument[] }>(`/workspace/projects/${projectId}/documents`).then(r => r.data),

  uploadDocument: (projectId: number | string, file: File, onProgress?: (percent: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<{ document_id: number; message: string; parse_status: string }>(
      `/workspace/projects/${projectId}/documents`,
      formData,
      {
        timeout: 300000,
        onUploadProgress: (e: any) => {
          if (onProgress && e.total) {
            onProgress(Math.round((e.loaded / e.total) * 100))
          }
        },
      }
    ).then(r => r.data)
  },

  setDocumentAsReport: (projectId: number | string, documentId: number | string) =>
    api.put<{ message: string }>(`/workspace/projects/${projectId}/documents/${documentId}/set-report`, {}).then(r => r.data),

  setDocumentAsExpertOpinion: (projectId: number | string, documentId: number | string) =>
    api.put<{ message: string }>(`/workspace/projects/${projectId}/documents/${documentId}/set-expert-opinion`, {}).then(r => r.data),

  deleteDocument: (projectId: number | string, documentId: number | string) =>
    api.delete<{ message: string }>(`/workspace/projects/${projectId}/documents/${documentId}`).then(r => r.data),

  // ========== 任务列表 ==========
  listAllTasks: (projectId: number | string) =>
    api.get<{ items: WorkspaceTask[] }>(`/workspace/projects/${projectId}/tasks`).then(r => r.data),
}
