import { useEffect, useState } from 'react'
import {
  FolderOpen, FileText, Table, SearchCheck, Reply,
  Plus, Clock, Building2, Calendar, User, FileSpreadsheet,
  ChevronRight, Loader2, Calculator, FolderSearch, Map, Box,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import { workspaceApi, type WorkspaceTask, type ProjectDocument } from '../../api/workspace'
import TaskProgressCard from '../../components/common/TaskProgressCard'

interface Props {
  onTabChange: (tab: 'overview' | 'documents' | 'section' | 'form' | 'review' | 'expert' | 'search' | 'calc' | 'history' | 'gis' | 'cad') => void
}

const QUICK_ACTIONS = [
  { key: 'documents', label: '上传资料', icon: FolderOpen, desc: '上传设计报告、基础资料等' },
  { key: 'section', label: '生成章节', icon: FileText, desc: '选择章节大纲，AI 流式生成' },
  { key: 'form', label: '填报表格', icon: FileSpreadsheet, desc: '自动提取字段，一键填充模板' },
  { key: 'review', label: 'AI 初审', icon: SearchCheck, desc: '规范引用、数据一致性检查' },
  { key: 'expert', label: '专家回复', icon: Reply, desc: '切分意见，逐条生成回复' },
  { key: 'calc', label: '水利计算', icon: Calculator, desc: '明渠、流量、管径、堤顶高程' },
  { key: 'history', label: '历史复用', icon: FolderSearch, desc: '智能推荐相似历史项目' },
  { key: 'gis', label: 'GIS 出图', icon: Map, desc: '空间分析、一键出图' },
  { key: 'cad', label: 'CAD 检查', icon: Box, desc: '图签识别、目录生成' },
] as const

export default function ProjectOverview({ onTabChange }: Props) {
  const { currentProject } = useProject()
  const [tasks, setTasks] = useState<WorkspaceTask[]>([])
  const [docs, setDocs] = useState<ProjectDocument[]>([])
  const [stats, setStats] = useState({ documents: 0, form_tasks: 0, form_completed: 0, section_tasks: 0, review_tasks: 0, reply_tasks: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!currentProject) return
    Promise.all([
      workspaceApi.listAllTasks(currentProject.id).then(r => r.items).catch(() => [] as WorkspaceTask[]),
      workspaceApi.listDocuments(currentProject.id).then(r => r.items).catch(() => [] as ProjectDocument[]),
      workspaceApi.getProjectOverview(currentProject.id).then(r => r.statistics).catch(() => stats),
    ]).then(([t, d, s]) => {
      setTasks(t.slice(0, 5))
      setDocs(d)
      setStats(s)
      setLoading(false)
    })
  }, [currentProject])

  if (!currentProject) return null

  const totalTasks = stats.form_tasks + stats.section_tasks + stats.review_tasks + stats.reply_tasks
  const doneTasks = stats.form_completed
  const progress = totalTasks > 0 ? Math.round((doneTasks / totalTasks) * 100) : 0
  const createdDate = (() => {
    try { return new Date(currentProject.created_at).toLocaleDateString('zh-CN') } catch { return '' }
  })()

  return (
    <div className="space-y-6">
      {/* 基本信息 */}
      <div className="panel p-5">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
            项目基本信息
          </h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-4 text-sm">
          <div>
            <p className="text-xs text-neutral-500 mb-1">项目名称</p>
            <p className="text-neutral-900 font-medium">{currentProject.name}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">项目编号</p>
            <p className="text-neutral-900 font-mono">{currentProject.code || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">设计阶段</p>
            <p className="text-neutral-900">{currentProject.stage || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">业主单位</p>
            <p className="text-neutral-900">{currentProject.client || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">承担部门</p>
            <p className="text-neutral-900">{currentProject?.department || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">资料数量</p>
            <p className="text-neutral-900">{docs.length} 份</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">创建时间</p>
            <p className="text-neutral-900 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-neutral-400" />{createdDate}
            </p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">项目状态</p>
            <span className={`badge ${
              currentProject.status === 'active' ? 'badge-brand' :
              currentProject.status === 'completed' ? 'badge-success' : 'badge-neutral'
            }`}>
              {currentProject.status === 'active' ? '进行中' : currentProject.status === 'completed' ? '已完成' : '已归档'}
            </span>
          </div>
        </div>

        {/* 进度条 */}
        <div className="mt-5 pt-5 border-t border-neutral-100">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-neutral-600 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-neutral-400" />
              总体进度
            </span>
            <span className="font-semibold text-neutral-900">{progress}%</span>
          </div>
          <div className="w-full h-2 bg-neutral-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-600 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* 快速操作 */}
      <div>
        <h2 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
          <Plus className="w-4 h-4 text-brand-600" strokeWidth={2} />
          快速操作
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {QUICK_ACTIONS.map(action => {
            const Icon = action.icon
            return (
              <button
                key={action.key}
                onClick={() => onTabChange(action.key)}
                className="panel p-4 text-left hover:border-brand-300 hover:bg-brand-50/30 transition-colors group"
              >
                <div className="w-9 h-9 rounded-lg bg-brand-50 flex items-center justify-center mb-3 group-hover:bg-brand-100">
                  <Icon className="w-5 h-5 text-brand-600" strokeWidth={1.75} />
                </div>
                <p className="text-sm font-medium text-neutral-900 mb-0.5">{action.label}</p>
                <p className="text-xs text-neutral-500 leading-relaxed">{action.desc}</p>
                <ChevronRight className="w-4 h-4 text-neutral-300 mt-2 group-hover:text-brand-600" />
              </button>
            )
          })}
        </div>
      </div>

      {/* 最近任务 */}
      <div>
        <h2 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
          <User className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
          最近任务
        </h2>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 text-brand-600 animate-spin" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="panel">
            <div className="empty-state py-10">
              <Clock className="empty-state-icon" strokeWidth={1.5} />
              <p className="empty-state-text">暂无任务记录，从快速操作开始</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {tasks.map(task => (
              <TaskProgressCard key={task.id} task={task} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
