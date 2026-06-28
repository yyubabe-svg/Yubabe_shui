import { useState, useEffect } from 'react'
import { FileSpreadsheet, FileText, Download, CheckCircle, AlertCircle, Package, BookOpen, Layers, Plus, Trash2, ChevronRight, Loader2 } from 'lucide-react'
import { phase4Api, ExportFormat, SectionDesignInput } from '../../api/phase4'
import { phase3Api, SectionDesignResult } from '../../api/phase3'
import { useProject } from '../../context/ProjectContext'

interface SectionRow extends SectionDesignInput {
  id: string
  length_m: number
  name: string
  result?: SectionDesignResult
}

const SECTION_TYPE_MAP: Record<string, { name: string; icon: string }> = {
  trapezoidal: { name: '梯形断面', icon: '⬜' },
  rectangular: { name: '矩形(挡墙)', icon: '▭' },
  compound: { name: '复式断面', icon: '▬' },
}

export default function ExportPanel() {
  const { currentProject } = useProject()
  const [formats, setFormats] = useState<ExportFormat[]>([])
  const [sectionTypes, setSectionTypes] = useState<{ id: string; name: string; description: string }[]>([])

  // 多断面列表
  const [sections, setSections] = useState<SectionRow[]>([
    {
      id: 'sec1',
      name: '堤段1（典型断面）',
      length_m: 1000,
      section_type: 'trapezoidal',
      design_water_level: 100,
      bed_elevation: 95,
      bed_width: 10,
      m_slope: 2.0,
      revetment_type: 'stone_mortar',
      freeboard: 1.0,
      crest_width: 5.0,
      foundation_depth: 0.6,
    }
  ])

  const [previewResults, setPreviewResults] = useState<SectionDesignResult[]>([])
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState<'boq' | 'report' | null>(null)
  const [exportMsg, setExportMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    phase4Api.getExportOptions().then(res => {
      setFormats(res.export_formats)
      setSectionTypes(res.section_types)
    }).catch(() => {})
  }, [])

  // 汇总统计
  const totals = previewResults.reduce((acc, r) => {
    const idx = previewResults.indexOf(r)
    const len = sections[idx]?.length_m || 1000
    acc.fill += (r.quantities.fill_volume_m3_per_m || 0) * len
    acc.stone += (r.quantities.concrete_or_stone_m3_per_m || 0) * len
    acc.exc += (r.quantities.excavation_m3_per_m || 0) * len
    acc.cost += (r.costs.total_cost_yuan_per_m || 0) * len
    return acc
  }, { fill: 0, stone: 0, exc: 0, cost: 0 })
  const totalLen = sections.reduce((s, r) => s + r.length_m, 0)

  const addSection = () => {
    const newId = `sec${sections.length + 1}`
    setSections([...sections, {
      id: newId,
      name: `堤段${sections.length + 1}`,
      length_m: 800,
      section_type: 'trapezoidal',
      design_water_level: sections[0].design_water_level,
      bed_elevation: sections[0].bed_elevation,
      bed_width: 10,
      m_slope: 2.0,
      revetment_type: 'stone_mortar',
      freeboard: 1.0,
      crest_width: 5.0,
      foundation_depth: 0.6,
    }])
  }

  const removeSection = (id: string) => {
    if (sections.length <= 1) return
    setSections(sections.filter(s => s.id !== id))
    setPreviewResults([])
  }

  const updateSection = (id: string, field: keyof SectionRow, value: any) => {
    setSections(sections.map(s => s.id === id ? { ...s, [field]: value } : s))
  }

  const handlePreview = async () => {
    setLoading(true)
    try {
      const results: SectionDesignResult[] = []
      for (const sec of sections) {
        const res = await phase3Api.designSection({
          section_type: sec.section_type,
          design_water_level: sec.design_water_level,
          bed_elevation: sec.bed_elevation,
          bed_width: sec.bed_width,
          m_slope: sec.m_slope,
          revetment_type: sec.revetment_type,
          freeboard: sec.freeboard,
          crest_width: sec.crest_width,
          foundation_depth: sec.foundation_depth,
        }, currentProject?.id)
        results.push(res)
      }
      setPreviewResults(results)
      setExportMsg({ type: 'success', text: `已完成${results.length}个断面的设计计算预览` })
    } catch (e: any) {
      setExportMsg({ type: 'error', text: '预览失败：' + (e?.message || '未知错误') })
    } finally {
      setLoading(false)
    }
  }

  const handleExportBoq = async () => {
    if (previewResults.length === 0) {
      await handlePreview()
    }
    setExporting('boq')
    setExportMsg(null)
    try {
      const req = {
        sections: sections.map(s => ({
          section_type: s.section_type,
          design_water_level: s.design_water_level,
          bed_elevation: s.bed_elevation,
          bed_width: s.bed_width,
          m_slope: s.m_slope,
          revetment_type: s.revetment_type,
          freeboard: s.freeboard,
          crest_width: s.crest_width,
          foundation_depth: s.foundation_depth,
          wall_thickness: s.wall_thickness,
          wall_bottom_thickness: s.wall_bottom_thickness,
          wall_height: s.wall_height,
          main_channel_width: s.main_channel_width,
          main_channel_depth: s.main_channel_depth,
          floodplain_width: s.floodplain_width,
          m_slope_main: s.m_slope_main,
          m_slope_flood: s.m_slope_flood,
          floodplain_revetment: s.floodplain_revetment,
        })),
        channel_lengths: sections.map(s => s.length_m),
      }
      const res = await phase4Api.exportBoq(req, currentProject?.id)
      setExportMsg({ type: 'success', text: `工程量清单已导出：${res.filename}` })
    } catch (e: any) {
      setExportMsg({ type: 'error', text: '导出失败：' + (e?.message || '未知错误') })
    } finally {
      setExporting(null)
    }
  }

  const handleExportReport = async () => {
    if (previewResults.length === 0) {
      await handlePreview()
    }
    setExporting('report')
    setExportMsg(null)
    try {
      const req = {
        sections: sections.map(s => ({
          section_type: s.section_type,
          design_water_level: s.design_water_level,
          bed_elevation: s.bed_elevation,
          bed_width: s.bed_width,
          m_slope: s.m_slope,
          revetment_type: s.revetment_type,
          freeboard: s.freeboard,
          crest_width: s.crest_width,
          foundation_depth: s.foundation_depth,
        })),
        channel_lengths: sections.map(s => s.length_m),
      }
      const res = await phase4Api.exportReport(req, currentProject?.id)
      setExportMsg({ type: 'success', text: `设计说明书已导出：${res.filename}` })
    } catch (e: any) {
      setExportMsg({ type: 'error', text: '导出失败：' + (e?.message || '未知错误') })
    } finally {
      setExporting(null)
    }
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 头部 */}
      <div className="px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-emerald-50 to-teal-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-sm">
              <Package className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">智能成果输出</h2>
              <p className="text-xs text-slate-500">一键生成工程量清单Excel、设计说明书Word</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePreview}
              disabled={loading}
              className="px-4 py-2 text-sm bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 flex items-center gap-1.5 disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin"/> : <ChevronRight className="w-4 h-4"/>}
              {loading ? '计算中...' : '预览工程量'}
            </button>
            <button
              onClick={handleExportBoq}
              disabled={exporting !== null}
              className="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 flex items-center gap-1.5 shadow-sm disabled:opacity-50"
            >
              {exporting === 'boq' ? <Loader2 className="w-4 h-4 animate-spin"/> : <FileSpreadsheet className="w-4 h-4"/>}
              导出工程量清单
            </button>
            <button
              onClick={handleExportReport}
              disabled={exporting !== null}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-1.5 shadow-sm disabled:opacity-50"
            >
              {exporting === 'report' ? <Loader2 className="w-4 h-4 animate-spin"/> : <FileText className="w-4 h-4"/>}
              导出设计说明书
            </button>
          </div>
        </div>
      </div>

      {/* 消息提示 */}
      {exportMsg && (
        <div className={`mx-6 mt-3 px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${
          exportMsg.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {exportMsg.type === 'success' ? <CheckCircle className="w-4 h-4"/> : <AlertCircle className="w-4 h-4"/>}
          {exportMsg.text}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {/* 导出格式说明 */}
        <div className="grid grid-cols-2 gap-3">
          {formats.map(f => (
            <div key={f.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 mb-1">
                {f.ext === '.xlsx' ? <FileSpreadsheet className="w-5 h-5 text-emerald-600"/> : <BookOpen className="w-5 h-5 text-blue-600"/>}
                <span className="font-medium text-slate-800 text-sm">{f.name}</span>
                <span className="text-xs text-slate-400">{f.ext}</span>
              </div>
              <p className="text-xs text-slate-600 ml-7">{f.desc}</p>
            </div>
          ))}
        </div>

        {/* 分段断面配置 */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <Layers className="w-4 h-4 text-slate-600"/>
              分段断面配置（共{sections.length}段，总长{totalLen}m）
            </h3>
            <button
              onClick={addSection}
              className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md flex items-center gap-1"
            >
              <Plus className="w-3 h-3"/> 添加堤段
            </button>
          </div>

          {sections.map((sec, idx) => (
            <div key={sec.id} className="border border-slate-200 rounded-lg bg-white overflow-hidden">
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg">{SECTION_TYPE_MAP[sec.section_type]?.icon || '▫'}</span>
                  <input
                    type="text"
                    value={sec.name}
                    onChange={e => updateSection(sec.id, 'name', e.target.value)}
                    className="text-sm font-medium bg-transparent border-none outline-none text-slate-800 w-48"
                  />
                  <span className="text-xs px-2 py-0.5 bg-white rounded border border-slate-200 text-slate-600">
                    {SECTION_TYPE_MAP[sec.section_type]?.name || sec.section_type}
                  </span>
                </div>
                <button
                  onClick={() => removeSection(sec.id)}
                  disabled={sections.length <= 1}
                  className="p-1 text-slate-400 hover:text-red-500 disabled:opacity-30"
                >
                  <Trash2 className="w-4 h-4"/>
                </button>
              </div>

              <div className="p-4 grid grid-cols-4 gap-3">
                <Field label="段长(m)">
                  <input type="number" value={sec.length_m} onChange={e => updateSection(sec.id, 'length_m', +e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                </Field>
                <Field label="断面形式">
                  <select value={sec.section_type} onChange={e => updateSection(sec.id, 'section_type', e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-slate-200 rounded bg-white">
                    {sectionTypes.map(st => <option key={st.id} value={st.id}>{st.name}</option>)}
                  </select>
                </Field>
                <Field label="设计水位(m)">
                  <input type="number" step="0.1" value={sec.design_water_level} onChange={e => updateSection(sec.id, 'design_water_level', +e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                </Field>
                <Field label="河底高程(m)">
                  <input type="number" step="0.1" value={sec.bed_elevation} onChange={e => updateSection(sec.id, 'bed_elevation', +e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                </Field>

                {sec.section_type !== 'rectangular' && (
                  <Field label={sec.section_type === 'compound' ? '主槽底宽(m)' : '底宽(m)'}>
                    <input type="number" step="0.1" value={sec.bed_width} onChange={e => updateSection(sec.id, 'bed_width', +e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                  </Field>
                )}
                {sec.section_type === 'trapezoidal' && (
                  <Field label="边坡系数m">
                    <input type="number" step="0.1" value={sec.m_slope} onChange={e => updateSection(sec.id, 'm_slope', +e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                  </Field>
                )}
                <Field label="超高(m)">
                  <input type="number" step="0.1" value={sec.freeboard} onChange={e => updateSection(sec.id, 'freeboard', +e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                </Field>
                <Field label="堤顶宽(m)">
                  <input type="number" step="0.1" value={sec.crest_width} onChange={e => updateSection(sec.id, 'crest_width', +e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                </Field>
                <Field label="护岸类型">
                  <select value={sec.revetment_type} onChange={e => updateSection(sec.id, 'revetment_type', e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-slate-200 rounded bg-white">
                    <option value="stone_mortar">浆砌石</option>
                    <option value="concrete">混凝土</option>
                    <option value="stone_dry">干砌石</option>
                    <option value="ecological">生态护岸</option>
                    <option value="grass">草皮护坡</option>
                  </select>
                </Field>

                {/* 矩形断面参数 */}
                {sec.section_type === 'rectangular' && (
                  <>
                    <Field label="挡墙顶宽(m)">
                      <input type="number" step="0.1" value={sec.wall_thickness || 0.6} onChange={e => updateSection(sec.id, 'wall_thickness', +e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                    </Field>
                    <Field label="挡墙底宽(m)">
                      <input type="number" step="0.1" value={sec.wall_bottom_thickness || 1.8} onChange={e => updateSection(sec.id, 'wall_bottom_thickness', +e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                    </Field>
                  </>
                )}

                {/* 复式断面参数 */}
                {sec.section_type === 'compound' && (
                  <>
                    <Field label="主槽深度(m)">
                      <input type="number" step="0.1" value={sec.main_channel_depth || 3.5} onChange={e => updateSection(sec.id, 'main_channel_depth', +e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                    </Field>
                    <Field label="滩地宽(m/侧)">
                      <input type="number" step="1" value={sec.floodplain_width || 20} onChange={e => updateSection(sec.id, 'floodplain_width', +e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                    </Field>
                    <Field label="主槽边坡m1">
                      <input type="number" step="0.1" value={sec.m_slope_main || 2.0} onChange={e => updateSection(sec.id, 'm_slope_main', +e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                    </Field>
                    <Field label="滩地边坡m2">
                      <input type="number" step="0.1" value={sec.m_slope_flood || 2.5} onChange={e => updateSection(sec.id, 'm_slope_flood', +e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-slate-200 rounded"/>
                    </Field>
                  </>
                )}
              </div>

              {/* 该段预览结果 */}
              {previewResults[idx] && (
                <div className="mx-4 mb-4 p-3 bg-emerald-50 rounded border border-emerald-200">
                  <div className="grid grid-cols-5 gap-3 text-xs">
                    <Stat label="填筑(m³/m)" value={previewResults[idx].quantities.fill_volume_m3_per_m?.toFixed(2) || '-'} color="text-amber-700"/>
                    <Stat label="护岸(m³/m)" value={previewResults[idx].quantities.revetment_volume_m3_per_m?.toFixed(2) || '-'} color="text-slate-700"/>
                    <Stat label="开挖(m³/m)" value={previewResults[idx].quantities.excavation_m3_per_m?.toFixed(2) || '-'} color="text-orange-700"/>
                    <Stat label="造价(元/m)" value={previewResults[idx].costs.total_cost_yuan_per_m?.toFixed(0) || '-'} color="text-red-600 font-semibold"/>
                    <Stat label="抗滑Kc" value={previewResults[idx].stability.anti_slide_Kc?.toFixed(2) || '-'} color={previewResults[idx].stability.pass ? 'text-green-600' : 'text-red-600'}/>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 工程汇总 */}
        {previewResults.length > 0 && (
          <div className="border border-emerald-200 rounded-lg bg-gradient-to-br from-emerald-50 to-teal-50 p-5">
            <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-600"/>
              工程量汇总（{totalLen}m 堤防）
            </h3>
            <div className="grid grid-cols-5 gap-4">
              <SummaryCard label="土方填筑" value={`${(totals.fill/10000).toFixed(1)}万m³`} sub={`${totals.fill.toFixed(0)} m³`} color="amber"/>
              <SummaryCard label="砌石/混凝土" value={`${(totals.stone/10000).toFixed(2)}万m³`} sub={`${totals.stone.toFixed(0)} m³`} color="slate"/>
              <SummaryCard label="基础开挖" value={`${(totals.exc/10000).toFixed(1)}万m³`} sub={`${totals.exc.toFixed(0)} m³`} color="orange"/>
              <SummaryCard label="估算投资" value={`${(totals.cost/10000).toFixed(1)}万元`} sub={`${totals.cost.toFixed(0)} 元`} color="red"/>
              <SummaryCard label="单位投资" value={`${(totals.cost/totalLen*1000).toFixed(0)} 元/km`} sub={`${(totals.cost/totalLen).toFixed(0)} 元/m`} color="blue"/>
            </div>
          </div>
        )}

        {/* 说明书章节预览 */}
        <div className="border border-slate-200 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-blue-600"/>
            设计说明书包含章节
          </h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {[
              '1. 综合说明', '2. 水文', '3. 工程地质', '4. 工程布置及建筑物',
              '5. 施工组织设计', '6. 工程投资估算', '7. 结论与建议',
              '附：主要工程量清单 / 主要材料用量汇总表'
            ].map(ch => (
              <div key={ch} className="flex items-center gap-2 px-3 py-2 bg-slate-50 rounded text-slate-700">
                <CheckCircle className="w-3.5 h-3.5 text-blue-500"/>
                {ch}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-slate-500 mb-1">{label}</label>
      {children}
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div>
      <div className="text-slate-500 mb-0.5">{label}</div>
      <div className={`${color} font-medium`}>{value}</div>
    </div>
  )
}

function SummaryCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  const colorMap: Record<string, string> = {
    amber: 'bg-amber-100 text-amber-800',
    slate: 'bg-slate-200 text-slate-800',
    orange: 'bg-orange-100 text-orange-800',
    red: 'bg-red-100 text-red-700',
    blue: 'bg-blue-100 text-blue-800',
  }
  return (
    <div className="bg-white rounded-lg p-3 border border-white shadow-sm">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${color === 'red' ? 'text-red-600' : color === 'blue' ? 'text-blue-600' : 'text-slate-800'}`}>{value}</div>
      <div className="text-xs text-slate-400 mt-0.5">{sub}</div>
    </div>
  )
}
