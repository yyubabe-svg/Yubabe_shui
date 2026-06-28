import api from './client'

// ==================== 第四阶段：成果导出 ====================

export interface ExportFormat {
  id: string
  name: string
  ext: string
  desc: string
}

export interface SectionDesignInput {
  section_type: string
  design_water_level: number
  bed_elevation: number
  bed_width: number
  m_slope?: number
  revetment_type: string
  freeboard: number
  crest_width: number
  foundation_depth?: number
  // 矩形断面
  wall_thickness?: number
  wall_bottom_thickness?: number
  wall_height?: number
  // 复式断面
  main_channel_width?: number
  main_channel_depth?: number
  floodplain_width?: number
  m_slope_main?: number
  m_slope_flood?: number
  floodplain_revetment?: string
}

export interface ExportRequest {
  sections: SectionDesignInput[]
  channel_lengths?: number[]
  include_report?: boolean
  include_boq?: boolean
}

export interface RainfallInput {
  city: string
  return_period: number
  duration_min: number
  timestep_min: number
}

export const phase4Api = {
  // ---------- 导出选项 ----------
  getExportOptions: () =>
    api.get<{
      export_formats: ExportFormat[]
      section_types: { id: string; name: string; description: string }[]
    }>('/phase4/export/options').then(r => r.data),

  // ---------- 文件下载辅助 ----------
  _downloadBlob: async (blobPromise: Promise<Blob>, defaultName: string) => {
    const blob = await blobPromise
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = defaultName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },

  // ---------- 导出工程量清单 Excel ----------
  exportBoq: (data: ExportRequest, projectId?: number) => {
    return api.post('/phase4/export/boq', data, {
      params: projectId ? { project_id: projectId } : {},
      responseType: 'blob',
    }).then(r => {
      const disposition = (r.headers as any)['content-disposition'] || ''
      let filename = `工程量清单_${new Date().toISOString().slice(0,10)}.xlsx`
      const match = disposition.match(/filename\*?=UTF-8''([^;]+)/)
      if (match) {
        try { filename = decodeURIComponent(match[1]) } catch { /* use default */ }
      }
      const url = window.URL.createObjectURL(new Blob([r.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      return { success: true, filename }
    })
  },

  // ---------- 导出设计说明书 Word ----------
  exportReport: (data: ExportRequest & { rainfall?: RainfallInput }, projectId?: number) => {
    const body: any = { sections: data.sections, channel_lengths: data.channel_lengths }
    return api.post('/phase4/export/report', body, {
      params: projectId ? { project_id: projectId } : {},
      responseType: 'blob',
      // rainfall作为query/body暂不传入，简化接口
    }).then(r => {
      const disposition = (r.headers as any)['content-disposition'] || ''
      let filename = `设计说明书_${new Date().toISOString().slice(0,10)}.docx`
      const match = disposition.match(/filename\*?=UTF-8''([^;]+)/)
      if (match) {
        try { filename = decodeURIComponent(match[1]) } catch { /* use default */ }
      }
      const url = window.URL.createObjectURL(new Blob([r.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      return { success: true, filename }
    })
  },
}
