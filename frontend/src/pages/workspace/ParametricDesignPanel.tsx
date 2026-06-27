import { useState, useEffect, useMemo } from 'react'
import { Ruler, Shapes, GitCompare, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react'
import { phase3Api, SectionDesignResult, RevetmentType, DesignRecommendations } from '../../api/phase3'
import { useProject } from '../../context/ProjectContext'

export default function ParametricDesignPanel() {
  const { currentProject } = useProject()
  const [revetmentTypes, setRevetmentTypes] = useState<RevetmentType[]>([])
  const [recommendations, setRecommendations] = useState<DesignRecommendations | null>(null)

  const [dwl, setDwl] = useState(100)
  const [bedEl, setBedEl] = useState(95)
  const [bedW, setBedW] = useState(10)
  const [mSlope, setMSlope] = useState(2.0)
  const [revetment, setRevetment] = useState('stone_mortar')
  const [freeboard, setFreeboard] = useState(1.0)
  const [crestW, setCrestW] = useState(5.0)
  const [foundationD, setFoundationD] = useState(0.6)

  const [designResult, setDesignResult] = useState<SectionDesignResult | null>(null)
  const [designing, setDesigning] = useState(false)

  const [compareSchemes, setCompareSchemes] = useState([
    { name: '方案A：浆砌石', revetment_type: 'stone_mortar', m_slope: 1.75, bed_width: 10, crest_width: 5.0, freeboard: 1.0, design_water_level: 100, bed_elevation: 95 },
    { name: '方案B：混凝土', revetment_type: 'concrete', m_slope: 2.0, bed_width: 10, crest_width: 5.0, freeboard: 1.0, design_water_level: 100, bed_elevation: 95 },
    { name: '方案C：生态护岸', revetment_type: 'ecological', m_slope: 3.0, bed_width: 10, crest_width: 5.0, freeboard: 1.0, design_water_level: 100, bed_elevation: 95 },
  ])
  const [compareResult, setCompareResult] = useState<any>(null)
  const [comparing, setComparing] = useState(false)
  const [mode, setMode] = useState<'design' | 'compare'>('design')

  useEffect(() => {
    const level = currentProject?.main_building_level || 4
    phase3Api.getParametricOptions(level).then(res => {
      setRevetmentTypes(res.revetment_types)
      setRecommendations(res.recommendations)
      setFreeboard(res.recommendations.freeboard)
      setCrestW(res.recommendations.crest_width)
    }).catch(() => {})
  }, [currentProject])

  useEffect(() => {
    // 同步对比方案的水位/高程
    setCompareSchemes(prev => prev.map(s => ({ ...s, design_water_level: dwl, bed_elevation: bedEl, bed_width: bedW, freeboard, crest_width: crestW })))
  }, [dwl, bedEl, bedW, freeboard, crestW])

  const selectedRevetment = useMemo(() =>
    revetmentTypes.find(r => r.id === revetment), [revetmentTypes, revetment])

  const handleDesign = async () => {
    setDesigning(true)
    try {
      const res = await phase3Api.designSection({
        design_water_level: dwl, bed_elevation: bedEl, bed_width: bedW,
        m_slope: mSlope, revetment_type: revetment, freeboard, crest_width: crestW,
        foundation_depth: foundationD
      }, currentProject?.id)
      setDesignResult(res)
    } catch (e) { console.error(e) }
    finally { setDesigning(false) }
  }

  const handleCompare = async () => {
    setComparing(true)
    try {
      const res = await phase3Api.compareSchemes(compareSchemes)
      setCompareResult(res)
    } catch (e) { console.error(e) }
    finally { setComparing(false) }
  }

  const renderSectionSVG = (r: SectionDesignResult) => {
    const pts = r.geometry.outline_points
    const xs = pts.map(p => p.x), ys = pts.map(p => p.y)
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const minY = Math.min(...ys), maxY = Math.max(...ys, r.parameters.crest_elevation)
    const w = 600, h = 280, pad = 40
    const sx = (x: number) => pad + (x - minX) / (maxX - minX) * (w - 2*pad)
    const sy = (y: number) => h - pad - (y - minY) / (maxY - minY) * (h - 2*pad)
    const pathD = pts.map((p, i) => `${i===0?'M':'L'}${sx(p.x)},${sy(p.y)}`).join(' ')
    const wl = r.parameters.design_water_level
    const wlPts = r.geometry.water_level_points
    const bedPts = r.geometry.bed_points
    return (
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-64 bg-gradient-to-b from-sky-50 to-blue-50 rounded border">
        <path d={`${pathD} L${sx(maxX)},${sy(minY)} L${sx(minX)},${sy(minY)} Z`} fill="#d4a574" stroke="#8B6914" strokeWidth="1.5"/>
        <path d={pathD} fill="none" stroke="#6b4423" strokeWidth="2.5"/>
        <polygon
          points={`${sx(wlPts[0].x)},${sy(wl)} ${sx(wlPts[1].x)},${sy(wl)} ${sx(wlPts[1].x)},${sy(bedPts[0].y)} ${sx(bedPts[0].x)},${sy(bedPts[0].y)} ${sx(bedPts[1].x)},${sy(bedPts[1].y)} ${sx(wlPts[0].x)},${sy(wl)}`}
          fill="rgba(59,130,246,0.35)" stroke="#3b82f6" strokeWidth="0.5" strokeDasharray="4,2"/>
        <line x1={sx(wlPts[0].x)-20} y1={sy(wl)} x2={sx(wlPts[1].x)+20} y2={sy(wl)} stroke="#2563eb" strokeWidth="1" strokeDasharray="5,3"/>
        <text x={sx(wlPts[1].x)+25} y={sy(wl)+3} fontSize="10" fill="#2563eb">设计水位 {wl}m</text>
        <line x1={sx(pts[1].x)-10} y1={sy(r.parameters.crest_elevation)} x2={sx(pts[2].x)+10} y2={sy(r.parameters.crest_elevation)} stroke="#b91c1c" strokeWidth="1.5"/>
        <text x={sx(pts[2].x)+15} y={sy(r.parameters.crest_elevation)+3} fontSize="10" fill="#b91c1c">堤顶 {r.parameters.crest_elevation}m</text>
        <line x1={sx(bedPts[0].x)} y1={sy(bedPts[0].y)} x2={sx(bedPts[1].x)} y2={sy(bedPts[1].y)} stroke="#6b4423" strokeWidth="2"/>
        <text x={sx((bedPts[0].x+bedPts[1].x)/2)} y={sy(bedPts[0].y)+15} fontSize="10" fill="#6b4423" textAnchor="middle">河底 {r.parameters.bed_width}m</text>
        <text x={sx((pts[0].x+pts[1].x)/2)-10} y={sy((pts[0].y+pts[1].y)/2)} fontSize="9" fill="#6b4423">1:{mSlope}</text>
      </svg>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-neutral-800 flex items-center gap-2">
          <Ruler className="w-5 h-5 text-emerald-600"/> 参数化设计
        </h2>
        <p className="text-sm text-neutral-500 mt-1">堤防/渠道典型断面参数化设计、工程量自动计算、多方案比选</p>
      </div>

      <div className="flex gap-1 mb-4 border-b border-neutral-200">
        {[
          { key: 'design', label: '断面设计', icon: Shapes },
          { key: 'compare', label: '方案对比', icon: GitCompare },
        ].map(t => (
          <button key={t.key} onClick={() => setMode(t.key as any)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              mode === t.key ? 'border-emerald-600 text-emerald-600' : 'border-transparent text-neutral-500 hover:text-neutral-700'
            }`}>
            <t.icon className="w-4 h-4"/>{t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto pr-2">
        {mode === 'design' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="panel p-4 lg:col-span-1">
              <h3 className="font-medium text-neutral-800 mb-3">设计参数</h3>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-neutral-500 block mb-1">设计水位(m)</label>
                    <input className="input" type="number" step="0.1" value={dwl} onChange={e => setDwl(+e.target.value)}/>
                  </div>
                  <div>
                    <label className="text-xs text-neutral-500 block mb-1">河底高程(m)</label>
                    <input className="input" type="number" step="0.1" value={bedEl} onChange={e => setBedEl(+e.target.value)}/>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-neutral-500 block mb-1">河底宽度(m)</label>
                    <input className="input" type="number" step="0.5" value={bedW} onChange={e => setBedW(+e.target.value)}/>
                  </div>
                  <div>
                    <label className="text-xs text-neutral-500 block mb-1">边坡系数 m</label>
                    <input className="input" type="number" step="0.25" value={mSlope} onChange={e => setMSlope(+e.target.value)}/>
                  </div>
                </div>
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">护岸类型</label>
                  <select className="input" value={revetment} onChange={e => setRevetment(e.target.value)}>
                    {revetmentTypes.map(r => <option key={r.id} value={r.id}>{r.name} (m推荐{r.slope_ratio_recommend})</option>)}
                  </select>
                </div>
                {selectedRevetment && (
                  <div className="text-xs p-2 bg-emerald-50 text-emerald-800 rounded">
                    <div>推荐边坡: 1:{selectedRevetment.slope_ratio_min}~1:{selectedRevetment.slope_ratio_max} (建议1:{selectedRevetment.slope_ratio_recommend})</div>
                    <div>护岸厚度: {selectedRevetment.thickness_m}m | 允许流速: {selectedRevetment.suitable_flow_ms}m/s</div>
                    <div className="mt-1 text-emerald-600">{selectedRevetment.notes}</div>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-neutral-500 block mb-1">堤顶超高(m)</label>
                    <input className="input" type="number" step="0.1" value={freeboard} onChange={e => setFreeboard(+e.target.value)}/>
                  </div>
                  <div>
                    <label className="text-xs text-neutral-500 block mb-1">堤顶宽度(m)</label>
                    <input className="input" type="number" step="0.5" value={crestW} onChange={e => setCrestW(+e.target.value)}/>
                  </div>
                </div>
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">基础埋深(m)</label>
                  <input className="input" type="number" step="0.1" value={foundationD} onChange={e => setFoundationD(+e.target.value)}/>
                </div>
                {recommendations && (
                  <div className="text-xs text-neutral-500 p-2 bg-neutral-50 rounded">
                    {currentProject?.main_building_level}级建筑物推荐：堤顶宽≥{recommendations.crest_width}m，超高≥{recommendations.freeboard}m，抗滑≥{recommendations.anti_slide_safety_factor}
                  </div>
                )}
                <button className="btn-primary w-full" onClick={handleDesign} disabled={designing}>
                  {designing ? <RefreshCw className="w-4 h-4 animate-spin"/> : <Shapes className="w-4 h-4"/>}
                  开始断面设计
                </button>
              </div>
            </div>

            <div className="lg:col-span-2 space-y-4">
              {designResult ? (
                <>
                  <div className="panel p-4">
                    <h3 className="font-medium text-neutral-800 mb-2">{designResult.section_name}</h3>
                    {renderSectionSVG(designResult)}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="panel p-4">
                      <h4 className="text-sm font-medium text-neutral-700 mb-2">工程量（每延米）</h4>
                      <table className="w-full text-xs">
                        <tbody>
                          {Object.entries(designResult.quantities).map(([k, v]) => {
                            const labels: Record<string, string> = {
                              revetment_volume_m3_per_m: '护岸砌体(m³)', fill_volume_m3_per_m: '堤身填筑(m³)',
                              foundation_volume_m3_per_m: '基础(m³)', excavation_m3_per_m: '土方开挖(m³)',
                              concrete_or_stone_m3_per_m: '砼/砌体合计(m³)', wetted_perimeter_m: '湿周(m)',
                              flow_area_m2: '过水面积(m²)', hydraulic_radius_m: '水力半径(m)',
                            }
                            return <tr key={k} className="border-b border-neutral-100">
                              <td className="py-1 text-neutral-600">{labels[k] || k}</td>
                              <td className="py-1 text-right font-medium">{typeof v === 'number' ? v.toFixed(2) : v}</td>
                            </tr>
                          })}
                        </tbody>
                      </table>
                    </div>
                    <div className="panel p-4">
                      <h4 className="text-sm font-medium text-neutral-700 mb-2">投资估算（每延米）</h4>
                      <table className="w-full text-xs">
                        <tbody>
                          {Object.entries(designResult.costs).map(([k, v]) => {
                            const labels: Record<string, string> = {
                              revetment_cost_yuan_per_m: '护岸工程(元)', fill_cost_yuan_per_m: '土方填筑(元)',
                              foundation_cost_yuan_per_m: '基础工程(元)', total_cost_yuan_per_m: '合计(元/m)',
                              total_cost_yuan_per_km: '每公里造价(万元/km)',
                            }
                            return <tr key={k} className="border-b border-neutral-100">
                              <td className="py-1 text-neutral-600">{labels[k] || k}</td>
                              <td className="py-1 text-right font-medium">
                                {k.includes('per_km') ? (v/10000).toFixed(1) + '万' : typeof v === 'number' ? v.toFixed(0) : v}
                              </td>
                            </tr>
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <div className="panel p-4">
                    <h4 className="text-sm font-medium text-neutral-700 mb-2">稳定验算 & 规范符合性</h4>
                    <div className={`p-2 rounded mb-2 flex items-center gap-2 ${designResult.stability.pass ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                      {designResult.stability.pass ? <CheckCircle className="w-4 h-4"/> : <AlertCircle className="w-4 h-4"/>}
                      抗滑稳定安全系数 Kc = <b>{designResult.stability.anti_slide_Kc}</b>（允许值 {recommendations?.anti_slide_safety_factor || 1.25}）
                      {designResult.stability.pass ? '，满足规范要求' : '，不满足规范要求！'}
                    </div>
                    {designResult.compliance.map((c, i) => (
                      <div key={i} className="text-xs text-green-700 flex gap-1.5 py-0.5">
                        <CheckCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5"/>✓ {c}
                      </div>
                    ))}
                    {designResult.warnings.map((w, i) => (
                      <div key={i} className="text-xs text-amber-700 flex gap-1.5 py-0.5">
                        <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5"/>⚠ {w}
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="panel p-8 text-center text-neutral-400">
                  <Shapes className="w-12 h-12 mx-auto mb-2 opacity-40"/>
                  <p>请设置参数后点击"开始断面设计"</p>
                </div>
              )}
            </div>
          </div>
        )}

        {mode === 'compare' && (
          <div className="space-y-4">
            <div className="panel p-4">
              <h3 className="font-medium text-neutral-800 mb-3">多方案对比</h3>
              <p className="text-xs text-neutral-500 mb-3">综合评分：造价40%+稳定性30%+占地30%</p>
              {compareSchemes.map((s, i) => (
                <div key={i} className="mb-3 p-3 border border-neutral-200 rounded-lg">
                  <div className="text-sm font-medium text-neutral-700 mb-2">{s.name}</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                    <div>
                      <label className="text-neutral-500 block mb-0.5">护岸类型</label>
                      <select className="input" value={s.revetment_type} onChange={e => {
                        const n = [...compareSchemes]; n[i].revetment_type = e.target.value; setCompareSchemes(n)
                      }}>
                        {revetmentTypes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-neutral-500 block mb-0.5">边坡系数 m</label>
                      <input className="input" type="number" step="0.25" value={s.m_slope} onChange={e => {
                        const n = [...compareSchemes]; n[i].m_slope = +e.target.value; setCompareSchemes(n)
                      }}/>
                    </div>
                  </div>
                </div>
              ))}
              <button className="btn-primary" onClick={handleCompare} disabled={comparing}>
                {comparing ? <RefreshCw className="w-4 h-4 animate-spin"/> : <GitCompare className="w-4 h-4"/>}
                开始方案对比
              </button>
            </div>
            {compareResult && (
              <div className="panel p-4">
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded mb-4">
                  <div className="text-sm font-medium text-emerald-800">推荐方案：<b>{compareResult.recommended}</b></div>
                  <div className="text-xs text-emerald-700 mt-1">{compareResult.recommended_reason}</div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-neutral-50 text-xs text-neutral-500">
                        <th className="text-left p-2">方案</th><th className="text-right p-2">护岸</th>
                        <th className="text-right p-2">边坡</th><th className="text-right p-2">Kc</th>
                        <th className="text-right p-2">造价(元/m)</th><th className="text-right p-2">占地宽(m)</th>
                        <th className="text-right p-2">综合评分</th>
                      </tr>
                    </thead>
                    <tbody>
                      {compareResult.schemes.map((s: any, i: number) => (
                        <tr key={i} className={`border-t ${s.name === compareResult.recommended ? 'bg-emerald-50' : ''}`}>
                          <td className="p-2 font-medium">{s.name}
                            {s.name === compareResult.recommended && <span className="ml-1 text-xs bg-emerald-600 text-white px-1.5 py-0.5 rounded">推荐</span>}
                          </td>
                          <td className="p-2 text-right text-xs">{s.revetment_name}</td>
                          <td className="p-2 text-right">1:{s.m_slope}</td>
                          <td className="p-2 text-right"><span className={s.stability_pass ? 'text-green-600' : 'text-red-600'}>{s.stability_Kc.toFixed(2)}</span></td>
                          <td className="p-2 text-right">{s.total_cost_per_m.toFixed(0)}</td>
                          <td className="p-2 text-right">{s.section_width.toFixed(1)}</td>
                          <td className="p-2 text-right font-bold text-emerald-700">{s.composite_score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
