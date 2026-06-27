import { useState, useEffect, useRef, useCallback } from 'react'
import {
  MessageSquare, Send, Download, CheckCircle, Loader2, ChevronDown,
  ChevronRight, FileText, AlertCircle, RefreshCw, Sparkles, Save,
  FolderOpen, Calendar, Tag, MapPin, Hash, User,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import {
  workspaceApi,
  type ProjectDocument,
  type ExpertReplyTaskDetail,
  type ExpertOpinionItem,
} from '../../api/workspace'

// 专业分类颜色映射
const MAJOR_CATEGORY_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  hydrology:    { label: '水文',     bg: 'bg-blue-50',    text: 'text-blue-700',    border: 'border-blue-200' },
  hydraulic:    { label: '水工',     bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  geology:      { label: '地质',     bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-200' },
  construction: { label: '施工组织', bg: 'bg-orange-50',  text: 'text-orange-700',  border: 'border-orange-200' },
  investment:   { label: '投资',     bg: 'bg-purple-50',  text: 'text-purple-700',  border: 'border-purple-200' },
  environment:  { label: '环境水保', bg: 'bg-teal-50',    text: 'text-teal-700',    border: 'border-teal-200' },
  format:       { label: '格式',     bg: 'bg-gray-50',    text: 'text-gray-600',    border: 'border-gray-200' },
}

function getCategoryConfig(cat: string) {
  return MAJOR_CATEGORY_CONFIG[cat] || { label: cat || '其他', bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200' }
}

// 自适应高度 textarea
function AutoTextarea({
  value,
  onChange,
  placeholder,
  minHeight = 80,
  className = '',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  minHeight?: number
  className?: string
}) {
  const ref = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.max(el.scrollHeight, minHeight) + 'px'
  }, [value, minHeight])
  return (
    <textarea
      ref={ref}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full resize-none rounded-md border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 ${className}`}
      style={{ minHeight }}
    />
  )
}

type Step = 'select' | 'parsing' | 'reply'

export default function ExpertReplyPanel() {
  const { currentProject } = useProject()

  // ===== 步骤与通用状态 =====
  const [step, setStep] = useState<Step>('select')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // ===== 第一步：文档选择 =====
  const [documents, setDocuments] = useState<ProjectDocument[]>([])
  const [opinionDocId, setOpinionDocId] = useState<number | null>(null)
  const [reportDocId, setReportDocId] = useState<number | null>(null)
  const [meetingName, setMeetingName] = useState('')
  const [meetingDate, setMeetingDate] = useState('')
  const [taskId, setTaskId] = useState<number | null>(null)

  // ===== 解析进度 =====
  const [parseProgress, setParseProgress] = useState(0)
  const [parseStatus, setParseStatus] = useState('')
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  // ===== 第三步：意见列表 =====
  const [taskDetail, setTaskDetail] = useState<ExpertReplyTaskDetail | null>(null)
  const [opinions, setOpinions] = useState<ExpertOpinionItem[]>([])
  const [generatingId, setGeneratingId] = useState<number | null>(null)
  const [generatingAll, setGeneratingAll] = useState(false)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [expandedCats, setExpandedCats] = useState<Record<string, boolean>>({})
  const [exporting, setExporting] = useState(false)
  const batchPollTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  // 加载文档列表
  useEffect(() => {
    if (!currentProject) return
    setLoading(true)
    workspaceApi.listDocuments(currentProject.id)
      .then(res => {
        setDocuments(res.items || [])
        // 自动预选已标记的文档
        const opinionDoc = res.items?.find(d => d.is_expert_opinion)
        const reportDoc = res.items?.find(d => d.is_report)
        if (opinionDoc) setOpinionDocId(opinionDoc.id)
        if (reportDoc) setReportDocId(reportDoc.id)
      })
      .catch(e => setError(e?.response?.data?.detail || '加载文档列表失败'))
      .finally(() => setLoading(false))
  }, [currentProject])

  // 轮询解析任务状态
  const startPolling = useCallback((tid: number) => {
    if (pollTimer.current) clearInterval(pollTimer.current)
    pollTimer.current = setInterval(async () => {
      try {
        const detail = await workspaceApi.getExpertReplyTask(tid)
        setTaskDetail(detail)
        setParseProgress(detail.progress || 0)
        setParseStatus(detail.status)
        if (detail.status === 'completed' || detail.status === 'parsed') {
          if (pollTimer.current) clearInterval(pollTimer.current)
          pollTimer.current = null
          setOpinions(detail.opinions || [])
          // 默认展开所有分类
          const cats: Record<string, boolean> = {}
          ;(detail.opinions || []).forEach(o => { cats[o.major_category] = true })
          setExpandedCats(cats)
          setStep('reply')
        } else if (detail.status === 'failed') {
          if (pollTimer.current) clearInterval(pollTimer.current)
          pollTimer.current = null
          setError('意见解析失败，请重试')
          setStep('select')
        }
      } catch (e: any) {
        // 忽略轮询中的临时错误
      }
    }, 2000)
  }, [])

  useEffect(() => {
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current)
      if (batchPollTimer.current) clearInterval(batchPollTimer.current)
    }
  }, [])

  // 创建任务并开始解析
  const handleCreateTask = async () => {
    if (!currentProject || !opinionDocId) {
      setError('请选择专家意见文档')
      return
    }
    setError('')
    setLoading(true)
    try {
      const res = await workspaceApi.createExpertReplyTask(currentProject.id, {
        opinion_document_id: opinionDocId,
        report_document_id: reportDocId ?? undefined,
        meeting_name: meetingName.trim() || undefined,
        meeting_date: meetingDate || undefined,
      })
      setTaskId(res.task_id)
      setStep('parsing')
      setParseStatus('parsing')
      setParseProgress(5)
      // 触发解析
      await workspaceApi.parseExpertOpinions(res.task_id)
      startPolling(res.task_id)
    } catch (e: any) {
      setError(e?.response?.data?.detail || '创建任务失败')
    } finally {
      setLoading(false)
    }
  }

  // 单条生成回复
  const handleGenerateReply = async (opinionId: number) => {
    setGeneratingId(opinionId)
    setError('')
    try {
      const res = await workspaceApi.generateOpinionReply(opinionId)
      setOpinions(prev => prev.map(o =>
        o.id === opinionId
          ? {
              ...o,
              reply: {
                reply_content: res.reply_content,
                modify_status: o.reply?.modify_status || '',
                modify_location: o.reply?.modify_location || '',
                modify_page: o.reply?.modify_page || '',
                status: 'generated',
              },
            }
          : o
      ))
      // 刷新详情
      if (taskId) {
        const d = await workspaceApi.getExpertReplyTask(taskId)
        setTaskDetail(d)
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || '生成回复失败')
    } finally {
      setGeneratingId(null)
    }
  }

  // 批量生成所有回复
  const handleGenerateAll = async () => {
    if (!taskId) return
    setGeneratingAll(true)
    setError('')
    try {
      await workspaceApi.generateAllReplies(taskId)
      // 先清理旧的轮询
      if (batchPollTimer.current) clearInterval(batchPollTimer.current)
      // 轮询等待批量生成完成
      batchPollTimer.current = setInterval(async () => {
        try {
          const d = await workspaceApi.getExpertReplyTask(taskId)
          setTaskDetail(d)
          setOpinions(d.opinions || [])
          const allDone = (d.opinions || []).every(o => o.reply?.reply_content)
          if (allDone || (d.status !== 'generating' && d.status !== 'pending')) {
            if (batchPollTimer.current) {
              clearInterval(batchPollTimer.current)
              batchPollTimer.current = null
            }
            setGeneratingAll(false)
          }
        } catch {
          // 忽略轮询中的临时错误
        }
      }, 2000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || '批量生成失败')
      setGeneratingAll(false)
    }
  }

  // 保存单条回复（包括修改情况）
  const handleSaveReply = async (opinion: ExpertOpinionItem) => {
    if (!opinion.reply) return
    setSavingId(opinion.id)
    setError('')
    try {
      await workspaceApi.updateOpinionReply(opinion.id, {
        reply_content: opinion.reply.reply_content,
        modify_status: opinion.reply.modify_status || undefined,
        modify_location: opinion.reply.modify_location || undefined,
        modify_page: opinion.reply.modify_page || undefined,
      })
      setOpinions(prev => prev.map(o =>
        o.id === opinion.id
          ? { ...o, reply: { ...o.reply!, status: 'saved' } }
          : o
      ))
    } catch (e: any) {
      setError(e?.response?.data?.detail || '保存失败')
    } finally {
      setSavingId(null)
    }
  }

  // 更新回复字段
  const updateReplyField = (opinionId: number, field: string, value: string) => {
    setOpinions(prev => prev.map(o => {
      if (o.id !== opinionId) return o
      const reply = o.reply || { reply_content: '', status: 'draft' }
      return { ...o, reply: { ...reply, [field]: value, status: 'edited' } }
    }))
  }

  // 导出回复表
  const handleExport = async () => {
    if (!taskId) return
    setExporting(true)
    try {
      const url = workspaceApi.exportReplyTable(taskId)
      window.open(url, '_blank')
    } catch (e: any) {
      setError(e?.response?.data?.detail || '导出失败')
    } finally {
      setExporting(false)
    }
  }

  // 重置
  const handleReset = () => {
    if (pollTimer.current) clearInterval(pollTimer.current)
    if (batchPollTimer.current) clearInterval(batchPollTimer.current)
    setStep('select')
    setTaskId(null)
    setTaskDetail(null)
    setOpinions([])
    setParseProgress(0)
    setParseStatus('')
    setError('')
    setGeneratingAll(false)
    setMeetingName('')
    setMeetingDate('')
  }

  // 按专业分组
  const groupedOpinions = useCallback(() => {
    const groups: Record<string, ExpertOpinionItem[]> = {}
    opinions.forEach(o => {
      const cat = o.major_category || 'other'
      if (!groups[cat]) groups[cat] = []
      groups[cat].push(o)
    })
    // 按 opinion_index 排序
    Object.keys(groups).forEach(k => groups[k].sort((a, b) => a.opinion_index - b.opinion_index))
    return groups
  }, [opinions])

  const groups = groupedOpinions()
  const totalReplied = opinions.filter(o => o.reply?.reply_content?.trim()).length

  // ==================== 渲染 ====================

  if (!currentProject) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-neutral-500">
        请先选择一个项目
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-brand-600" strokeWidth={1.75} />
          <h1 className="text-base font-semibold text-neutral-900">专家意见回复</h1>
          {taskDetail?.meeting_name && (
            <span className="text-xs text-neutral-500 ml-2">· {taskDetail.meeting_name}</span>
          )}
          {taskDetail?.meeting_date && (
            <span className="text-xs text-neutral-500">{taskDetail.meeting_date}</span>
          )}
        </div>
        {step === 'reply' && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-500">
              已回复 {totalReplied}/{opinions.length}
            </span>
            <button onClick={handleReset} className="btn-ghost text-xs">
              <RefreshCw className="w-3.5 h-3.5" /> 新建任务
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* ===== 第一步：选择文档 ===== */}
      {step === 'select' && (
        <div className="panel p-5 space-y-5">
          <h2 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
            选择文档与会议信息
          </h2>

          {/* 专家意见文档 */}
          <div>
            <label className="label flex items-center gap-1">
              <FileText className="w-3.5 h-3.5" /> 专家意见文档 <span className="text-red-500">*</span>
            </label>
            <select
              value={opinionDocId ?? ''}
              onChange={e => setOpinionDocId(e.target.value ? Number(e.target.value) : null)}
              className="input w-full text-sm"
              disabled={loading}
            >
              <option value="">请选择专家意见文档...</option>
              {documents.map(d => (
                <option key={d.id} value={d.id}>
                  {d.title || d.original_filename}
                  {d.is_expert_opinion ? ' [已标记为意见]' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* 报告文档 */}
          <div>
            <label className="label flex items-center gap-1">
              <FileText className="w-3.5 h-3.5" /> 对应报告文档 <span className="text-neutral-400 font-normal">(可选)</span>
            </label>
            <select
              value={reportDocId ?? ''}
              onChange={e => setReportDocId(e.target.value ? Number(e.target.value) : null)}
              className="input w-full text-sm"
              disabled={loading}
            >
              <option value="">请选择报告文档（用于定位上下文）...</option>
              {documents.map(d => (
                <option key={d.id} value={d.id}>
                  {d.title || d.original_filename}
                  {d.is_report ? ' [已标记为报告]' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* 会议名称 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label flex items-center gap-1">
                <Tag className="w-3.5 h-3.5" /> 会议名称 <span className="text-neutral-400 font-normal">(可选)</span>
              </label>
              <input
                type="text"
                value={meetingName}
                onChange={e => setMeetingName(e.target.value)}
                placeholder="如：XX工程可行性研究报告审查会"
                className="input w-full text-sm"
              />
            </div>
            <div>
              <label className="label flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" /> 会议日期 <span className="text-neutral-400 font-normal">(可选)</span>
              </label>
              <input
                type="date"
                value={meetingDate}
                onChange={e => setMeetingDate(e.target.value)}
                className="input w-full text-sm"
              />
            </div>
          </div>

          <div className="border border-blue-100 bg-blue-50/60 rounded-md px-3 py-2.5 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700 leading-relaxed">
              选择专家意见文档后，系统将自动解析并按专业分类切分为逐条意见，再基于报告内容辅助生成回复。
            </p>
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleCreateTask}
              disabled={!opinionDocId || loading}
              className="btn-primary px-6"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" strokeWidth={1.75} />}
              创建任务并解析意见
            </button>
          </div>
        </div>
      )}

      {/* ===== 第二步：解析中 ===== */}
      {step === 'parsing' && (
        <div className="panel p-10 text-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-brand-50 flex items-center justify-center mx-auto">
            <Loader2 className="w-7 h-7 text-brand-600 animate-spin" />
          </div>
          <h2 className="text-base font-semibold text-neutral-900">正在解析专家意见...</h2>
          <p className="text-sm text-neutral-500">系统正在切分意见并进行专业分类，请稍候</p>
          <div className="max-w-sm mx-auto w-full">
            <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full transition-all duration-500"
                style={{ width: `${parseProgress}%` }}
              />
            </div>
            <p className="text-xs text-neutral-400 mt-2">{parseProgress}%</p>
          </div>
        </div>
      )}

      {/* ===== 第三步：意见列表与回复 ===== */}
      {step === 'reply' && taskDetail && (
        <div className="space-y-4">
          {/* 操作栏 */}
          <div className="panel p-4 flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-4 text-sm text-neutral-600">
              <span className="flex items-center gap-1">
                <Hash className="w-3.5 h-3.5" />
                共 <b className="text-neutral-900">{opinions.length}</b> 条意见
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5 text-green-600" />
                已回复 <b className="text-neutral-900">{totalReplied}</b> 条
              </span>
              {Object.keys(groups).length > 0 && (
                <span className="flex items-center gap-1">
                  <Tag className="w-3.5 h-3.5" />
                  {Object.keys(groups).length} 个专业
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleGenerateAll}
                disabled={generatingAll || totalReplied === opinions.length}
                className="btn-secondary text-xs"
              >
                {generatingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                {generatingAll ? '批量生成中...' : '一键生成全部回复'}
              </button>
              <button
                onClick={handleExport}
                disabled={exporting || totalReplied === 0}
                className="btn-primary text-xs px-4"
              >
                {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                导出回复表
              </button>
            </div>
          </div>

          {/* 按专业分类展示 */}
          {Object.entries(groups).map(([cat, items]) => {
            const cfg = getCategoryConfig(cat)
            const isExpanded = expandedCats[cat] ?? true
            const repliedInCat = items.filter(o => o.reply?.reply_content?.trim()).length
            return (
              <div key={cat} className={`panel overflow-hidden border ${cfg.border}`}>
                {/* 分类标题 */}
                <button
                  onClick={() => setExpandedCats(prev => ({ ...prev, [cat]: !isExpanded }))}
                  className={`w-full flex items-center justify-between px-4 py-3 ${cfg.bg} border-b ${cfg.border} transition-colors`}
                >
                  <div className="flex items-center gap-2">
                    {isExpanded
                      ? <ChevronDown className="w-4 h-4 text-neutral-500" />
                      : <ChevronRight className="w-4 h-4 text-neutral-500" />}
                    <span className={`text-sm font-semibold ${cfg.text}`}>
                      {cfg.label}
                    </span>
                    <span className={`text-xs ${cfg.text} opacity-70`}>
                      {items.length} 条意见 · {repliedInCat}/{items.length} 已回复
                    </span>
                  </div>
                </button>

                {/* 意见列表 */}
                {isExpanded && (
                  <div className="divide-y divide-neutral-100">
                    {items.map((op, idx) => {
                      const isGenerating = generatingId === op.id
                      const isSaving = savingId === op.id
                      const hasReply = !!op.reply?.reply_content?.trim()
                      const replyStatus = op.reply?.status
                      return (
                        <div key={op.id} className="p-4 hover:bg-neutral-50/30 transition-colors">
                          {/* 意见头部 */}
                          <div className="flex items-start gap-3 mb-3">
                            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-neutral-100 text-neutral-600 text-xs font-medium flex items-center justify-center">
                              {op.opinion_index || idx + 1}
                            </span>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap mb-1.5">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg.bg} ${cfg.text} border ${cfg.border}`}>
                                  {cfg.label}
                                </span>
                                {op.expert_name && (
                                  <span className="inline-flex items-center gap-1 text-xs text-neutral-600">
                                    <User className="w-3 h-3" />
                                    {op.expert_name}
                                  </span>
                                )}
                                {op.opinion_type && (
                                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-neutral-100 text-neutral-600">
                                    {op.opinion_type}
                                  </span>
                                )}
                                {op.page_number != null && (
                                  <span className="inline-flex items-center gap-1 text-xs text-neutral-500">
                                    <Hash className="w-3 h-3" /> 第{op.page_number}页
                                  </span>
                                )}
                                {op.chapter_path && (
                                  <span className="inline-flex items-center gap-1 text-xs text-neutral-500">
                                    <MapPin className="w-3 h-3" /> {op.chapter_path}
                                  </span>
                                )}
                              </div>
                              {/* 意见内容 */}
                              <p className="text-sm text-neutral-800 leading-relaxed whitespace-pre-wrap">
                                {op.content}
                              </p>
                            </div>
                          </div>

                          {/* 回复区域 */}
                          <div className="ml-10 space-y-3">
                            {/* 回复内容 */}
                            <div>
                              <label className="label flex items-center gap-1 mb-1.5">
                                <MessageSquare className="w-3.5 h-3.5" /> 回复内容
                              </label>
                              <AutoTextarea
                                value={op.reply?.reply_content || ''}
                                onChange={v => updateReplyField(op.id, 'reply_content', v)}
                                placeholder={isGenerating ? '正在生成回复...' : '点击"生成回复"或手动输入回复内容'}
                                minHeight={80}
                              />
                            </div>

                            {/* 修改情况 */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                              <div>
                                <label className="label text-xs mb-1">修改状态</label>
                                <select
                                  value={op.reply?.modify_status || ''}
                                  onChange={e => updateReplyField(op.id, 'modify_status', e.target.value)}
                                  className="input w-full text-xs py-1.5"
                                >
                                  <option value="">未选择</option>
                                  <option value="已修改">已修改</option>
                                  <option value="部分修改">部分修改</option>
                                  <option value="已说明">已说明</option>
                                  <option value="不修改">不修改</option>
                                </select>
                              </div>
                              <div>
                                <label className="label text-xs mb-1">修改位置</label>
                                <input
                                  type="text"
                                  value={op.reply?.modify_location || ''}
                                  onChange={e => updateReplyField(op.id, 'modify_location', e.target.value)}
                                  placeholder="如：第3章 3.2节"
                                  className="input w-full text-xs py-1.5"
                                />
                              </div>
                              <div>
                                <label className="label text-xs mb-1">修改页码</label>
                                <input
                                  type="text"
                                  value={op.reply?.modify_page || ''}
                                  onChange={e => updateReplyField(op.id, 'modify_page', e.target.value)}
                                  placeholder="如：P15-P16"
                                  className="input w-full text-xs py-1.5"
                                />
                              </div>
                            </div>

                            {/* 操作按钮 */}
                            <div className="flex items-center gap-2 pt-1">
                              <button
                                onClick={() => handleGenerateReply(op.id)}
                                disabled={isGenerating}
                                className="btn-primary text-xs px-3 py-1.5"
                              >
                                {isGenerating
                                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  : <Sparkles className="w-3.5 h-3.5" />}
                                {isGenerating ? '生成中...' : hasReply ? '重新生成' : '生成回复'}
                              </button>
                              {hasReply && (
                                <button
                                  onClick={() => handleSaveReply(op)}
                                  disabled={isSaving}
                                  className="btn-secondary text-xs px-3 py-1.5"
                                >
                                  {isSaving
                                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    : <Save className="w-3.5 h-3.5" />}
                                  保存
                                </button>
                              )}
                              {replyStatus === 'saved' && (
                                <span className="inline-flex items-center gap-1 text-xs text-green-600">
                                  <CheckCircle className="w-3.5 h-3.5" /> 已保存
                                </span>
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

          {/* 底部操作 */}
          <div className="panel p-4 flex items-center justify-between">
            <button onClick={handleReset} className="btn-ghost text-sm">
              <RefreshCw className="w-4 h-4" /> 新建任务
            </button>
            <button
              onClick={handleExport}
              disabled={exporting || totalReplied === 0}
              className="btn-primary px-6"
            >
              {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" strokeWidth={1.75} />}
              导出回复表
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
