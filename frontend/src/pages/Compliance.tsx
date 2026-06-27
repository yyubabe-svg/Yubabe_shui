/**
 * 合规初审模块主页面
 * 包含：统计看板、项目列表、筛选、创建项目、审核操作等功能
 */
import { useState, useEffect } from 'react'
import {
  FileCheck,
  Plus,
  Search,
  Filter,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FileText,
  Users,
  TrendingUp,
  ChevronRight,
  MoreHorizontal,
  Calendar,
  User,
  Building2,
  Tag,
  Upload,
  MessageSquare,
  Download,
  Eye,
} from 'lucide-react'
import {
  getStatistics,
  getProjects,
  createProject,
  getTemplates,
  type ComplianceStatistics,
  type ComplianceProject,
  type ChecklistTemplate,
  getStatusLabel,
  getStatusColor,
  getPriorityLabel,
  getPriorityColor,
} from '../api/compliance'

// 统计卡片组件
function StatCard({
  title,
  value,
  icon: Icon,
  color,
  subtext,
}: {
  title: string
  value: number | string
  icon: any
  color: string
  subtext?: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gov-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gov-500 mb-1">{title}</p>
          <p className="text-2xl font-bold text-gov-800">{value}</p>
          {subtext && <p className="text-xs text-gov-400 mt-1">{subtext}</p>}
        </div>
        <div className={`w-12 h-12 rounded-xl ${color} flex items-center justify-center`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  )
}

// 状态标签组件
function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(status as any)}`}>
      {getStatusLabel(status as any)}
    </span>
  )
}

// 创建项目弹窗
function CreateProjectModal({
  isOpen,
  onClose,
  onSuccess,
  templates,
}: {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  templates: ChecklistTemplate[]
}) {
  const [formData, setFormData] = useState({
    project_code: '',
    project_name: '',
    project_type: '',
    project_stage: '',
    applicant: '',
    applicant_dept: '',
    priority: 'normal',
    pass_score: 60,
    template_id: '',
  })
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.project_code || !formData.project_name) return

    setLoading(true)
    try {
      await createProject({
        ...formData,
        priority: formData.priority as any,
        template_id: formData.template_id ? Number(formData.template_id) : undefined,
      })
      onSuccess()
      onClose()
    } catch (error) {
      console.error('创建失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gov-200">
          <h2 className="text-xl font-bold text-gov-800">新建合规初审项目</h2>
          <p className="text-sm text-gov-500 mt-1">填写项目基本信息，创建后可上传相关资料并提交审核</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gov-700 mb-1.5">
                项目编号 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.project_code}
                onChange={(e) => setFormData({ ...formData, project_code: e.target.value })}
                className="w-full px-3 py-2 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                placeholder="例如：CDSD260001C"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gov-700 mb-1.5">
                项目名称 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.project_name}
                onChange={(e) => setFormData({ ...formData, project_name: e.target.value })}
                className="w-full px-3 py-2 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                placeholder="请输入项目名称"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gov-700 mb-1.5">项目类型</label>
              <select
                value={formData.project_type}
                onChange={(e) => setFormData({ ...formData, project_type: e.target.value })}
                className="w-full px-3 py-2 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
              >
                <option value="">请选择</option>
                <option value="堤防工程">堤防工程</option>
                <option value="水库工程">水库工程</option>
                <option value="灌溉工程">灌溉工程</option>
                <option value="供水工程">供水工程</option>
                <option value="水力发电">水力发电</option>
                <option value="河道整治">河道整治</option>
                <option value="其他">其他</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gov-700 mb-1.5">项目阶段</label>
              <select
                value={formData.project_stage}
                onChange={(e) => setFormData({ ...formData, project_stage: e.target.value })}
                className="w-full px-3 py-2 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
              >
                <option value="">请选择</option>
                <option value="项目建议书">项目建议书</option>
                <option value="可行性研究">可行性研究</option>
                <option value="初步设计">初步设计</option>
                <option value="施工图设计">施工图设计</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gov-700 mb-1.5">申报单位/人</label>
              <input
                type="text"
                value={formData.applicant}
                onChange={(e) => setFormData({ ...formData, applicant: e.target.value })}
                className="w-full px-3 py-2 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                placeholder="请输入"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gov-700 mb-1.5">申报部门</label>
              <input
                type="text"
                value={formData.applicant_dept}
                onChange={(e) => setFormData({ ...formData, applicant_dept: e.target.value })}
                className="w-full px-3 py-2 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                placeholder="请输入"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gov-700 mb-1.5">优先级</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="w-full px-3 py-2 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
              >
                <option value="low">低</option>
                <option value="normal">普通</option>
                <option value="high">高</option>
                <option value="urgent">紧急</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gov-700 mb-1.5">及格分数线</label>
              <input
                type="number"
                value={formData.pass_score}
                onChange={(e) => setFormData({ ...formData, pass_score: Number(e.target.value) })}
                className="w-full px-3 py-2 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                min={0}
                max={100}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gov-700 mb-1.5">检查表模板</label>
              <select
                value={formData.template_id}
                onChange={(e) => setFormData({ ...formData, template_id: e.target.value })}
                className="w-full px-3 py-2 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
              >
                <option value="">不使用模板</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>{t.template_name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gov-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gov-600 hover:bg-gov-100 rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading || !formData.project_code || !formData.project_name}
              className="px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {loading ? '创建中...' : '创建项目'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Compliance() {
  const [statistics, setStatistics] = useState<ComplianceStatistics | null>(null)
  const [projects, setProjects] = useState<ComplianceProject[]>([])
  const [templates, setTemplates] = useState<ChecklistTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [listStats, setListStats] = useState({
    all: 0, draft: 0, pending: 0, returned: 0, passed: 0, rejected: 0
  })

  const tabs = [
    { key: 'all', label: '全部', count: listStats.all },
    { key: 'draft', label: '草稿', count: listStats.draft },
    { key: 'pending', label: '待审核', count: listStats.pending },
    { key: 'returned', label: '已退回', count: listStats.returned },
    { key: 'passed', label: '已通过', count: listStats.passed },
    { key: 'rejected', label: '不通过', count: listStats.rejected },
  ]

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsRes, projectsRes, templatesRes] = await Promise.all([
        getStatistics(),
        getProjects({ page, page_size: 20, status: activeTab === 'all' ? undefined : activeTab, keyword: searchKeyword || undefined }),
        getTemplates({ is_active: true }),
      ])
      setStatistics(statsRes)
      setProjects(projectsRes.items)
      setTotal(projectsRes.total)
      setListStats(projectsRes.statistics)
      setTemplates(templatesRes)
    } catch (error) {
      console.error('加载数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [page, activeTab])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadData()
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('zh-CN')
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gov-800 flex items-center gap-2">
            <FileCheck className="w-7 h-7 text-primary-600" />
            合规初审
          </h1>
          <p className="text-gov-500 mt-1">水利工程项目合规性初审管理，支持检查表审核、流程跟踪、报告生成</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors shadow-sm"
        >
          <Plus className="w-5 h-5" />
          新建初审项目
        </button>
      </div>

      {/* 统计看板 */}
      {statistics && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            title="总项目数"
            value={statistics.total_projects}
            icon={FileText}
            color="bg-gradient-to-br from-blue-500 to-blue-600"
            subtext={`通过率 ${statistics.pass_rate}%`}
          />
          <StatCard
            title="待审核"
            value={statistics.pending_count}
            icon={Clock}
            color="bg-gradient-to-br from-orange-500 to-orange-600"
            subtext={`含审核中 ${statistics.reviewing_count} 项`}
          />
          <StatCard
            title="已通过"
            value={statistics.passed_count}
            icon={CheckCircle2}
            color="bg-gradient-to-br from-green-500 to-green-600"
            subtext={`平均得分 ${statistics.avg_score} 分`}
          />
          <StatCard
            title="平均审核天数"
            value={`${statistics.avg_review_days} 天`}
            icon={TrendingUp}
            color="bg-gradient-to-br from-purple-500 to-purple-600"
            subtext="效率统计"
          />
        </div>
      )}

      {/* 筛选和搜索 */}
      <div className="bg-white rounded-xl border border-gov-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => { setActiveTab(tab.key); setPage(1) }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gov-600 hover:bg-gov-100'
                }`}
              >
                {tab.label}
                <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-xs ${
                  activeTab === tab.key ? 'bg-primary-100 text-primary-700' : 'bg-gov-100 text-gov-500'
                }`}>
                  {tab.count}
                </span>
              </button>
            ))}
          </div>
          <form onSubmit={handleSearch} className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gov-400" />
              <input
                type="text"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                placeholder="搜索项目名称、编号、申报单位..."
                className="pl-9 pr-4 py-2 w-72 border border-gov-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm"
              />
            </div>
            <button
              type="button"
              className="p-2 border border-gov-300 rounded-lg hover:bg-gov-50 transition-colors"
            >
              <Filter className="w-4 h-4 text-gov-500" />
            </button>
          </form>
        </div>

        {/* 项目列表 */}
        {loading ? (
          <div className="py-12 text-center text-gov-400">
            <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto mb-3" />
            加载中...
          </div>
        ) : projects.length === 0 ? (
          <div className="py-16 text-center">
            <FileText className="w-16 h-16 text-gov-300 mx-auto mb-4" />
            <p className="text-gov-500 mb-2">暂无初审项目</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="text-primary-600 hover:text-primary-700 text-sm font-medium"
            >
              立即创建第一个项目
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gov-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gov-500 uppercase tracking-wider">项目信息</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gov-500 uppercase tracking-wider">类型/阶段</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gov-500 uppercase tracking-wider">申报方</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gov-500 uppercase tracking-wider">审核人</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gov-500 uppercase tracking-wider">状态</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gov-500 uppercase tracking-wider">得分</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gov-500 uppercase tracking-wider">时间</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gov-500 uppercase tracking-wider">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gov-100">
                {projects.map((project) => (
                  <tr key={project.id} className="hover:bg-gov-50 transition-colors">
                    <td className="py-4 px-4">
                      <div className="flex items-start gap-3">
                        <div className={`w-1 h-10 rounded-full ${
                          project.priority === 'urgent' ? 'bg-red-500' :
                          project.priority === 'high' ? 'bg-orange-500' :
                          project.priority === 'normal' ? 'bg-blue-500' : 'bg-gray-300'
                        } mt-1`} />
                        <div>
                          <p className="font-medium text-gov-800 hover:text-primary-600 cursor-pointer">
                            {project.project_name}
                          </p>
                          <p className="text-sm text-gov-500 font-mono">{project.project_code}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="text-sm">
                        <p className="text-gov-700 flex items-center gap-1">
                          <Tag className="w-3.5 h-3.5" />
                          {project.project_type || '-'}
                        </p>
                        <p className="text-gov-500">{project.project_stage || '-'}</p>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="text-sm">
                        <p className="text-gov-700 flex items-center gap-1">
                          <Building2 className="w-3.5 h-3.5" />
                          {project.applicant || '-'}
                        </p>
                        <p className="text-gov-500">{project.applicant_dept || '-'}</p>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="text-sm text-gov-700 flex items-center gap-1">
                        <User className="w-3.5 h-3.5" />
                        {project.reviewer_name || <span className="text-gov-400">未分配</span>}
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <StatusBadge status={project.status} />
                    </td>
                    <td className="py-4 px-4">
                      {project.status === 'passed' || project.status === 'reviewing' ? (
                        <span className={`font-semibold ${
                          project.total_score >= project.pass_score ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {project.total_score} 分
                        </span>
                      ) : (
                        <span className="text-gov-400">-</span>
                      )}
                    </td>
                    <td className="py-4 px-4">
                      <div className="text-sm">
                        <p className="text-gov-500 flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          {formatDate(project.created_at)}
                        </p>
                        {project.deadline && (
                          <p className="text-orange-600 text-xs">截止: {formatDate(project.deadline)}</p>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-1">
                        <button className="p-1.5 hover:bg-gov-100 rounded-lg transition-colors" title="查看详情">
                          <Eye className="w-4 h-4 text-gov-500" />
                        </button>
                        <button className="p-1.5 hover:bg-gov-100 rounded-lg transition-colors" title="上传附件">
                          <Upload className="w-4 h-4 text-gov-500" />
                        </button>
                        <button className="p-1.5 hover:bg-gov-100 rounded-lg transition-colors" title="评论">
                          <MessageSquare className="w-4 h-4 text-gov-500" />
                        </button>
                        {project.status === 'passed' && (
                          <button className="p-1.5 hover:bg-gov-100 rounded-lg transition-colors" title="下载报告">
                            <Download className="w-4 h-4 text-gov-500" />
                          </button>
                        )}
                        <button className="p-1.5 hover:bg-gov-100 rounded-lg transition-colors">
                          <MoreHorizontal className="w-4 h-4 text-gov-500" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 分页 */}
        {total > 20 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gov-200">
            <p className="text-sm text-gov-500">共 {total} 条记录</p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 text-sm border border-gov-300 rounded-lg hover:bg-gov-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              <span className="px-3 py-1.5 text-sm text-gov-600">第 {page} 页</span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page * 20 >= total}
                className="px-3 py-1.5 text-sm border border-gov-300 rounded-lg hover:bg-gov-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 创建项目弹窗 */}
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={loadData}
        templates={templates}
      />
    </div>
  )
}
