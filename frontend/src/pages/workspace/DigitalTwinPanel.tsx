import { useState, useEffect } from 'react'
import { Activity, TrendingUp, AlertTriangle, Clock, CheckCircle2, Circle, PlayCircle, BarChart3, Layers, MapPin, Calendar, DollarSign, Ruler } from 'lucide-react'
import { phase3Api, DashboardData } from '../../api/phase3'
import { useProject } from '../../context/ProjectContext'

// 简单的class合并工具
function cn(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ')
}

export default function DigitalTwinPanel() {
  const { currentProject } = useProject()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (currentProject?.id) {
      setLoading(true)
      phase3Api.getDashboard(currentProject.id)
        .then(setData)
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [currentProject?.id])

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-neutral-400">
      <div className="animate-pulse">加载看板数据中...</div>
    </div>
  }

  if (!data) {
    return <div className="flex items-center justify-center h-64 text-neutral-400">
      请先选择一个项目
    </div>
  }

  const { kpis, progress, timeline } = data
  const overallPct = progress.overall_progress

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-neutral-800 flex items-center gap-2">
          <Activity className="w-5 h-5 text-violet-600"/> 项目数字看板
        </h2>
        <p className="text-sm text-neutral-500 mt-1">项目KPI、设计进度、风险指标一屏掌握</p>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 space-y-4">
        {/* 顶部KPI卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-lg">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-blue-600 font-medium">设计总进度</div>
                <div className="text-2xl font-bold text-blue-900 mt-1">{overallPct}%</div>
              </div>
              <TrendingUp className="w-6 h-6 text-blue-400"/>
            </div>
            <div className="mt-2 h-1.5 bg-blue-200 rounded-full overflow-hidden">
              <div className="h-full bg-blue-600 rounded-full transition-all" style={{width: `${overallPct}%`}}/>
            </div>
          </div>

          <div className="p-3 bg-gradient-to-br from-emerald-50 to-emerald-100 border border-emerald-200 rounded-lg">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-emerald-600 font-medium">总投资</div>
                <div className="text-2xl font-bold text-emerald-900 mt-1">
                  {kpis.investment.items[0]?.value ? (kpis.investment.items[0].value / 10000).toFixed(2) : '-'}
                  <span className="text-sm font-normal ml-0.5">亿</span>
                </div>
              </div>
              <DollarSign className="w-6 h-6 text-emerald-400"/>
            </div>
            <div className="text-xs text-emerald-700 mt-1">{kpis.investment.items[0]?.unit || '万元'}</div>
          </div>

          <div className="p-3 bg-gradient-to-br from-amber-50 to-amber-100 border border-amber-200 rounded-lg">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-amber-600 font-medium">已进行</div>
                <div className="text-2xl font-bold text-amber-900 mt-1">{timeline.days_elapsed}<span className="text-sm font-normal ml-0.5">天</span></div>
              </div>
              <Calendar className="w-6 h-6 text-amber-400"/>
            </div>
            <div className="text-xs text-amber-700 mt-1">预计剩余 {timeline.estimated_remaining_days} 天</div>
          </div>

          <div className="p-3 bg-gradient-to-br from-violet-50 to-violet-100 border border-violet-200 rounded-lg">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-violet-600 font-medium">风险/预警</div>
                <div className="text-2xl font-bold text-violet-900 mt-1">{kpis.risks.length}</div>
              </div>
              <AlertTriangle className="w-6 h-6 text-violet-400"/>
            </div>
            <div className="text-xs text-violet-700 mt-1">需关注事项</div>
          </div>
        </div>

        {/* 项目基本信息 */}
        <div className="p-4 bg-white border border-neutral-200 rounded-lg">
          <h3 className="font-medium text-neutral-800 mb-3 flex items-center gap-2">
            <Layers className="w-4 h-4 text-neutral-500"/> 项目概况
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div><span className="text-neutral-500">项目类型：</span>{kpis.basic.project_type}</div>
            <div><span className="text-neutral-500">设计阶段：</span>{kpis.basic.design_stage}</div>
            <div><span className="text-neutral-500">工程等别：</span>{kpis.basic.project_grade}等</div>
            <div><span className="text-neutral-500">建筑物级别：</span>{kpis.basic.building_level}级</div>
          </div>

          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            {kpis.scale.items.map((s, i) => (
              <div key={i} className="text-center p-2 bg-neutral-50 rounded-lg">
                <div className="flex items-center justify-center gap-1 text-xs text-neutral-500 mb-0.5">
                  <Ruler className="w-3 h-3"/>{s.label}
                </div>
                <div className="text-lg font-bold text-neutral-800">{s.value} <span className="text-xs font-normal text-neutral-500">{s.unit}</span></div>
              </div>
            ))}
          </div>
        </div>

        {/* 设计进度 */}
        <div className="p-4 bg-white border border-neutral-200 rounded-lg">
          <h3 className="font-medium text-neutral-800 mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-neutral-500"/> 各专业设计进度
          </h3>
          <div className="space-y-2.5">
            {progress.disciplines.map(d => {
              const color = d.status === 'completed' ? 'bg-emerald-500' : d.status === 'in_progress' ? 'bg-blue-500' : 'bg-neutral-300'
              return (
                <div key={d.id} className="group">
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="flex items-center gap-1.5 text-neutral-700">
                      {d.status === 'completed' ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500"/> :
                       d.status === 'in_progress' ? <PlayCircle className="w-3.5 h-3.5 text-blue-500"/> :
                       <Circle className="w-3.5 h-3.5 text-neutral-400"/>}
                      {d.name}
                    </span>
                    <span className={cn(
                      'text-xs font-medium',
                      d.status === 'completed' ? 'text-emerald-600' :
                      d.status === 'in_progress' ? 'text-blue-600' : 'text-neutral-400'
                    )}>{d.progress}%</span>
                  </div>
                  <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                    <div className={cn('h-full rounded-full transition-all', color)} style={{width: `${d.progress}%`}}/>
                  </div>
                  {/* 交付物列表 */}
                  <div className="hidden group-hover:flex flex-wrap gap-1.5 mt-1">
                    {d.deliverables.map((dl, j) => (
                      <span key={j} className={cn(
                        'text-[10px] px-1.5 py-0.5 rounded',
                        dl.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                        dl.status === 'in_progress' ? 'bg-blue-100 text-blue-700' : 'bg-neutral-100 text-neutral-500'
                      )}>{dl.name}</span>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="mt-4 p-3 bg-blue-50 rounded-lg flex items-start gap-2">
            <Clock className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5"/>
            <div>
              <div className="text-sm font-medium text-blue-800">下一里程碑：{progress.next_milestone.name}</div>
              <div className="text-xs text-blue-600 mt-0.5">目标进度 {progress.next_milestone.progress_target}%
                {progress.next_milestone.next_stage && `，完成后进入${progress.next_milestone.next_stage}阶段`}
              </div>
            </div>
          </div>
        </div>

        {/* 投资构成 */}
        {kpis.investment.items.length > 1 && (
          <div className="p-4 bg-white border border-neutral-200 rounded-lg">
            <h3 className="font-medium text-neutral-800 mb-3 flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-neutral-500"/> 投资构成（估算）
            </h3>
            <div className="space-y-2">
              {kpis.investment.items.slice(1).map((item, i) => {
                const total = kpis.investment.items[0]?.value || 1
                const pct = (item.value / total) * 100
                const colors = ['bg-blue-500', 'bg-emerald-500', 'bg-amber-500', 'bg-violet-500', 'bg-rose-500', 'bg-cyan-500', 'bg-indigo-500']
                return (
                  <div key={i}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="text-neutral-600">{item.label}</span>
                      <span className="text-neutral-800 font-medium">{item.value.toLocaleString()} {item.unit} ({pct.toFixed(1)}%)</span>
                    </div>
                    <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                      <div className={cn('h-full rounded-full', colors[i % colors.length])} style={{width: `${pct}%`}}/>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* 工程量估算 */}
        {kpis.engineering.items.length > 0 && (
          <div className="p-4 bg-white border border-neutral-200 rounded-lg">
            <h3 className="font-medium text-neutral-800 mb-3 flex items-center gap-2">
              <Ruler className="w-4 h-4 text-neutral-500"/> 主要工程量（经验估算）
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {kpis.engineering.items.map((e, i) => (
                <div key={i} className="p-2 bg-neutral-50 rounded-lg text-center">
                  <div className="text-lg font-bold text-neutral-800">{e.value} <span className="text-xs font-normal">{e.unit}</span></div>
                  <div className="text-xs text-neutral-500">{e.label}</div>
                </div>
              ))}
            </div>
            <div className="mt-2 text-[11px] text-neutral-400 italic">{kpis.engineering.note}</div>
          </div>
        )}

        {/* 风险提示 */}
        {kpis.risks.length > 0 && (
          <div className="p-4 bg-white border border-neutral-200 rounded-lg">
            <h3 className="font-medium text-neutral-800 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500"/> 风险与注意事项
            </h3>
            <div className="space-y-2">
              {kpis.risks.map((r, i) => {
                const levelStyle = {
                  info: 'bg-blue-50 border-blue-200 text-blue-800',
                  warning: 'bg-amber-50 border-amber-200 text-amber-800',
                  error: 'bg-red-50 border-red-200 text-red-800',
                }[r.level] || 'bg-neutral-50 border-neutral-200'
                const Icon = r.level === 'warning' ? AlertTriangle : r.level === 'error' ? AlertTriangle : BarChart3
                return (
                  <div key={i} className={cn('p-2 rounded border text-sm flex gap-2', levelStyle)}>
                    <Icon className="w-4 h-4 flex-shrink-0 mt-0.5"/>
                    {r.message}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* 进度时间线 */}
        <div className="p-4 bg-white border border-neutral-200 rounded-lg">
          <h3 className="font-medium text-neutral-800 mb-3 flex items-center gap-2">
            <Clock className="w-4 h-4 text-neutral-500"/> 时间进度
          </h3>
          <div className="relative pt-1">
            <div className="flex items-center justify-between mb-1 text-xs text-neutral-500">
              <span>{timeline.created_at}</span>
              <span>预计{timeline.estimated_total_days}天</span>
            </div>
            <div className="h-3 bg-neutral-100 rounded-full overflow-hidden relative">
              <div className="h-full bg-gradient-to-r from-blue-500 to-violet-500 rounded-full" style={{width: `${Math.min(100, timeline.time_progress_pct)}%`}}/>
              {/* 当前进度标记 */}
              <div className="absolute top-0 h-full w-0.5 bg-red-500" style={{left: `${overallPct}%`}}/>
            </div>
            <div className="flex justify-between mt-1 text-xs">
              <span className="text-blue-600">时间进度 {timeline.time_progress_pct}%</span>
              <span className={timeline.schedule_status === 'on_track' ? 'text-emerald-600' : 'text-red-600'}>
                {timeline.schedule_status === 'on_track' ? '✓ 进度正常' : '⚠ 进度滞后'}
              </span>
              <span className="text-violet-600">设计进度 {overallPct}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
