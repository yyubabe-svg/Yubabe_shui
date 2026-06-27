import api from './client'

// ==================== 类型定义 ====================

export interface Project {
  id: number
  project_code: string
  project_name: string
  project_type: string
  project_type_name?: string
  design_stage?: string
  design_stage_name?: string
  client?: string
  designer?: string
  department?: string
  location?: string
  river_basin?: string
  status: string
  total_investment?: number
  document_count: number
  form_task_count?: number
  section_task_count?: number
  review_task_count?: number
  reply_task_count?: number
  // 前端兼容别名
  name: string    // = project_name
  code: string    // = project_code
  stage: string   // = design_stage_name
  doc_count: number  // = document_count
  created_at: string
  updated_at: string
}

export interface ProjectDetail extends Project {
  project_grade?: string
  scale_type?: string
  main_building_level?: number
  flood_std_design?: string
  flood_std_check?: string
  catchment_area?: number
  river_governance_length?: number
  embankment_length?: number
  report_file_id?: number
}

export interface ProjectCreate {
  project_name: string
  project_type: string
  design_stage?: string
  client?: string
  designer?: string
  location?: string
}

export interface ProjectUpdate {
  project_name?: string
  project_type?: string
  design_stage?: string
  client?: string
  designer?: string
  location?: string
  department?: string
}

export interface ProjectListResponse {
  items: Project[]
  total: number
}

export interface ProjectTypeOption {
  value: string
  label: string
}

export interface ProjectTypeOptionsResponse {
  project_types: ProjectTypeOption[]
  design_stages: ProjectTypeOption[]
}

export interface ProjectDocument {
  id: number
  title: string
  file_type: string
  original_filename: string
  file_size: number
  parse_status: string
  table_count?: number
  total_pages?: number
  created_at: string
}

export interface ProjectDocumentListResponse {
  items: ProjectDocument[]
}

export interface UploadReportResponse {
  document_id: number
  message: string
}

// ==================== 工具函数 ====================

function mapProject(p: any): Project {
  return {
    ...p,
    name: p.project_name || p.name || '',
    code: p.project_code || p.code || '',
    stage: p.design_stage_name || p.design_stage || p.stage || '',
    doc_count: p.document_count || p.doc_count || 0,
  }
}

// ==================== API 封装 ====================

export const projectsApi = {
  // 获取项目类型和阶段选项
  getTypeOptions: () =>
    api.get<ProjectTypeOptionsResponse>('/projects/types/options').then(r => r.data),

  // 获取项目列表
  list: (params?: { keyword?: string; project_type?: string; design_stage?: string }) =>
    api.get<ProjectListResponse>('/projects', { params }).then(r => ({
      ...r.data,
      items: r.data.items.map(mapProject)
    })),

  // 获取项目详情
  get: (id: number | string) =>
    api.get<ProjectDetail>(`/projects/${id}`).then(r => mapProject(r.data) as ProjectDetail),

  // 创建项目
  create: (data: ProjectCreate) =>
    api.post<{ id: number; project_code: string; project_name: string; message: string }>('/projects', data)
      .then(r => r.data),

  // 更新项目
  update: (id: number | string, data: ProjectUpdate) =>
    api.put<{ message: string }>(`/projects/${id}`, data).then(r => r.data),

  // 删除项目（归档）
  delete: (id: number | string) =>
    api.delete<{ message: string }>(`/projects/${id}`).then(r => r.data),

  // 获取项目文档列表
  listDocuments: (projectId: number | string) =>
    api.get<ProjectDocumentListResponse>(`/projects/${projectId}/documents`).then(r => r.data),

  // 上传项目报告
  uploadReport: (projectId: number | string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<UploadReportResponse>(`/projects/${projectId}/upload-report`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    }).then(r => r.data)
  },
}
