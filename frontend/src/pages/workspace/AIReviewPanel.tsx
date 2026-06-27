import { useEffect, useState, useRef, useCallback } from 'react'
import {
  SearchCheck, FileText, Play, Download, Loader2,
  CheckCircle2, XCircle, AlertTriangle, AlertCircle, Info,
  ListFilter, RefreshCw, ChevronDown, ChevronUp, FileCheck,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import {
  workspaceApi,
  type ProjectDocument,
  type ReviewIssue,
  type ReviewTaskDetail,
  type IssueSeverity,
  type IssueStatus,
} from '../../api/workspace'
import StepWizard from '../../components/common/StepWizard'

type Step = 'select' | 'running' | 'result'

const REVIEW_DIMENSIONS = [
  { key: 'code_compliance', label: '规范符合性' },
  { key: 'param_completeness', label: '参数完整性' },
  { key: 'chapter_completeness', label: '章节完整性' },
  { key: 'value_consistency', label: '数值一致性' },
  { key: 'format_standard', label: '格式规范性' },
]

// 严重程度显示配置
const severityConfig: Record<IssueSeverity, {
  icon: typeof AlertCircle
  label: string
  order: number
  headerBg: string
  headerText: string
  headerBorder: string
  badgeBg: string
  badgeText: string
  dotColor: string
  cardBorder: string
}> = {
  critical: {
    icon: AlertCircle,
    label: '严重问题',
    order: 0,
    headerBg: 'bg-red-50',
    headerText: 'text-red-700',
    headerBorder: 'border-red-200',
    badgeBg: 'bg-red-100',
    badgeText: 'text-red-700',
    dotColor: 'bg-red-500',
    cardBorder: 'border-l-red-500',
  },
  major: {
    icon: AlertTriangle,
    label: '重要问题',
    order: 1,
    headerBg: 'bg-orange-50',
    headerText: 'text-orange-700',
    headerBorder: 'border-orange-200',
    badgeBg: 'bg-orange-100',
    badgeText: 'text-orange-700',
    dotColor: 'bg-orange-500',
    cardBorder: 'border-l-orange-500',
  },
  minor: {
    icon: Info,
    label: '一般问题',
    order: 2,
    headerBg: 'bg-yellow-50',
    headerText: 'text-yellow-700',
    headerBorder: 'border-yellow-200',
    badgeBg: 'bg-yellow-100',
    badgeText: 'text-yellow-700',
    dotColor: 'bg-yellow-500',
    cardBorder: 'border-l-yellow-500',
  },
  suggestion: {
    icon: FileCheck,
    label: '优化建议',
    order: 3,
    headerBg: 'bg-blue-50',
    headerText: 'text-blue-700',
    headerBorder: 'border-blue-200',
    badgeBg: 'bg-blue-100',
    badgeText: 'text-blue-700',
    dotColor: 'bg-blue-500',
    cardBorder: 'border-l-blue-500',
  },
}

const categoryLabels: Record<string, string> = {
  code_compliance: '规范符合性',
  param_completeness: '参数完整性',
  chapter_completeness: '章节完整性',
  value_consistency: '数值一致性',
  format_standard: '格式规范性',
  code_ref: '规范引用',
  data_consistency: '数据一致性',
  design_depth: '设计深度',
  text: '文字表述',
}

const statusLabels: Record<IssueStatus, string> = {
  open: '未处理',
  accepted: '已接受',
  ignored: '已忽略',
  resolved: '已解决',
}

export default function AIReviewPanel() {
  const { currentProject } = useProject()
  const [step, setStep] = useState<Step>('select')
  const [docs, setDocs] = useState<ProjectDocument[]>([])
  const [selectedDoc, setSelectedDoc] = useState<ProjectDocument | null>(null)
  const [selectedDims, setSelectedDims] = useState<string[]>(REVIEW_DIMENSIONS.map(d => d.key))
  const [taskId, setTaskId] = useState<number | null>(null)
  const [taskDetail, setTaskDetail] = useState<ReviewTaskDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState(false)
  const [updatingIssueId, setUpdatingIssueId] = useState<number | null>(null)
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({})

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const cancelledRef = useRef(false)

  // 加载文档列表
  useEffect(() => {
    if (!currentProject) return
    cancelledRef.current = false
    workspaceApi.listDocuments(currentProject.id)
      .then(res => setDocs(res.items || []))
      .catch(() => setDocs([]))
    return () => {
      cancelledRef.current = true
    }
  }, [currentProject])

  // 清理轮询和SSE
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  // 只显示已解析完成的文档
  const parsedDocs = docs.filter(d => d.parse_status === 'completed' || d.parse_status === 'parsed')

  const toggleDim = (key: string) => {
    setSelectedDims(prev =>
      prev.includes(key) ? prev.filter(d => d !== key) : [...prev, key]
    )
  }

  // 轮询获取任务详情
  const pollTask = useCallback(async (tid: number) => {
    try {
      const detail = await workspaceApi.getReviewTask(tid)
      if (cancelledRef.current) return
      setTaskDetail(detail)

      if (detail.status === 'completed' || detail.status === 'failed' || detail.status === 'error') {
        stopPolling()
        if (detail.status === 'completed') {
          setStep('result')
        } else {
          setError('审查任务失败，请重试')
          setStep('select')
        }
        setLoading(false)
      }
    } catch (e: any) {
      // 轮询出错时静默重试，不打断流程
      console.warn('poll review task error:', e)
    }
  }, [stopPolling])

  const handleRun = async () => {
    if (!currentProject || !selectedDoc) return
    setLoading(true)
    setError('')
    setTaskDetail(null)
    setStep('running')
    cancelledRef.current = false

    try {
      // 1. 创建审查任务
      const createRes = await workspaceApi.createReviewTask(currentProject.id, {
        document_id: selectedDoc.id,
        dimensions: selectedDims.length > 0 ? selectedDims : undefined,
      })
      const tid = createRes.task_id
      setTaskId(tid)

      // 2. 启动审查
      await workspaceApi.runReview(tid)

      // 3. 优先尝试SSE，降级为定时轮询
      const sseUrl = workspaceApi.getReviewStreamUrl(tid)
      try {
        const es = new EventSource(sseUrl)
        eventSourceRef.current = es

        es.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (cancelledRef.current) return
            setTaskDetail(prev => prev ? { ...prev, ...data } : data)
            if (data.status === 'completed' || data.status === 'failed' || data.status === 'error') {
              es.close()
              eventSourceRef.current = null
              if (data.status === 'completed') {
                // SSE可能不携带完整issues，做一次最终拉取
                workspaceApi.getReviewTask(tid).then(d => {
                  if (!cancelledRef.current) {
                    setTaskDetail(d)
                    setStep('result')
                    setLoading(false)
                  }
                })
              } else {
                setError('审查任务失败，请重试')
                setStep('select')
                setLoading(false)
              }
            }
          } catch {
            // 忽略解析错误
          }
        }

        es.onerror = () => {
          es.close()
          eventSourceRef.current = null
          // SSE失败，降级为轮询
          startPolling(tid)
        }
      } catch {
        // 浏览器不支持SSE或连接失败，使用轮询
        startPolling(tid)
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || '创建审查任务失败，请重试')
      setStep('select')
      setLoading(false)
    }
  }

  const startPolling = (tid: number) => {
    // 立即拉一次
    pollTask(tid)
    pollTimerRef.current = setInterval(() => pollTask(tid), 2000)
  }

  const handleStatusChange = async (issueId: number, status: IssueStatus) => {
    setUpdatingIssueId(issueId)
    try {
      await workspaceApi.updateReviewIssue(issueId, { status })
      // 本地更新
      setTaskDetail(prev => {
        if (!prev) return prev
        return {
          ...prev,
          issues: prev.issues.map(i => i.id === issueId ? { ...i, status } : i),
        }
      })
    } catch (e: any) {
      setError(e?.response?.data?.detail || '更新状态失败')
    } finally {
      setUpdatingIssueId(null)
    }
  }

  const handleExport = async () => {
    if (!taskId) return
    setExporting(true)
    try {
      const url = workspaceApi.exportReviewReport(taskId)
      // 在新标签页打开下载
      window.open(url, '_blank')
    } catch (e: any) {
      setError(e?.response?.data?.detail || '导出失败')
    } finally {
      setExporting(false)
    }
  }

  const reset = () => {
    stopPolling()
    setStep('select')
    setSelectedDoc(null)
    setTaskId(null)
    setTaskDetail(null)
    setError('')
    setLoading(false)
    setCollapsedGroups({})
  }

  const toggleGroup = (sev: string) => {
    setCollapsedGroups(prev => ({ ...prev, [sev]: !prev[sev] }))
  }

  const steps = [
    { key: 'select', label: '选择文档', icon: FileText },
    { key: 'running', label: 'AI审查中', icon: Play },
    { key: 'result', label: '查看结果', icon: SearchCheck },
  ] as const

  // 按严重程度分组问题
  const groupedIssues = taskDetail ? (() => {
    const groups: Record<IssueSeverity, ReviewIssue[]> = {
      critical: [], major: [], minor: [], suggestion: [],
    }
    taskDetail.issues.forEach(issue => {
      groups[issue.severity]?.push(issue)
    })
    return groups
  })() : null

  return (
    <div className="space-y-6">
      <StepWizard steps={steps} activeStep={step} className="mb-6" />

      {/* 步骤1：选择文档 */}
      {step === 'select' && (
        <div className="space-y-5">
          <div className="panel p-5">
            <h2 className="text-sm font-semibold text-neutral-900 mb-4 flex items-center gap-2">
              <FileText className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
              选择审查文档
              <span className="text-xs font-normal text-neutral-400 ml-1">（仅显示已解析完成的文档）</span>
            </h2>
            {parsedDocs.length === 0 ? (
              <div className="empty-state py-10">
                <FileText className="empty-state-icon" strokeWidth={1.5} />
                <p className="empty-state-text">
                  {docs.length === 0
                    ? '请先在「资料管理」上传要审查的文档'
                    : '暂无可审查的文档，请等待文档解析完成后再试'}
                </p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[320px] overflow-y-auto">
                {parsedDocs.map(doc => (
                  <label
                    key={doc.id}
                    className={`flex items-center gap-3 p-3 border rounded cursor-pointer transition-colors ${
                      selectedDoc?.id === doc.id
                        ? 'border-brand-400 bg-brand-50/40'
                        : 'border-neutral-200 hover:border-neutral-300 bg-white'
                    }`}
                  >
                    <input
                      type="radio"
                      name="reviewDoc"
                      checked={selectedDoc?.id === doc.id}
                      onChange={() => setSelectedDoc(doc)}
                      className="text-brand-600"
                    />
                    <FileText className="w-5 h-5 text-blue-500 flex-shrink-0" strokeWidth={1.5} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-neutral-900 truncate">{doc.title || doc.original_filename}</p>
                      <p className="text-xs text-neutral-500">
                        {doc.file_type?.toUpperCase() || '文档'} · {(doc.file_size / 1024).toFixed(1)} KB
                        {doc.total_pages ? ` · ${doc.total_pages}页` : ''}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="panel p-5">
            <h2 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
              <ListFilter className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
              审查维度（可多选）
            </h2>
            <div className="flex flex-wrap gap-2">
              {REVIEW_DIMENSIONS.map(dim => (
                <button
                  key={dim.key}
                  onClick={() => toggleDim(dim.key)}
                  className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                    selectedDims.includes(dim.key)
                      ? 'bg-brand-50 border-brand-200 text-brand-700'
                      : 'bg-white border-neutral-200 text-neutral-500 hover:border-neutral-300'
                  }`}
                >
                  {dim.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-neutral-400 mt-2">不选则默认审查全部维度</p>
          </div>

          <div className="border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" strokeWidth={1.75} />
            <p className="text-xs text-amber-800">
              AI 审查结果仅供参考，不能替代人工校审。审查意见需由专业人员确认后使用。
            </p>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end">
            <button onClick={handleRun} disabled={!selectedDoc || loading} className="btn-primary px-6">
              <Play className="w-4 h-4" strokeWidth={1.75} />
              开始审查
            </button>
          </div>
        </div>
      )}

      {/* 步骤2：运行中 */}
      {step === 'running' && (
        <div className="panel p-10">
          <div className="flex items-center gap-3 mb-4">
            <Loader2 className="w-6 h-6 text-brand-600 animate-spin flex-shrink-0" />
            <div>
              <p className="text-sm text-neutral-800 font-medium">正在审查文档…</p>
              <p className="text-xs text-neutral-500 mt-0.5">
                {selectedDoc?.title || selectedDoc?.original_filename}
              </p>
            </div>
          </div>

          {/* 进度条 */}
          <div className="mb-3">
            <div className="flex justify-between text-xs text-neutral-500 mb-1.5">
              <span>审查进度</span>
              <span>{taskDetail?.progress ?? 0}%</span>
            </div>
            <div className="w-full h-2 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full transition-all duration-500"
                style={{ width: `${taskDetail?.progress ?? 0}%` }}
              />
            </div>
          </div>

          {/* 实时状态提示 */}
          <div className="bg-neutral-50 rounded-md px-4 py-3 mt-4">
            <p className="text-xs text-neutral-500">
              {taskDetail?.status === 'running' && '正在分析文档内容，检测设计问题…'}
              {taskDetail?.status === 'pending' && '任务已创建，正在排队…'}
              {!taskDetail && '任务初始化中…'}
            </p>
          </div>

          <p className="text-xs text-neutral-400 mt-4 text-center">
            审查可能需要数十秒到数分钟，请勿关闭页面
          </p>
        </div>
      )}

      {/* 步骤3：结果 */}
      {step === 'result' && taskDetail && (
        <div className="space-y-5">
          {/* 顶部操作栏 */}
          <div className="panel p-4 flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-500" strokeWidth={1.5} />
              <span className="text-sm font-medium text-neutral-900">审查完成</span>
              <span className="text-xs text-neutral-500">
                {taskDetail.document_title || selectedDoc?.title}
              </span>
            </div>
            <div className="flex gap-2">
              <button onClick={reset} className="btn-secondary text-xs">
                <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.75} />
                重新审查
              </button>
              <button onClick={handleExport} disabled={exporting} className="btn-primary text-xs px-4">
                {exporting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.75} />
                ) : (
                  <Download className="w-3.5 h-3.5" strokeWidth={1.75} />
                )}
                导出审查报告
              </button>
            </div>
          </div>

          {/* 统计卡片 */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="panel p-4 text-center">
              <div className="text-2xl font-bold text-brand-600">{taskDetail.total_score ?? '--'}</div>
              <div className="text-xs text-neutral-500 mt-1">综合评分</div>
            </div>
            <StatCard
              count={taskDetail.issue_count_critical}
              label="严重问题"
              bgColor="bg-red-50"
              textColor="text-red-600"
              icon={AlertCircle}
            />
            <StatCard
              count={taskDetail.issue_count_major}
              label="重要问题"
              bgColor="bg-orange-50"
              textColor="text-orange-600"
              icon={AlertTriangle}
            />
            <StatCard
              count={taskDetail.issue_count_minor}
              label="一般问题"
              bgColor="bg-yellow-50"
              textColor="text-yellow-600"
              icon={Info}
            />
            <StatCard
              count={taskDetail.issue_count_suggestion}
              label="优化建议"
              bgColor="bg-blue-50"
              textColor="text-blue-600"
              icon={FileCheck}
            />
          </div>

          {/* 摘要 */}
          {taskDetail.summary && (
            <div className="panel p-4">
              <h3 className="text-sm font-semibold text-neutral-900 mb-2">审查摘要</h3>
              <p className="text-sm text-neutral-700 leading-relaxed whitespace-pre-wrap">{taskDetail.summary}</p>
            </div>
          )}

          {/* 问题列表 - 按严重程度分组 */}
          {groupedIssues && (
            <div className="space-y-4">
              {(Object.keys(severityConfig) as IssueSeverity[])
                .sort((a, b) => severityConfig[a].order - severityConfig[b].order)
                .map(sev => {
                  const issues = groupedIssues[sev]
                  if (!issues || issues.length === 0) return null
                  const cfg = severityConfig[sev]
                  const Icon = cfg.icon
                  const collapsed = collapsedGroups[sev]

                  return (
                    <div key={sev} className="border border-neutral-200 rounded-lg overflow-hidden bg-white">
                      {/* 分组标题 */}
                      <button
                        onClick={() => toggleGroup(sev)}
                        className={`w-full flex items-center gap-2 px-4 py-2.5 ${cfg.headerBg} border-b ${cfg.headerBorder} text-left`}
                      >
                        <Icon className={`w-4 h-4 ${cfg.headerText}`} strokeWidth={1.75} />
                        <span className={`text-sm font-semibold ${cfg.headerText}`}>{cfg.label}</span>
                        <span className={`text-xs ${cfg.badgeBg} ${cfg.badgeText} px-1.5 py-0.5 rounded-full font-medium`}>
                          {issues.length}
                        </span>
                        <div className="ml-auto">
                          {collapsed ? (
                            <ChevronDown className="w-4 h-4 text-neutral-400" />
                          ) : (
                            <ChevronUp className="w-4 h-4 text-neutral-400" />
                          )}
                        </div>
                      </button>

                      {/* 问题卡片 */}
                      {!collapsed && (
                        <div className="divide-y divide-neutral-100">
                          {issues.map((issue, idx) => {
                            const isUpdating = updatingIssueId === issue.id
                            return (
                              <div
                                key={issue.id}
                                className={`p-4 border-l-4 ${cfg.cardBorder} hover:bg-neutral-50/30 transition-colors`}
                              >
                                <div className="flex items-start gap-3">
                                  <div className="flex-1 min-w-0">
                                    {/* 问题头部 */}
                                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                                      <span className="text-xs font-mono text-neutral-400">#{idx + 1}</span>
                                      <span className={`text-xs px-2 py-0.5 rounded-full ${cfg.badgeBg} ${cfg.badgeText} font-medium flex items-center gap-1`}>
                                        <span className={`w-1.5 h-1.5 rounded-full ${cfg.dotColor}`} />
                                        {cfg.label.replace('问题', '')}
                                      </span>
                                      {issue.category && (
                                        <span className="text-xs px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600">
                                          {categoryLabels[issue.category] || issue.category}
                                        </span>
                                      )}
                                      {issue.status !== 'open' && (
                                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                                          issue.status === 'accepted' ? 'bg-green-100 text-green-700' :
                                          issue.status === 'resolved' ? 'bg-blue-100 text-blue-700' :
                                          'bg-neutral-100 text-neutral-500'
                                        }`}>
                                          {statusLabels[issue.status]}
                                        </span>
                                      )}
                                    </div>

                                    {/* 位置信息 */}
                                    {(issue.chapter_path || issue.page_number || issue.location_desc) && (
                                      <div className="text-xs text-neutral-500 mb-2 flex items-center gap-2 flex-wrap">
                                        {issue.page_number && (
                                          <span className="inline-flex items-center gap-1">
                                            <FileText className="w-3 h-3" />
                                            第{issue.page_number}页
                                          </span>
                                        )}
                                        {issue.chapter_path && (
                                          <span className="inline-flex items-center gap-1">
                                            <span className="text-neutral-300">|</span>
                                            {issue.chapter_path}
                                          </span>
                                        )}
                                        {issue.location_desc && (
                                          <span className="inline-flex items-center gap-1">
                                            <span className="text-neutral-300">|</span>
                                            {issue.location_desc}
                                          </span>
                                        )}
                                      </div>
                                    )}

                                    {/* 问题描述 */}
                                    <p className="text-sm text-neutral-800 mb-2 leading-relaxed">
                                      {issue.description}
                                    </p>

                                    {/* 原文引用 */}
                                    {issue.original_text && (
                                      <div className="bg-neutral-50 rounded px-3 py-2 mb-2 border-l-2 border-neutral-300">
                                        <p className="text-xs text-neutral-400 mb-0.5">原文：</p>
                                        <p className="text-xs text-neutral-600 whitespace-pre-wrap">{issue.original_text}</p>
                                      </div>
                                    )}

                                    {/* 规范依据 */}
                                    {issue.basis_code && (
                                      <div className="flex items-start gap-1.5 mb-2">
                                        <Info className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0 mt-0.5" />
                                        <p className="text-xs text-neutral-600">
                                          <span className="text-neutral-400">规范依据：</span>
                                          {issue.basis_code}
                                        </p>
                                      </div>
                                    )}

                                    {/* 修改建议 */}
                                    {issue.suggestion && (
                                      <div className="bg-brand-50/50 rounded px-3 py-2 border-l-2 border-brand-400 mb-3">
                                        <p className="text-xs text-brand-700">
                                          <span className="text-brand-500 font-medium">修改建议：</span>
                                          {issue.suggestion}
                                        </p>
                                      </div>
                                    )}

                                    {/* 状态操作按钮 */}
                                    {issue.status === 'open' ? (
                                      <div className="flex items-center gap-2 mt-2">
                                        <button
                                          onClick={() => handleStatusChange(issue.id, 'accepted')}
                                          disabled={isUpdating}
                                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-md bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 transition-colors disabled:opacity-50"
                                        >
                                          <CheckCircle2 className="w-3 h-3" strokeWidth={2} />
                                          接受
                                        </button>
                                        <button
                                          onClick={() => handleStatusChange(issue.id, 'resolved')}
                                          disabled={isUpdating}
                                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-md bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors disabled:opacity-50"
                                        >
                                          <CheckCircle2 className="w-3 h-3" strokeWidth={2} />
                                          已解决
                                        </button>
                                        <button
                                          onClick={() => handleStatusChange(issue.id, 'ignored')}
                                          disabled={isUpdating}
                                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-md bg-neutral-50 text-neutral-600 border border-neutral-200 hover:bg-neutral-100 transition-colors disabled:opacity-50"
                                        >
                                          <XCircle className="w-3 h-3" strokeWidth={2} />
                                          忽略
                                        </button>
                                      </div>
                                    ) : (
                                      <div className="flex items-center gap-2 mt-2">
                                        <button
                                          onClick={() => handleStatusChange(issue.id, 'open')}
                                          disabled={isUpdating}
                                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-md bg-white text-neutral-500 border border-neutral-200 hover:bg-neutral-50 transition-colors disabled:opacity-50"
                                        >
                                          重新标记为未处理
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                })}

              {/* 无问题提示 */}
              {taskDetail.issues.length === 0 && (
                <div className="panel p-8 text-center">
                  <CheckCircle2 className="w-10 h-10 text-green-500 mx-auto mb-3" strokeWidth={1.5} />
                  <p className="text-sm text-neutral-700 font-medium">未发现问题</p>
                  <p className="text-xs text-neutral-500 mt-1">文档质量良好，未检测到明显的设计问题</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// 统计卡片子组件
function StatCard({
  count,
  label,
  bgColor,
  textColor,
  icon: Icon,
}: {
  count: number
  label: string
  bgColor: string
  textColor: string
  icon: typeof AlertCircle
}) {
  return (
    <div className={`panel p-4 text-center ${bgColor}`}>
      <div className="flex items-center justify-center gap-1.5 mb-1">
        <Icon className={`w-4 h-4 ${textColor}`} strokeWidth={1.75} />
        <span className={`text-2xl font-bold ${textColor}`}>{count}</span>
      </div>
      <div className="text-xs text-neutral-500">{label}</div>
    </div>
  )
}
