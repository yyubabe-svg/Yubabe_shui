import { useState, useEffect } from 'react'
import {
  Calculator, Play, Download, History, ChevronRight, Loader2,
  AlertTriangle, CheckCircle2, Info, RefreshCw, BookOpen, Save,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import { toolsApi, type CalcTypeDef, type CalcResult, type CalcParamDef, type CalcHistoryItem } from '../../api/tools'
import MarkdownRenderer from '../../components/MarkdownRenderer'

type Mode = 'calc' | 'history'

export default function CalculationPanel() {
  const { currentProject } = useProject()
  const [mode, setMode] = useState<Mode>('calc')
  const [categories, setCategories] = useState<Array<{ category: string; items: CalcTypeDef[] }>>([])
  const [selectedCalc, setSelectedCalc] = useState<CalcTypeDef | null>(null)
  const [paramValues, setParamValues] = useState<Record<string, any>>({})
  const [calculating, setCalculating] = useState(false)
  const [result, setResult] = useState<CalcResult | null>(null)
  const [history, setHistory] = useState<CalcHistoryItem[]>([])
  const [label, setLabel] = useState('')

  useEffect(() => {
    toolsApi.listCalcTypes().then(res => {
      setCategories(res.categories)
      if (res.categories.length > 0 && res.categories[0].items.length > 0) {
        selectCalc(res.categories[0].items[0])
      }
    }).catch(() => {})
    if (currentProject) {
      toolsApi.listCalcHistory({ project_id: currentProject.id, limit: 50 }).then(res => {
        setHistory(res.items)
      }).catch(() => {})
    }
  }, [currentProject])

  const selectCalc = (calc: CalcTypeDef) => {
    setSelectedCalc(calc)
    const defaults: Record<string, any> = {}
    calc.params.forEach(p => {
      if (p.default !== undefined) defaults[p.key] = p.default
    })
    setParamValues(defaults)
    setResult(null)
    setLabel('')
  }

  const handleCalculate = async () => {
    if (!selectedCalc) return
    setCalculating(true)
    try {
      const res = await toolsApi.compute({
        calc_type: selectedCalc.id,
        params: paramValues,
        label: label || undefined,
        save: true,
      }, currentProject?.id)
      setResult(res)
      if (currentProject) {
        toolsApi.listCalcHistory({ project_id: currentProject.id, limit: 50 }).then(r => setHistory(r.items))
      }
    } catch (e: any) {
      console.error('计算失败:', e)
    } finally {
      setCalculating(false)
    }
  }

  const loadHistoryResult = async (h: CalcHistoryItem) => {
    try {
      const detail = await toolsApi.getCalcHistory(h.id)
      setResult(detail as unknown as CalcResult)
      // 选中对应的计算类型
      for (const cat of categories) {
        const found = cat.items.find(i => i.id === h.calc_type)
        if (found) {
          setSelectedCalc(found)
          setParamValues(detail.inputs || {})
          break
        }
      }
      setMode('calc')
    } catch (e) {
      console.error(e)
    }
  }

  const formatValue = (v: any, unit?: string) => {
    if (v === null || v === undefined || v === '') return '—'
    if (typeof v === 'number') {
      const s = Math.abs(v) >= 100 ? v.toFixed(2) : v.toFixed(4)
      return unit ? `${s} ${unit}` : s
    }
    if (typeof v === 'boolean') return v ? '是' : '否'
    if (typeof v === 'object') return JSON.stringify(v)
    return unit ? `${v} ${unit}` : String(v)
  }

  return (
    <div className="flex gap-4 h-full">
      {/* 左侧计算类型列表 */}
      <div className="w-64 flex-shrink-0 space-y-3">
        <div className="panel p-1 inline-flex w-full">
          <button
            onClick={() => setMode('calc')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm rounded transition-colors ${
              mode === 'calc' ? 'bg-brand-600 text-white' : 'text-neutral-600 hover:bg-neutral-100'
            }`}
          >
            <Calculator className="w-3.5 h-3.5" />计算
          </button>
          <button
            onClick={() => setMode('history')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm rounded transition-colors ${
              mode === 'history' ? 'bg-brand-600 text-white' : 'text-neutral-600 hover:bg-neutral-100'
            }`}
          >
            <History className="w-3.5 h-3.5" />历史
          </button>
        </div>

        {mode === 'calc' ? (
          <div className="space-y-3">
            {categories.map(cat => (
              <div key={cat.category} className="panel p-3">
                <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">{cat.category}</h3>
                <div className="space-y-0.5">
                  {cat.items.map(c => (
                    <button
                      key={c.id}
                      onClick={() => selectCalc(c)}
                      className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-sm transition-colors ${
                        selectedCalc?.id === c.id
                          ? 'bg-brand-50 text-brand-700 font-medium'
                          : 'text-neutral-700 hover:bg-neutral-50'
                      }`}
                    >
                      <ChevronRight className={`w-3 h-3 flex-shrink-0 ${selectedCalc?.id === c.id ? 'text-brand-500' : 'text-neutral-300'}`} />
                      <span className="truncate">{c.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="panel p-3">
            <h3 className="text-xs font-semibold text-neutral-500 mb-2">计算历史（{history.length}）</h3>
            {history.length === 0 ? (
              <p className="text-sm text-neutral-400 py-4 text-center">暂无计算记录</p>
            ) : (
              <div className="space-y-1">
                {history.map(h => (
                  <button
                    key={h.id}
                    onClick={() => loadHistoryResult(h)}
                    className="w-full text-left px-2 py-2 rounded hover:bg-neutral-50 transition-colors"
                  >
                    <p className="text-sm text-neutral-800 truncate">{h.label || h.calc_name}</p>
                    <p className="text-xs text-neutral-400 mt-0.5">
                      {h.category} · {h.created_at ? new Date(h.created_at).toLocaleString('zh-CN', {month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}) : ''}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 右侧计算区 */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {selectedCalc && mode === 'calc' && (
          <>
            {/* 计算说明 */}
            <div className="panel p-5">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-brand-50 flex items-center justify-center flex-shrink-0">
                  <Calculator className="w-5 h-5 text-brand-600" strokeWidth={1.75} />
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-base font-semibold text-neutral-900">{selectedCalc.name}</h2>
                  <p className="text-sm text-neutral-500 mt-0.5">{selectedCalc.desc}</p>
                  <p className="text-xs text-neutral-400 mt-1 flex items-center gap-1">
                    <BookOpen className="w-3 h-3" />引用规范：{selectedCalc.code_basis}
                  </p>
                </div>
              </div>
            </div>

            {/* 参数输入 */}
            <div className="panel p-5">
              <h3 className="text-sm font-semibold text-neutral-900 mb-4 flex items-center gap-2">
                输入参数
              </h3>
              <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                {selectedCalc.params.map(p => (
                  <div key={p.key}>
                    <label className="block text-sm text-neutral-700 mb-1">
                      {p.label}
                      {p.required && <span className="text-red-500 ml-1">*</span>}
                      {p.unit && <span className="text-neutral-400 text-xs ml-1">({p.unit})</span>}
                    </label>
                    {p.type === 'select' ? (
                      <select
                        value={paramValues[p.key] ?? ''}
                        onChange={e => setParamValues(v => ({ ...v, [p.key]: e.target.value }))}
                        className="input"
                      >
                        {p.options?.map(opt => (
                          <option key={String(opt.value)} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="number"
                        step="any"
                        value={paramValues[p.key] ?? ''}
                        onChange={e => setParamValues(v => ({ ...v, [p.key]: e.target.value === '' ? '' : parseFloat(e.target.value) }))}
                        className="input"
                        placeholder={`默认: ${p.default ?? ''}`}
                      />
                    )}
                    {p.hint && <p className="text-xs text-neutral-400 mt-1">{p.hint}</p>}
                  </div>
                ))}
              </div>

              <div className="mt-5 pt-4 border-t border-neutral-100 flex items-center gap-3">
                <input
                  type="text"
                  value={label}
                  onChange={e => setLabel(e.target.value)}
                  placeholder="添加标签（如：K0+500断面）便于检索，可选"
                  className="input flex-1"
                />
                <button
                  onClick={handleCalculate}
                  disabled={calculating}
                  className="btn-primary px-6 flex items-center gap-2"
                >
                  {calculating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  开始计算
                </button>
              </div>
            </div>
          </>
        )}

        {/* 计算结果 */}
        {result && (
          <>
            <div className="panel p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
                  {result.success ? (
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                  )}
                  计算结果
                </h3>
                {result.review_required && (
                  <span className="text-xs px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />需人工复核
                  </span>
                )}
              </div>

              {/* 主要结果 */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-5">
                {Object.entries(result.outputs).map(([k, v]) => {
                  const outputLabels: Record<string, { label: string; unit?: string; highlight?: boolean }> = {
                    Q_m3_s: { label: '设计流量 Q', unit: 'm³/s', highlight: true },
                    v_m_s: { label: '流速 v', unit: 'm/s' },
                    A_m2: { label: '过水面积 A', unit: 'm²' },
                    R_m: { label: '水力半径 R', unit: 'm' },
                    Q_L_s: { label: '雨水流量 Q', unit: 'L/s', highlight: true },
                    Q_m3_s_rain: { label: '雨水流量 Q', unit: 'm³/s', highlight: true },
                    q_L_s_ha: { label: '暴雨强度 q', unit: 'L/(s·ha)' },
                    Q_full_m3_s: { label: '满流能力', unit: 'm³/s' },
                    fill_ratio: { label: '设计充满度', highlight: true },
                    max_fill_allowed: { label: '允许充满度' },
                    v_design_m_s: { label: '设计流速', unit: 'm/s' },
                    capacity_ok: { label: '输水能力', highlight: true },
                    fill_ok: { label: '充满度合格', highlight: true },
                    v_ok: { label: '流速合格', highlight: true },
                    d_recommended_m: { label: '推荐管径', unit: 'm' },
                    crest_elevation_m: { label: '堤顶高程', unit: 'm', highlight: true },
                    Y_total_freeboard_m: { label: '堤顶超高 Y', unit: 'm' },
                    R_wave_runup_m: { label: '波浪爬高 R', unit: 'm' },
                    e_wind_setup_m: { label: '风壅高度 e', unit: 'm' },
                    A_safety_m: { label: '安全加高 A', unit: 'm' },
                    cut_volume_m3: { label: '挖方量', unit: 'm³' },
                    fill_volume_m3: { label: '填方量', unit: 'm³' },
                    lining_area_m2: { label: '衬砌面积', unit: 'm²' },
                    H_total_m: { label: '渠道总深', unit: 'm' },
                    n: { label: '糙率 n' },
                    P_m: { label: '湿周 χ', unit: 'm' },
                  }
                  const info = outputLabels[k] || { label: k }
                  const displayVal = typeof v === 'boolean' ? (v ? '✓ 合格' : '✗ 不合格') : formatValue(v, info.unit)
                  return (
                    <div key={k} className={`p-3 rounded-lg border ${info.highlight ? 'bg-brand-50 border-brand-200' : 'bg-neutral-50 border-neutral-100'}`}>
                      <p className="text-xs text-neutral-500 mb-1">{info.label}</p>
                      <p className={`text-lg font-semibold ${
                        typeof v === 'boolean' ? (v ? 'text-green-700' : 'text-red-600') :
                        info.highlight ? 'text-brand-700' : 'text-neutral-900'
                      }`}>
                        {displayVal}
                      </p>
                    </div>
                  )
                })}
              </div>

              {/* 警告 */}
              {result.warnings && result.warnings.length > 0 && (
                <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs font-semibold text-amber-800 mb-1.5 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" />注意事项
                  </p>
                  <ul className="text-xs text-amber-700 space-y-1 list-disc list-inside">
                    {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}

              {/* 计算过程 */}
              <details className="mb-4">
                <summary className="text-sm font-medium text-neutral-700 cursor-pointer hover:text-brand-600 flex items-center gap-1">
                  <Info className="w-4 h-4" />查看详细计算过程（{result.steps.length}步）
                </summary>
                <div className="mt-3 space-y-2">
                  {result.steps.map((s, i) => (
                    <div key={i} className="p-3 bg-neutral-50 rounded-lg text-sm">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <p className="text-neutral-700">
                            <span className="text-neutral-400 mr-2">步骤{i + 1}.</span>
                            {s.description}
                          </p>
                          <p className="text-xs text-neutral-500 mt-1 font-mono bg-white px-2 py-1 rounded">{s.formula}</p>
                        </div>
                        <p className="text-sm font-semibold text-brand-700 flex-shrink-0">
                          = {formatValue(s.result, s.unit)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </details>

              {/* 规范依据 */}
              {result.code_basis && (
                <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg">
                  <p className="text-xs text-blue-700 flex items-start gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                    <span><strong>规范依据：</strong>{result.code_basis}</span>
                  </p>
                  {result.notes && (
                    <p className="text-xs text-blue-600 mt-1.5 ml-5">{result.notes}</p>
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {!selectedCalc && mode === 'calc' && (
          <div className="panel flex items-center justify-center py-20">
            <div className="text-center">
              <Calculator className="w-12 h-12 text-neutral-300 mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-neutral-500">请从左侧选择计算类型</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
