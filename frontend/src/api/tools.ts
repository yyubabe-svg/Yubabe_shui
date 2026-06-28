import api from './client'

// ==================== 水利计算 ====================

export interface CalcParamDef {
  key: string
  label: string
  type: 'number' | 'select' | 'text'
  unit?: string
  default?: any
  required?: boolean
  hint?: string
  options?: { value: any; label: string }[]
}

export interface CalcTypeDef {
  id: string
  name: string
  category: string
  desc: string
  params: CalcParamDef[]
  code_basis: string
}

export interface CalcStep {
  description: string
  formula: string
  inputs: Record<string, any>
  result: any
  unit: string
}

export interface CalcResult {
  calc_type: string
  calc_name: string
  success: boolean
  inputs: Record<string, any>
  outputs: Record<string, any>
  steps: CalcStep[]
  code_basis: string
  notes: string
  warnings: string[]
  review_required: boolean
  history_id?: number
}

export interface CalcHistoryItem {
  id: number
  project_id?: number
  calc_type: string
  calc_name: string
  category?: string
  label?: string
  outputs: Record<string, any>
  warnings?: string[]
  code_basis?: string
  is_favorite: number
  created_at?: string
}

// ==================== 历史项目复用 ====================

export interface SimilarProject {
  id: number
  project_code: string
  project_name: string
  project_type: string
  project_type_name: string
  design_stage?: string
  location?: string
  river_basin?: string
  total_investment?: number
  doc_count: number
  match_score: number
  match_reasons: string[]
  created_at?: string
}

// ==================== CAD 图纸检查 ====================

export interface CadDrawingInfo {
  filename: string
  file_size: number
  parse_status: string
  drawing_number?: string
  drawing_name?: string
  scale?: string
  date?: string
  designer?: string
  reviewer?: string
  chief?: string
  major?: string
  project_name?: string
  texts_found?: number
  blocks_found?: number
  error?: string
  warnings?: string[]
}

export interface CadCheckResult {
  total_files: number
  parsed_count: number
  drawings: CadDrawingInfo[]
  catalog: Array<{
    index: number
    drawing_number: string
    drawing_name: string
    scale: string
    major: string
    date: string
    filename: string
  }>
  issues: Array<{
    file?: string
    severity: 'error' | 'major' | 'minor' | 'warning'
    message: string
  }>
  summary: {
    total: number
    issues_total: number
    issues_critical: number
    issues_major: number
    issues_minor: number
    issues_warning: number
  }
}

// ==================== GIS 分析 ====================

export interface GisAnalysisResult {
  success: boolean
  limited?: boolean
  message?: string
  install_hint?: string
  analysis_type: string
  file_count: number
  results: Array<{
    filename: string
    file_size: number
    ext: string
    status: string  // 'processed' | 'limited' | 'error' | 'unsupported'
    feature_count?: number
    geometry_type?: string[]
    crs?: string
    bounds?: number[]
    columns?: string[]
    area_km2?: number
    length_km?: number
    raster_width?: number
    raster_height?: number
    resolution?: number[]
    band_count?: number
    min_value?: number
    max_value?: number
    mean_value?: number
    slope_min?: number
    slope_max?: number
    slope_mean?: number
    slope_classes?: Record<string, number>
    attribute_preview?: any[]
    error?: string
    message?: string
  }>
  supported_formats: { vector: string[]; raster: string[] }
  future_features: string[]
}

// ==================== API 封装 ====================

export const toolsApi = {
  // ========== 水利计算 ==========
  listCalcTypes: () =>
    api.get<{ categories: Array<{ category: string; items: CalcTypeDef[] }>; total: number }>('/tools/calc/types').then(r => r.data),

  compute: (data: { calc_type: string; params: Record<string, any>; label?: string; save?: boolean }, projectId?: number | string) =>
    api.post<CalcResult>('/tools/calc/compute', data, { params: projectId ? { project_id: projectId } : {} }).then(r => r.data),

  listCalcHistory: (params?: { project_id?: number | string; calc_type?: string; limit?: number }) =>
    api.get<{ items: CalcHistoryItem[]; total: number }>('/tools/calc/history', { params }).then(r => r.data),

  getCalcHistory: (id: number | string) =>
    api.get<CalcHistoryItem & { inputs: Record<string, any>; steps: CalcStep[]; notes?: string }>(`/tools/calc/history/${id}`).then(r => r.data),

  deleteCalcHistory: (id: number | string) =>
    api.delete(`/tools/calc/history/${id}`).then(r => r.data),

  // ========== 历史项目复用 ==========
  findSimilar: (params: {
    project_type?: string
    location_keyword?: string
    river_basin_keyword?: string
    project_type_name_keyword?: string
    exclude_project_id?: number
    limit?: number
  }) =>
    api.get<{ items: SimilarProject[]; total: number }>('/tools/history/similar', { params }).then(r => r.data),

  recommendForProject: (projectId: number | string, limit = 6) =>
    api.get<{ items: SimilarProject[]; total: number }>(`/tools/history/recommend-for-project/${projectId}`, { params: { limit } }).then(r => r.data),

  getReuseMaterials: (projectId: number | string) =>
    api.get(`/tools/history/reuse-materials/${projectId}`).then(r => r.data),

  // ========== CAD 图纸检查 ==========
  checkCadDrawings: (files: File[]) => {
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    return api.post<CadCheckResult>('/tools/cad/check-drawings', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data)
  },

  // ========== GIS 分析 ==========
  gisAnalyze: (files: File[], analysisType: string = 'basic') => {
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    return api.post<GisAnalysisResult>('/tools/gis/analyze', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { analysis_type: analysisType }
    }).then(r => r.data)
  },

  gisInfo: () =>
    api.get('/tools/gis/info').then(r => r.data),
}
