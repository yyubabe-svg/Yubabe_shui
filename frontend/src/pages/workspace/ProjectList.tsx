import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FolderPlus, Search, Plus, MoreVertical, Calendar, FileText,
  ChevronRight, Loader2, X, Building2,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import { projectsApi, type ProjectCreate } from '../../api/projects'

const PROJECT_TYPES = [
  { value: 'river_training', label: '河道治理' },
  { value: 'reservoir_reinforcement', label: '水库除险加固' },
  { value: 'drainage_pump', label: '排涝泵站' },
  { value: 'mountain_flood', label: '山洪沟治理' },
  { value: 'irrigation_upgrade', label: '灌区改造' },
  { value: 'flood_evaluation', label: '防洪评价' },
  { value: 'soil_conservation', label: '水土保持' },
  { value: 'rural_water', label: '农村供水' },
  { value: 'urban_waterlogging', label: '城市内涝' },
  { value: 'dike_engineering', label: '堤防工程' },
  { value: 'sluice_culvert', label: '涵闸工程' },
  { value: 'water_resource', label: '水资源论证' },
  { value: 'small_farmland_water', label: '小型农田水利' },
]

const DESIGN_STAGES = [
  { value: 'proposal', label: '项目建议书' },
  { value: 'feasibility', label: '可行性研究' },
  { value: 'preliminary', label: '初步设计' },
  { value: 'implementation', label: '实施方案' },
  { value: 'construction', label: '施工图' },
]

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  active:   { label: '进行中', cls: 'badge-brand' },
  completed:{ label: '已完成', cls: 'badge-success' },
  archived: { label: '已归档', cls: 'badge-neutral' },
}

export default function ProjectList() {
  const navigate = useNavigate()
  const { projects, loading, error, createProject, refreshProjects } = useProject()
  const [showModal, setShowModal] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [creating, setCreating] = useState(false)
  const [typeOptions, setTypeOptions] = useState<{ project_types: { value: string; label: string }[]; design_stages: { value: string; label: string }[] }>({
    project_types: PROJECT_TYPES,
    design_stages: DESIGN_STAGES,
  })
  const [form, setForm] = useState<ProjectCreate>({
    project_name: '',
    project_type: 'river_training',
    design_stage: 'preliminary',
    client: '',
    designer: '',
    location: '',
  })

  useEffect(() => {
    projectsApi.getTypeOptions().then(setTypeOptions).catch(() => {})
  }, [])

  const filtered = projects.filter(p => {
    if (keyword) {
      const kw = keyword.toLowerCase()
      if (!p.name.toLowerCase().includes(kw) && !(p.code || '').toLowerCase().includes(kw)) return false
    }
    if (typeFilter && p.project_type !== typeFilter) return false
    return true
  })

  const handleCreate = async () => {
    if (!form.project_name.trim()) return
    setCreating(true)
    try {
      const p = await createProject(form)
      setShowModal(false)
      setForm({
        project_name: '',
        project_type: 'river_training',
        design_stage: 'preliminary',
        client: '',
        designer: '',
        location: '',
      })
      navigate(`/workspace/${p.id}`)
    } catch {
      // error handled by context
    } finally {
      setCreating(false)
    }
  }

  const formatDate = (ts: string) => {
    try { return new Date(ts).toLocaleDateString('zh-CN') } catch { return ts }
  }

  return (
    <div className="page-container">
      <div className="page-header flex items-start justify-between">
        <div>
          <h1>项目工作台</h1>
          <p>管理项目资料、章节生成、表格填报、AI 初审与专家回复</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary">
          <Plus className="w-4 h-4" strokeWidth={2} />
          新建项目
        </button>
      </div>

      {/* 搜索筛选 */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <div className="relative flex-1 min-w-[240px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text"
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            placeholder="搜索项目名称或编号…"
            className="input pl-9"
          />
        </div>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="input max-w-[160px]">
          <option value="">全部类型</option>
          {typeOptions.project_types.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        {(keyword || typeFilter) && (
          <button onClick={() => { setKeyword(''); setTypeFilter('') }} className="btn-ghost text-sm">
            <X className="w-4 h-4" /> 清除筛选
          </button>
        )}
      </div>

      {error && (
        <div className="text-sm text-danger bg-red-50 border border-red-100 px-4 py-2.5 rounded mb-5">
          {error}
          <button onClick={refreshProjects} className="ml-3 underline">重试</button>
        </div>
      )}

      {/* 项目卡片列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-brand-600 animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="border border-neutral-200 bg-white">
          <div className="empty-state">
            <FolderPlus className="empty-state-icon" strokeWidth={1.5} />
            <p className="empty-state-text">
              {projects.length === 0 ? '还没有项目，点击右上角「新建项目」开始' : '没有匹配的项目'}
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(p => {
            const sc = STATUS_MAP[p.status] || STATUS_MAP.active
            return (
              <div
                key={p.id}
                onClick={() => navigate(`/workspace/${p.id}`)}
                className="panel p-5 cursor-pointer hover:border-brand-300 transition-colors group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-neutral-900 truncate group-hover:text-brand-700">
                      {p.name}
                    </h3>
                    {p.code && <p className="text-xs text-neutral-500 mt-0.5 font-mono">{p.code}</p>}
                  </div>
                  <span className={`${sc.cls} text-xs flex-shrink-0 ml-2`}>{sc.label}</span>
                </div>

                <div className="space-y-1.5 mb-4">
                  {p.project_type_name && (
                    <div className="flex items-center gap-2 text-xs text-neutral-500">
                      <Building2 className="w-3.5 h-3.5" /> {p.project_type_name}
                    </div>
                  )}
                  {p.stage && (
                    <div className="flex items-center gap-2 text-xs text-neutral-500">
                      {p.stage}
                    </div>
                  )}
                  {p.client && (
                    <div className="flex items-center gap-2 text-xs text-neutral-500 truncate">
                      业主：{p.client}
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-xs text-neutral-500">
                    <FileText className="w-3.5 h-3.5" />
                    {p.doc_count ?? 0} 份资料
                  </div>
                  <div className="flex items-center gap-2 text-xs text-neutral-500">
                    <Calendar className="w-3.5 h-3.5" />
                    更新于 {formatDate(p.updated_at)}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-neutral-100">
                  <span className="text-xs text-brand-600 group-hover:text-brand-700 font-medium flex items-center gap-1">
                    进入工作台 <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                  <button
                    onClick={e => { e.stopPropagation() }}
                    className="text-neutral-400 hover:text-neutral-600 p-1"
                  >
                    <MoreVertical className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 新建项目弹窗 */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setShowModal(false)}>
          <div className="bg-white w-full max-w-lg rounded-lg shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-200">
              <h2 className="text-base font-semibold text-neutral-900">新建项目</h2>
              <button onClick={() => setShowModal(false)} className="text-neutral-400 hover:text-neutral-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="label">项目名称 <span className="text-danger">*</span></label>
                <input
                  type="text"
                  value={form.project_name}
                  onChange={e => setForm({ ...form, project_name: e.target.value })}
                  placeholder="如：XX河道综合治理工程"
                  className="input"
                  autoFocus
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">项目类型 <span className="text-danger">*</span></label>
                  <select
                    value={form.project_type}
                    onChange={e => setForm({ ...form, project_type: e.target.value })}
                    className="input"
                  >
                    {typeOptions.project_types.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">设计阶段</label>
                  <select
                    value={form.design_stage}
                    onChange={e => setForm({ ...form, design_stage: e.target.value })}
                    className="input"
                  >
                    {typeOptions.design_stages.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">业主单位</label>
                  <input
                    type="text"
                    value={form.client || ''}
                    onChange={e => setForm({ ...form, client: e.target.value })}
                    placeholder="可选"
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">设计负责人</label>
                  <input
                    type="text"
                    value={form.designer || ''}
                    onChange={e => setForm({ ...form, designer: e.target.value })}
                    placeholder="可选"
                    className="input"
                  />
                </div>
              </div>
              <div>
                <label className="label">项目地点</label>
                <input
                  type="text"
                  value={form.location || ''}
                  onChange={e => setForm({ ...form, location: e.target.value })}
                  placeholder="可选"
                  className="input"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 px-5 py-4 border-t border-neutral-200 bg-neutral-50 rounded-b-lg">
              <button onClick={() => setShowModal(false)} className="btn-secondary">取消</button>
              <button onClick={handleCreate} disabled={!form.project_name.trim() || creating} className="btn-primary px-5">
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" strokeWidth={2} />}
                创建项目
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
