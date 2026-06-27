import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ChevronLeft, LayoutDashboard, FolderOpen, FileText, Table,
  SearchCheck, Reply, Search, Loader2, Calculator, FolderSearch,
  Map, Box, Waves, Ruler, Activity,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import { projectsApi } from '../../api/projects'
import ProjectOverview from './ProjectOverview'
import DocumentsPanel from './DocumentsPanel'
import SectionGenPanel from './SectionGenPanel'
import FormFillPanel from './FormFillPanel'
import AIReviewPanel from './AIReviewPanel'
import ExpertReplyPanel from './ExpertReplyPanel'
import SearchPanel from './SearchPanel'
import CalculationPanel from './CalculationPanel'
import HistoryReusePanel from './HistoryReusePanel'
import GISPanel from './GISPanel'
import CADPanel from './CADPanel'
import HydroModelPanel from './HydroModelPanel'
import ParametricDesignPanel from './ParametricDesignPanel'
import DigitalTwinPanel from './DigitalTwinPanel'

type TabKey = 'overview' | 'documents' | 'search' | 'section' | 'form' | 'review' | 'expert'
             | 'calc' | 'history' | 'gis' | 'cad'
             | 'hydro' | 'parametric' | 'twin'

interface TabDef {
  key: TabKey
  label: string
  icon: typeof LayoutDashboard
  group: 'core' | 'phase2' | 'phase3'
}

const TABS: TabDef[] = [
  { key: 'overview',  label: '概览',     icon: LayoutDashboard, group: 'core' },
  { key: 'documents', label: '资料管理', icon: FolderOpen,      group: 'core' },
  { key: 'search',    label: '资料检索', icon: Search,          group: 'core' },
  { key: 'section',   label: '报告生成', icon: FileText,        group: 'core' },
  { key: 'form',      label: '表格填报', icon: Table,           group: 'core' },
  { key: 'review',    label: 'AI 初审',  icon: SearchCheck,     group: 'core' },
  { key: 'expert',    label: '专家回复', icon: Reply,           group: 'core' },
  // 第二阶段功能
  { key: 'calc',      label: '水利计算', icon: Calculator,      group: 'phase2' },
  { key: 'history',   label: '历史复用', icon: FolderSearch,    group: 'phase2' },
  { key: 'gis',       label: 'GIS 出图', icon: Map,             group: 'phase2' },
  { key: 'cad',       label: 'CAD 检查', icon: Box,             group: 'phase2' },
  // 第三阶段功能
  { key: 'hydro',     label: '水文模型', icon: Waves,           group: 'phase3' },
  { key: 'parametric',label: '参数设计', icon: Ruler,           group: 'phase3' },
  { key: 'twin',      label: '项目看板', icon: Activity,        group: 'phase3' },
]

export default function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { currentProject, setCurrentProject } = useProject()
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!projectId) return
    setLoading(true)
    projectsApi.get(projectId)
      .then(p => setCurrentProject(p))
      .catch(e => setError(e?.response?.data?.detail || '项目不存在或加载失败'))
      .finally(() => setLoading(false))
  }, [projectId, setCurrentProject])

  if (loading) {
    return (
      <div className="h-[60vh] flex items-center justify-center">
        <Loader2 className="w-7 h-7 text-brand-600 animate-spin" />
      </div>
    )
  }

  if (error || !currentProject) {
    return (
      <div className="page-container">
        <div className="border border-neutral-200 bg-white px-8 py-12 text-center">
          <p className="text-sm text-danger mb-4">{error || '项目未找到'}</p>
          <button onClick={() => navigate('/workspace')} className="btn-primary">
            返回项目列表
          </button>
        </div>
      </div>
    )
  }

  const coreTabs = TABS.filter(t => t.group === 'core')
  const phase2Tabs = TABS.filter(t => t.group === 'phase2')
  const phase3Tabs = TABS.filter(t => t.group === 'phase3')

  return (
    <div className="page-container">
      {/* 顶部面包屑 + 标题 */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/workspace')}
          className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-700 mb-3"
        >
          <ChevronLeft className="w-4 h-4" />
          返回项目列表
        </button>
        <h1 className="text-xl font-semibold text-neutral-900 tracking-tight">{currentProject.name}</h1>
        <div className="flex items-center gap-3 mt-1.5 text-xs text-neutral-500 flex-wrap">
          {currentProject.code && <span className="font-mono">{currentProject.code}</span>}
          {currentProject.project_type_name && <span>{currentProject.project_type_name}</span>}
          {currentProject.stage && <span>{currentProject.stage}</span>}
          {currentProject.client && <span>业主：{currentProject.client}</span>}
        </div>
      </div>

      {/* Tab 导航 */}
      <div className="border-b border-neutral-200 mb-6 overflow-x-auto">
        <nav className="flex gap-1 -mb-px">
          {coreTabs.map(tab => {
            const Icon = tab.icon
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-brand-600 text-brand-700 font-medium'
                    : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                }`}
              >
                <Icon className="w-4 h-4" strokeWidth={1.75} />
                {tab.label}
              </button>
            )
          })}
          {/* 分隔 */}
          <div className="border-l border-neutral-200 mx-2 my-1.5" />
          {phase2Tabs.map(tab => {
            const Icon = tab.icon
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-brand-600 text-brand-700 font-medium'
                    : 'border-transparent text-neutral-400 hover:text-neutral-700 hover:border-neutral-300'
                }`}
                title="第二阶段功能"
              >
                <Icon className="w-4 h-4" strokeWidth={1.75} />
                {tab.label}
                <span className="text-[10px] bg-brand-100 text-brand-600 px-1 rounded ml-0.5">新</span>
              </button>
            )
          })}
          {/* 分隔 - 第三阶段 */}
          <div className="border-l border-neutral-200 mx-2 my-1.5" />
          {phase3Tabs.map(tab => {
            const Icon = tab.icon
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-violet-600 text-violet-700 font-medium'
                    : 'border-transparent text-neutral-400 hover:text-neutral-700 hover:border-neutral-300'
                }`}
                title="第三阶段功能"
              >
                <Icon className="w-4 h-4" strokeWidth={1.75} />
                {tab.label}
                <span className="text-[10px] bg-violet-100 text-violet-600 px-1 rounded ml-0.5">新</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab 内容 */}
      <div>
        {activeTab === 'overview' && <ProjectOverview onTabChange={setActiveTab} />}
        {activeTab === 'documents' && <DocumentsPanel />}
        {activeTab === 'search' && <SearchPanel />}
        {activeTab === 'section' && <SectionGenPanel />}
        {activeTab === 'form' && <FormFillPanel />}
        {activeTab === 'review' && <AIReviewPanel />}
        {activeTab === 'expert' && <ExpertReplyPanel />}
        {activeTab === 'calc' && <CalculationPanel />}
        {activeTab === 'history' && <HistoryReusePanel />}
        {activeTab === 'gis' && <GISPanel />}
        {activeTab === 'cad' && <CADPanel />}
        {activeTab === 'hydro' && <HydroModelPanel />}
        {activeTab === 'parametric' && <ParametricDesignPanel />}
        {activeTab === 'twin' && <DigitalTwinPanel />}
      </div>
    </div>
  )
}
