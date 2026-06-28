import api from './client'

// ==================== 水文模型辅助 ====================

export interface HydroModel {
  id: string
  name: string
  description: string
  features: string[]
  version: string
}

export interface RainfallResult {
  city: string
  return_period: number
  duration_min: number
  timestep_min: number
  r: number
  total_rainfall_mm: number
  avg_intensity_mm_h: number
  peak_intensity_mm_h: number
  peak_intensity_ratio: number
  peak_time_min: number
  times_min: number[]
  intensities_mm_h: number[]
  formula: string
}

export interface SwmmOptions {
  land_use_options: { key: string; name: string; pct_imperv: number }[]
  conduit_material_options: { key: string; name: string; n: number }[]
  supported_cities: string[]
}

export interface SubcatchmentDefaults {
  land_use_name: string
  n_imperv: number
  n_perv: number
  s_imperv: number
  s_perv: number
  pct_zero: number
  pct_imperv: number
  recommended_width_m: number
}

export interface SwmmInpResult {
  inp_content: string
  project_name: string
  element_counts: { subcatchments: number; junctions: number; conduits: number; outfalls: number }
  warnings: string[]
  notes: string[]
  land_use_options: any[]
  conduit_material_options: any[]
  supported_cities: string[]
}

export interface SwmmRptResult {
  summary: {
    subcatchment_count: number
    flooding_node_count: number
    surcharged_conduit_count: number
    max_flooding_nodes: any[]
    max_surcharge_conduits: any[]
  }
  continuity: {
    runoff_error_pct?: number
    routing_error_pct?: number
  }
  subcatchment_results: any[]
  node_flooding: any[]
  conduit_surcharge: any[]
  warnings: string[]
  errors: string[]
}

// ==================== 参数化设计 ====================

export interface SectionType {
  id: string
  name: string
  description: string
}

export interface RevetmentType {
  id: string
  name: string
  thickness_m: number
  slope_ratio_min: number
  slope_ratio_max: number
  slope_ratio_recommend: number
  cost_per_m3: number
  foundation_depth_m: number
  suitable_flow_ms: number
  applicable: string[]
  notes: string
}

export interface DesignRecommendations {
  crest_width: number
  freeboard: number
  anti_slide_safety_factor: number
  anti_overturn_safety_factor: number
}

export interface SectionDesignResult {
  success: boolean
  section_name: string
  section_type: string
  parameters: Record<string, any>
  geometry: {
    outline_points: { x: number; y: number }[]
    water_level_points: { x: number; y: number }[]
    bed_points: { x: number; y: number }[]
    section_width_m: number
    section_height_m: number
  }
  quantities: Record<string, number>
  costs: Record<string, number>
  stability: {
    anti_slide_Kc: number
    weight_kN_per_m: number
    water_pressure_kN_per_m: number
    friction_coeff: number
    pass: boolean
  }
  compliance: string[]
  warnings: string[]
  notes: string[]
}

export interface SchemeCompareResult {
  schemes: {
    name: string
    revetment_name: string
    m_slope: number
    stability_Kc: number
    stability_pass: boolean
    total_cost_per_m: number
    fill_volume_per_m: number
    section_width: number
    warnings: string[]
    compliance: string[]
    composite_score: number
  }[]
  recommended: string
  recommended_reason: string
  comparison_dimensions: string[]
}

// ==================== 轻量数字孪生 ====================

export interface Discipline {
  id: string
  name: string
  weight: number
}

export interface DashboardData {
  project_id: number
  kpis: {
    basic: Record<string, any>
    scale: { items: { label: string; value: any; unit: string }[] }
    investment: { items: { label: string; value: any; unit: string }[] }
    engineering: { items: { label: string; value: any; unit: string }[]; note: string }
    risks: { level: string; message: string }[]
  }
  progress: {
    overall_progress: number
    design_stage: string
    disciplines: {
      id: string
      name: string
      weight: number
      progress: number
      status: 'completed' | 'in_progress' | 'pending'
      deliverables: { name: string; status: string }[]
    }[]
    critical_path: string[]
    next_milestone: { name: string; progress_target: number; next_stage?: string }
  }
  timeline: {
    created_at: string
    days_elapsed: number
    estimated_total_days: number
    estimated_remaining_days: number
    time_progress_pct: number
    schedule_status: string
  }
  generated_at: string
}

// ==================== API ====================

export const phase3Api = {
  // ---------- 水文模型 ----------
  listHydroModels: () =>
    api.get<{ models: HydroModel[]; supported_cities: string[] }>('/phase3/hydro/models').then(r => r.data),

  generateRainfall: (params: {
    city: string
    return_period?: number
    duration_min?: number
    timestep_min?: number
    r_factor?: number
  }) =>
    api.post<{ success: boolean; data: RainfallResult; warnings: string[]; notes: string[] }>(
      '/phase3/hydro/rainfall/generate', params
    ).then(r => r.data),

  getSwmmOptions: () =>
    api.get<SwmmOptions>('/phase3/hydro/swmm/options').then(r => r.data),

  getSubcatchmentParams: (land_use: string, area_ha: number) =>
    api.get<SubcatchmentDefaults>('/phase3/hydro/subcatchment/params', {
      params: { land_use, area_ha }
    }).then(r => r.data),

  generateSwmmInp: (params: {
    project_name: string
    subcatchments: any[]
    junctions: any[]
    conduits: any[]
    outfalls: any[]
    rain_gauge?: any
  }, projectId?: number) =>
    api.post<{ success: boolean; data: SwmmInpResult; warnings: string[]; notes: string[] }>(
      '/phase3/hydro/swmm/generate-inp', params,
      { params: projectId ? { project_id: projectId } : {} }
    ).then(r => r.data),

  parseSwmmRpt: (file: File, projectId?: number) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<{ success: boolean; filename: string; data: SwmmRptResult; warnings: string[]; errors: string[] }>(
      '/phase3/hydro/swmm/parse-rpt', form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        params: projectId ? { project_id: projectId } : {}
      }
    ).then(r => r.data)
  },

  // ---------- 参数化设计 ----------
  getParametricOptions: (buildingLevel: number = 4) =>
    api.get<{
      section_types: SectionType[]
      revetment_types: RevetmentType[]
      recommendations: DesignRecommendations
    }>('/phase3/parametric/options', { params: { building_level: buildingLevel } }).then(r => r.data),

  designSection: (params: {
    section_type?: string
    design_water_level: number
    bed_elevation: number
    bed_width: number
    m_slope?: number
    revetment_type: string
    freeboard: number
    crest_width: number
    berm_width?: number
    foundation_depth?: number
    wall_thickness?: number
    wall_bottom_thickness?: number
    wall_height?: number
    main_channel_width?: number
    main_channel_depth?: number
    floodplain_width?: number
    m_slope_main?: number
    m_slope_flood?: number
    floodplain_revetment?: string
  }, projectId?: number) =>
    api.post<SectionDesignResult>('/phase3/parametric/design-section', params,
      { params: projectId ? { project_id: projectId } : {} }
    ).then(r => r.data),

  compareSchemes: (schemes: any[]) =>
    api.post<SchemeCompareResult>('/phase3/parametric/compare', { schemes }).then(r => r.data),

  // ---------- 数字孪生 ----------
  getDashboard: (projectId: number) =>
    api.get<DashboardData>(`/phase3/digital-twin/dashboard/${projectId}`).then(r => r.data),

  getDisciplines: () =>
    api.get<{ disciplines: Discipline[] }>('/phase3/digital-twin/disciplines').then(r => r.data),
}
