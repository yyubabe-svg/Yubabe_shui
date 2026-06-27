import { useState, useEffect, useRef } from 'react'
import { Waves, CloudRain, FileCode, FileBarChart, Download, Upload, Play, RefreshCw, AlertCircle, CheckCircle, Info, Copy } from 'lucide-react'
import { phase3Api, RainfallResult, HydroModel, SwmmOptions } from '../../api/phase3'
import { useProject } from '../../context/ProjectContext'

type SubTab = 'rainfall' | 'swmm_inp' | 'swmm_rpt'

const CITIES = ['成都', '乐山', '绵阳', '德阳', '眉山', '自贡', '内江', '遂宁', '广元', '雅安', '重庆', '北京', '上海', '广州']

export default function HydroModelPanel() {
  const { currentProject } = useProject()
  const [subTab, setSubTab] = useState<SubTab>('rainfall')
  const [models, setModels] = useState<HydroModel[]>([])
  const [swmmOptions, setSwmmOptions] = useState<SwmmOptions | null>(null)

  const [rfCity, setRfCity] = useState('成都')
  const [rfReturn, setRfReturn] = useState(20)
  const [rfDuration, setRfDuration] = useState(120)
  const [rfTimestep, setRfTimestep] = useState(5)
  const [rfR, setRfR] = useState(0.4)
  const [rfResult, setRfResult] = useState<RainfallResult | null>(null)
  const [rfLoading, setRfLoading] = useState(false)

  const [inpResult, setInpResult] = useState<any>(null)
  const [inpLoading, setInpLoading] = useState(false)
  const [scList, setScList] = useState<any[]>([{ name: 'S1', land_use: 'residential', area_ha: 5, outlet: 'J1' }])
  const [juncList, setJuncList] = useState<any[]>([{ name: 'J1', invert_elev_m: 498, max_depth_m: 3 }])
  const [conduitList, setConduitList] = useState<any[]>([{ name: 'C1', from_node: 'J1', to_node: 'OUT1', length_m: 100, diameter_m: 0.8, material: 'concrete' }])
  const [outfallList, setOutfallList] = useState<any[]>([{ name: 'OUT1', invert_elev_m: 496, type: 'FREE' }])

  const [rptResult, setRptResult] = useState<any>(null)
  const [rptLoading, setRptLoading] = useState(false)
  const rptFileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    phase3Api.listHydroModels().then(res => setModels(res.models)).catch(() => {})
    phase3Api.getSwmmOptions().then(setSwmmOptions).catch(() => {})
  }, [])

  useEffect(() => {
    if (currentProject?.location) {
      for (const c of CITIES) {
        if (currentProject.location.includes(c)) { setRfCity(c); break }
      }
    }
  }, [currentProject])

  const handleGenerateRainfall = async () => {
    setRfLoading(true)
    try {
      const res = await phase3Api.generateRainfall({
        city: rfCity, return_period: rfReturn, duration_min: rfDuration,
        timestep_min: rfTimestep, r_factor: rfR
      })
      setRfResult(res.data)
    } catch (e) { console.error(e) }
    finally { setRfLoading(false) }
  }

  const handleGenerateInp = async () => {
    setInpLoading(true)
    try {
      const res = await phase3Api.generateSwmmInp({
        project_name: currentProject?.project_name || '未命名项目',
        subcatchments: scList, junctions: juncList, conduits: conduitList, outfalls: outfallList
      }, currentProject?.id)
      setInpResult(res.data)
    } catch (e) { console.error(e) }
    finally { setInpLoading(false) }
  }

  const handleParseRpt = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setRptLoading(true)
    try {
      const res = await phase3Api.parseSwmmRpt(file, currentProject?.id)
      setRptResult(res.data)
    } catch (e) { console.error(e) }
    finally { setRptLoading(false) }
  }

  const downloadInp = () => {
    if (!inpResult?.inp_content) return
    const blob = new Blob([inpResult.inp_content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${currentProject?.project_name || 'project'}.inp`; a.click()
    URL.revokeObjectURL(url)
  }
  const copyInp = () => { if (inpResult?.inp_content) navigator.clipboard.writeText(inpResult.inp_content) }

  const renderRainfallChart = (data: RainfallResult) => {
    const maxI = Math.max(...data.intensities_mm_h)
    const w = 600, h = 200, padL = 40, padB = 30, padT = 10, padR = 10
    const chartW = w - padL - padR, chartH = h - padT - padB
    const barW = chartW / data.intensities_mm_h.length * 0.8
    const gap = chartW / data.intensities_mm_h.length * 0.2
    return (
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-48">
        <line x1={padL} y1={padT} x2={padL} y2={h-padB} stroke="#94a3b8" strokeWidth="1"/>
        <line x1={padL} y1={h-padB} x2={w-padR} y2={h-padB} stroke="#94a3b8" strokeWidth="1"/>
        <text x={padL-5} y={padT+5} textAnchor="end" fontSize="10" fill="#64748b">0</text>
        <text x={padL-5} y={padT+chartH/2} textAnchor="end" fontSize="10" fill="#64748b">{Math.round(maxI/2)}</text>
        <text x={padL-5} y={padT+chartH} textAnchor="end" fontSize="10" fill="#64748b">{Math.round(maxI)}</text>
        <text x={padL-30} y={padT+chartH/2} textAnchor="middle" fontSize="10" fill="#64748b" transform={`rotate(-90, ${padL-30}, ${padT+chartH/2})`}>mm/h</text>
        {data.intensities_mm_h.map((v, i) => {
          const x = padL + i * (barW + gap)
          const barH = (v / maxI) * chartH
          return (
            <g key={i}>
              <rect x={x} y={h-padB-barH} width={barW} height={barH}
                fill={v === maxI ? '#ef4444' : 'rgba(59,130,246,0.7)'} rx="1"/>
              {i % Math.ceil(data.intensities_mm_h.length / 8) === 0 && (
                <text x={x+barW/2} y={h-padB+15} textAnchor="middle" fontSize="9" fill="#64748b">{data.times_min[i]}</text>
              )}
            </g>
          )
        })}
        <line x1={padL + (data.peak_time_min/data.duration_min)*chartW} y1={padT}
              x2={padL + (data.peak_time_min/data.duration_min)*chartW} y2={h-padB}
              stroke="#ef4444" strokeWidth="1" strokeDasharray="3,3"/>
      </svg>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-neutral-800 flex items-center gap-2">
          <Waves className="w-5 h-5 text-blue-600"/> 水文模型辅助
        </h2>
        <p className="text-sm text-neutral-500 mt-1">SWMM暴雨管理模型辅助：设计暴雨生成、INP输入文件生成、RPT报告解析</p>
      </div>

      <div className="flex gap-1 mb-4 border-b border-neutral-200">
        {[
          { key: 'rainfall', label: '设计暴雨', icon: CloudRain },
          { key: 'swmm_inp', label: 'SWMM建模', icon: FileCode },
          { key: 'swmm_rpt', label: '结果解析', icon: FileBarChart },
        ].map(t => (
          <button key={t.key} onClick={() => setSubTab(t.key as SubTab)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              subTab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-neutral-500 hover:text-neutral-700'
            }`}>
            <t.icon className="w-4 h-4"/>{t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto pr-2">
        {subTab === 'rainfall' && (
          <div className="space-y-4">
            <div className="panel p-4">
              <h3 className="font-medium text-neutral-800 mb-3 flex items-center gap-2">
                <CloudRain className="w-4 h-4 text-blue-600"/> 芝加哥雨型（Keifer & Chu）
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-3">
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">城市</label>
                  <select className="input" value={rfCity} onChange={e => setRfCity(e.target.value)}>
                    {CITIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">重现期(年)</label>
                  <input className="input" type="number" value={rfReturn} onChange={e => setRfReturn(+e.target.value)} min={1} max={1000}/>
                </div>
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">降雨历时(min)</label>
                  <input className="input" type="number" value={rfDuration} onChange={e => setRfDuration(+e.target.value)} min={30} max={1440}/>
                </div>
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">时间步长(min)</label>
                  <input className="input" type="number" value={rfTimestep} onChange={e => setRfTimestep(+e.target.value)} min={1} max={60}/>
                </div>
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">雨峰系数r</label>
                  <input className="input" type="number" value={rfR} onChange={e => setRfR(+e.target.value)} min={0.1} max={0.9} step={0.05}/>
                </div>
              </div>
              <button className="btn-primary" onClick={handleGenerateRainfall} disabled={rfLoading}>
                {rfLoading ? <RefreshCw className="w-4 h-4 animate-spin"/> : <Play className="w-4 h-4"/>}
                生成设计暴雨
              </button>
            </div>

            {rfResult && (
              <>
                <div className="panel p-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="text-center p-3 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-700">{rfResult.total_rainfall_mm}</div>
                      <div className="text-xs text-neutral-500">总降雨量(mm)</div>
                    </div>
                    <div className="text-center p-3 bg-cyan-50 rounded-lg">
                      <div className="text-2xl font-bold text-cyan-700">{rfResult.peak_intensity_mm_h}</div>
                      <div className="text-xs text-neutral-500">峰值雨强(mm/h)</div>
                    </div>
                    <div className="text-center p-3 bg-indigo-50 rounded-lg">
                      <div className="text-2xl font-bold text-indigo-700">{rfResult.peak_time_min}</div>
                      <div className="text-xs text-neutral-500">峰现时间(min)</div>
                    </div>
                    <div className="text-center p-3 bg-violet-50 rounded-lg">
                      <div className="text-2xl font-bold text-violet-700">{rfResult.peak_intensity_ratio}</div>
                      <div className="text-xs text-neutral-500">峰均比</div>
                    </div>
                  </div>
                  <div className="bg-white rounded-lg border border-neutral-200 p-2">
                    {renderRainfallChart(rfResult)}
                  </div>
                  <div className="mt-2 text-xs text-neutral-500 font-mono bg-neutral-50 p-2 rounded">
                    暴雨强度公式：{rfResult.formula}
                  </div>
                </div>

                <div className="panel p-4">
                  <h4 className="font-medium text-sm text-neutral-700 mb-2">降雨过程数据</h4>
                  <div className="max-h-40 overflow-y-auto text-xs font-mono bg-neutral-50 p-2 rounded">
                    <table className="w-full">
                      <thead><tr className="text-neutral-500"><th className="text-left py-0.5">时间(min)</th><th className="text-right">雨强(mm/h)</th></tr></thead>
                      <tbody>
                        {rfResult.times_min.map((t, i) => (
                          <tr key={i}><td className="py-0.5">{t}</td><td className="text-right">{rfResult.intensities_mm_h[i]}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {subTab === 'swmm_inp' && (
          <div className="space-y-4">
            <div className="panel p-4">
              <h3 className="font-medium text-neutral-800 mb-3">快速建模（生成 .inp 文件）</h3>
              <p className="text-xs text-neutral-500 mb-3">输入子汇水区、节点、管段、排放口参数，自动生成SWMM输入文件</p>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-neutral-700 block mb-1">子汇水区（{scList.length}个）</label>
                  {scList.map((sc, i) => (
                    <div key={i} className="flex gap-1 mb-1 text-xs">
                      <input className="input flex-1" placeholder="名称" value={sc.name} onChange={e => { const n=[...scList]; n[i].name=e.target.value; setScList(n); }}/>
                      <select className="input flex-1" value={sc.land_use} onChange={e => { const n=[...scList]; n[i].land_use=e.target.value; setScList(n); }}>
                        {swmmOptions?.land_use_options.map(o => <option key={o.key} value={o.key}>{o.name}</option>)}
                      </select>
                      <input className="input w-20" type="number" placeholder="面积(ha)" value={sc.area_ha} onChange={e => { const n=[...scList]; n[i].area_ha=+e.target.value; setScList(n); }}/>
                      <input className="input w-16" placeholder="出口" value={sc.outlet} onChange={e => { const n=[...scList]; n[i].outlet=e.target.value; setScList(n); }}/>
                      <button onClick={() => setScList(scList.filter((_,j)=>j!==i))} className="text-red-500 px-1 hover:bg-red-50 rounded">×</button>
                    </div>
                  ))}
                  <button onClick={() => setScList([...scList,{name:`S${scList.length+1}`,land_use:'residential',area_ha:1,outlet:'J1'}])}
                    className="text-xs text-blue-600 hover:underline">+ 添加子汇水区</button>
                </div>
                <div>
                  <label className="text-sm font-medium text-neutral-700 block mb-1">节点（{juncList.length}个）</label>
                  {juncList.map((j, i) => (
                    <div key={i} className="flex gap-1 mb-1 text-xs">
                      <input className="input flex-1" placeholder="名称" value={j.name} onChange={e => { const n=[...juncList]; n[i].name=e.target.value; setJuncList(n); }}/>
                      <input className="input w-28" type="number" placeholder="井底高程(m)" value={j.invert_elev_m} onChange={e => { const n=[...juncList]; n[i].invert_elev_m=+e.target.value; setJuncList(n); }}/>
                      <input className="input w-20" type="number" placeholder="井深(m)" value={j.max_depth_m} onChange={e => { const n=[...juncList]; n[i].max_depth_m=+e.target.value; setJuncList(n); }}/>
                      <button onClick={() => setJuncList(juncList.filter((_,x)=>x!==i))} className="text-red-500 px-1 hover:bg-red-50 rounded">×</button>
                    </div>
                  ))}
                  <button onClick={() => setJuncList([...juncList,{name:`J${juncList.length+1}`,invert_elev_m:0,max_depth_m:2.5}])}
                    className="text-xs text-blue-600 hover:underline">+ 添加节点</button>
                </div>
                <div>
                  <label className="text-sm font-medium text-neutral-700 block mb-1">管段（{conduitList.length}个）</label>
                  {conduitList.map((c, i) => (
                    <div key={i} className="flex gap-1 mb-1 text-xs flex-wrap">
                      <input className="input w-20" placeholder="名称" value={c.name} onChange={e => { const n=[...conduitList]; n[i].name=e.target.value; setConduitList(n); }}/>
                      <input className="input w-16" placeholder="起点" value={c.from_node} onChange={e => { const n=[...conduitList]; n[i].from_node=e.target.value; setConduitList(n); }}/>
                      <input className="input w-16" placeholder="终点" value={c.to_node} onChange={e => { const n=[...conduitList]; n[i].to_node=e.target.value; setConduitList(n); }}/>
                      <input className="input w-20" type="number" placeholder="长度(m)" value={c.length_m} onChange={e => { const n=[...conduitList]; n[i].length_m=+e.target.value; setConduitList(n); }}/>
                      <input className="input w-20" type="number" placeholder="管径(m)" value={c.diameter_m} onChange={e => { const n=[...conduitList]; n[i].diameter_m=+e.target.value; setConduitList(n); }}/>
                      <select className="input w-24" value={c.material} onChange={e => { const n=[...conduitList]; n[i].material=e.target.value; setConduitList(n); }}>
                        {swmmOptions?.conduit_material_options.map(o => <option key={o.key} value={o.key}>{o.name}</option>)}
                      </select>
                      <button onClick={() => setConduitList(conduitList.filter((_,x)=>x!==i))} className="text-red-500 px-1 hover:bg-red-50 rounded">×</button>
                    </div>
                  ))}
                  <button onClick={() => setConduitList([...conduitList,{name:`C${conduitList.length+1}`,from_node:'J1',to_node:'OUT1',length_m:50,diameter_m:0.8,material:'concrete'}])}
                    className="text-xs text-blue-600 hover:underline">+ 添加管段</button>
                </div>
                <div>
                  <label className="text-sm font-medium text-neutral-700 block mb-1">排放口（{outfallList.length}个）</label>
                  {outfallList.map((o, i) => (
                    <div key={i} className="flex gap-1 mb-1 text-xs">
                      <input className="input flex-1" placeholder="名称" value={o.name} onChange={e => { const n=[...outfallList]; n[i].name=e.target.value; setOutfallList(n); }}/>
                      <input className="input w-24" type="number" placeholder="高程(m)" value={o.invert_elev_m} onChange={e => { const n=[...outfallList]; n[i].invert_elev_m=+e.target.value; setOutfallList(n); }}/>
                      <select className="input w-24" value={o.type} onChange={e => { const n=[...outfallList]; n[i].type=e.target.value; setOutfallList(n); }}>
                        <option value="FREE">自由出流</option><option value="NORMAL">正常水深</option><option value="FIXED">固定水位</option>
                      </select>
                      <button onClick={() => setOutfallList(outfallList.filter((_,x)=>x!==i))} className="text-red-500 px-1 hover:bg-red-50 rounded">×</button>
                    </div>
                  ))}
                  <button onClick={() => setOutfallList([...outfallList,{name:`OUT${outfallList.length+1}`,invert_elev_m:0,type:'FREE'}])}
                    className="text-xs text-blue-600 hover:underline">+ 添加排放口</button>
                </div>
              </div>
              <button className="btn-primary mt-4" onClick={handleGenerateInp} disabled={inpLoading}>
                {inpLoading ? <RefreshCw className="w-4 h-4 animate-spin"/> : <FileCode className="w-4 h-4"/>}
                生成 INP 文件
              </button>
            </div>

            {inpResult && (
              <div className="panel p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-neutral-800 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-600"/> INP 文件已生成
                  </h3>
                  <div className="flex gap-2">
                    <button className="btn-secondary text-sm py-1 px-2" onClick={copyInp}><Copy className="w-3.5 h-3.5"/>复制</button>
                    <button className="btn-primary text-sm py-1 px-2" onClick={downloadInp}><Download className="w-3.5 h-3.5"/>下载</button>
                  </div>
                </div>
                <div className="text-xs text-neutral-600 mb-2">
                  共{inpResult.element_counts.subcatchments}子汇水区、{inpResult.element_counts.junctions}节点、{inpResult.element_counts.conduits}管段、{inpResult.element_counts.outfalls}排放口
                </div>
                {inpResult.warnings?.length > 0 && (
                  <div className="mb-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
                    <AlertCircle className="w-3.5 h-3.5 inline mr-1"/>{inpResult.warnings.join('；')}
                  </div>
                )}
                <pre className="max-h-80 overflow-y-auto text-xs font-mono bg-neutral-900 text-green-300 p-3 rounded leading-relaxed">
                  {inpResult.inp_content}
                </pre>
              </div>
            )}
          </div>
        )}

        {subTab === 'swmm_rpt' && (
          <div className="space-y-4">
            <div className="panel p-6 border-2 border-dashed text-center">
              <Upload className="w-10 h-10 text-neutral-400 mx-auto mb-2"/>
              <p className="text-sm text-neutral-600 mb-3">上传SWMM模拟输出报告(.rpt)，自动解析关键结果</p>
              <input ref={rptFileRef} type="file" accept=".rpt,.txt" onChange={handleParseRpt} className="hidden"/>
              <button className="btn-primary" onClick={() => rptFileRef.current?.click()} disabled={rptLoading}>
                {rptLoading ? <RefreshCw className="w-4 h-4 animate-spin"/> : <Upload className="w-4 h-4"/>}选择 RPT 文件
              </button>
            </div>

            {rptResult && (
              <>
                <div className="panel p-4">
                  <h3 className="font-medium text-neutral-800 mb-3 flex items-center gap-2"><FileBarChart className="w-4 h-4 text-blue-600"/> 模拟结果</h3>
                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="p-3 bg-blue-50 rounded-lg text-center">
                      <div className="text-xl font-bold text-blue-700">{rptResult.summary.subcatchment_count}</div>
                      <div className="text-xs text-neutral-500">子汇水区</div>
                    </div>
                    <div className={`p-3 rounded-lg text-center ${rptResult.summary.flooding_node_count > 0 ? 'bg-red-50' : 'bg-green-50'}`}>
                      <div className={`text-xl font-bold ${rptResult.summary.flooding_node_count > 0 ? 'text-red-700' : 'text-green-700'}`}>{rptResult.summary.flooding_node_count}</div>
                      <div className="text-xs text-neutral-500">积水节点</div>
                    </div>
                    <div className={`p-3 rounded-lg text-center ${rptResult.summary.surcharged_conduit_count > 0 ? 'bg-amber-50' : 'bg-green-50'}`}>
                      <div className={`text-xl font-bold ${rptResult.summary.surcharged_conduit_count > 0 ? 'text-amber-700' : 'text-green-700'}`}>{rptResult.summary.surcharged_conduit_count}</div>
                      <div className="text-xs text-neutral-500">超载管段</div>
                    </div>
                  </div>
                  {rptResult.warnings?.length > 0 && (
                    <div className="p-2 bg-amber-50 border border-amber-200 rounded">
                      {rptResult.warnings.map((w: string, i: number) => (
                        <div key={i} className="text-xs text-amber-800 flex gap-1.5"><AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5"/>{w}</div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
            <div className="text-xs text-neutral-400 flex items-start gap-1.5 p-3 bg-neutral-50 rounded-lg">
              <Info className="w-4 h-4 flex-shrink-0 mt-0.5"/>
              <div>本功能仅解析SWMM报告，不运行模型。需在SWMM软件中运行后导出.rpt文件上传。</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
