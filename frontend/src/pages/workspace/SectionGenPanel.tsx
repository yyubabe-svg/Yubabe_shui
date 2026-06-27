import { useEffect, useState, useRef, useCallback, type ReactNode } from 'react'
import {
  FileText, ListOrdered, Sparkles, Download, Loader2,
  CheckCircle2, ChevronRight, ChevronDown, AlertTriangle,
  FolderOpen, Edit3, RefreshCw, ArrowRight, ArrowLeft,
  Eye, X, SkipForward, Check, Save, File,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import {
  workspaceApi,
  type SectionTemplate,
  type SectionTaskDetail,
  type SectionDraft,
  type ProjectDocument,
} from '../../api/workspace'
import StepWizard from '../../components/common/StepWizard'
import MarkdownRenderer from '../../components/MarkdownRenderer'

type Step = 'select' | 'outline' | 'generate' | 'edit' | 'export'

// 段落流式状态
interface StreamParagraph {
  paragraph_id: string
  title?: string
  level?: number
  content: string
  status: 'pending' | 'generating' | 'completed'
}

// 大纲节点
interface OutlineNode {
  id: string
  title: string
  level?: number
  children?: OutlineNode[]
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

export default function SectionGenPanel() {
  const { currentProject } = useProject()

  // ========== 步骤状态 ==========
  const [step, setStep] = useState<Step>('select')

  // ========== 模板相关 ==========
  const [templates, setTemplates] = useState<SectionTemplate[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [checkedNodes, setCheckedNodes] = useState<Set<number>>(new Set())
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  // ========== 文档相关 ==========
  const [documents, setDocuments] = useState<ProjectDocument[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [selectedDocIds, setSelectedDocIds] = useState<Set<number>>(new Set())

  // ========== 任务相关 ==========
  const [taskId, setTaskId] = useState<number | null>(null)
  const [taskDetail, setTaskDetail] = useState<SectionTaskDetail | null>(null)
  const [outline, setOutline] = useState<OutlineNode[] | null>(null)
  const [outlineText, setOutlineText] = useState('')

  // ========== 流式生成 ==========
  const [generating, setGenerating] = useState(false)
  const [streamParagraphs, setStreamParagraphs] = useState<StreamParagraph[]>([])
  const [activeParagraphId, setActiveParagraphId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // ========== 段落编辑 ==========
  const [editingDraftId, setEditingDraftId] = useState<number | null>(null)
  const [editingContent, setEditingContent] = useState('')
  const [savingDraft, setSavingDraft] = useState<number | null>(null)
  const [acceptingDraft, setAcceptingDraft] = useState<number | null>(null)
  const [skippingDraft, setSkippingDraft] = useState<number | null>(null)

  // ========== 导出 ==========
  const [exporting, setExporting] = useState(false)
  const [exportUrl, setExportUrl] = useState('')

  // ========== 通用 ==========
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // ========== 加载章节模板 ==========
  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true)
    setError('')
    try {
      const res = await workspaceApi.getSectionTemplates(currentProject?.project_type || undefined)
      setTemplates(res.items || [])
      // 默认展开第一层
      const exp: Record<number, boolean> = {}
      ;(res.items || []).forEach(t => { exp[t.id] = true })
      setExpanded(exp)
    } catch (e: any) {
      setError(e?.response?.data?.detail || '加载章节模板失败')
      setTemplates([])
    } finally {
      setTemplatesLoading(false)
    }
  }, [currentProject?.project_type])

  useEffect(() => {
    loadTemplates()
  }, [loadTemplates])

  // ========== 加载文档列表 ==========
  const loadDocuments = useCallback(async () => {
    if (!currentProject) return
    setDocumentsLoading(true)
    try {
      const res = await workspaceApi.listDocuments(currentProject.id)
      setDocuments(res.items || [])
    } catch (e: any) {
      setError(e?.response?.data?.detail || '加载文档列表失败')
      setDocuments([])
    } finally {
      setDocumentsLoading(false)
    }
  }, [currentProject])

  useEffect(() => {
    if (currentProject && step === 'select') {
      loadDocuments()
    }
  }, [currentProject, step, loadDocuments])

  // ========== 树勾选逻辑 ==========
  // 获取节点及其所有后代id
  const getAllDescendantIds = (node: SectionTemplate): number[] => {
    const ids = [node.id]
    if (node.children) {
      for (const child of node.children) {
        ids.push(...getAllDescendantIds(child))
      }
    }
    return ids
  }

  const toggleCheck = (node: SectionTemplate) => {
    setCheckedNodes(prev => {
      const next = new Set(prev)
      const descendantIds = getAllDescendantIds(node)
      const isChecked = next.has(node.id)
      if (isChecked) {
        descendantIds.forEach(id => next.delete(id))
      } else {
        descendantIds.forEach(id => next.add(id))
      }
      return next
    })
  }

  // 检查节点是否全选/半选
  const getCheckState = (node: SectionTemplate): 'checked' | 'indeterminate' | 'none' => {
    if (!node.children || node.children.length === 0) {
      return checkedNodes.has(node.id) ? 'checked' : 'none'
    }
    const childStates = node.children.map(c => getCheckState(c))
    const allChecked = childStates.every(s => s === 'checked')
    const noneChecked = childStates.every(s => s === 'none')
    if (allChecked) return 'checked'
    if (noneChecked && !checkedNodes.has(node.id)) return 'none'
    return 'indeterminate'
  }

  const toggleExpand = (id: number) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }))
  }

  // 获取选中的顶层模板id（用于template_id）
  const getSelectedTemplateId = (): number | null => {
    for (const t of templates) {
      if (checkedNodes.has(t.id)) return t.id
    }
    // 如果没有顶层被选中，找任意被选中节点的顶层祖先
    for (const checkedId of checkedNodes) {
      // 简单策略：返回第一个被选中节点
      return checkedId
    }
    return null
  }

  // ========== 步骤1 -> 步骤2：创建任务并生成大纲 ==========
  const handleGenerateOutline = async () => {
    if (!currentProject) return
    const templateId = getSelectedTemplateId()
    if (!templateId) {
      setError('请至少选择一个章节')
      return
    }
    setLoading(true)
    setError('')
    try {
      // 创建任务
      const docIds = selectedDocIds.size > 0 ? Array.from(selectedDocIds) : undefined
      const createRes = await workspaceApi.createSectionTask(currentProject.id, {
        template_id: templateId,
        document_ids: docIds,
      })
      const tid = createRes.task_id
      setTaskId(tid)

      // 生成大纲
      await workspaceApi.generateSectionOutline(tid)

      // 获取任务详情以拿到大纲
      const detail = await workspaceApi.getSectionTask(tid)
      setTaskDetail(detail)

      // 解析大纲
      if (detail.outline_json) {
        setOutline(detail.outline_json.items || detail.outline_json || null)
        // 将大纲转为文本用于编辑
        const text = outlineToText(detail.outline_json.items || detail.outline_json || [])
        setOutlineText(text)
      }

      setStep('outline')
    } catch (e: any) {
      setError(e?.response?.data?.detail || '创建任务失败')
    } finally {
      setLoading(false)
    }
  }

  // 大纲转文本（可编辑）
  const outlineToText = (nodes: OutlineNode[], depth = 0): string => {
    let text = ''
    for (const node of nodes) {
      const hashes = '#'.repeat(Math.min(node.level || depth + 1, 6))
      text += `${hashes} ${node.title}\n`
      if (node.children && node.children.length > 0) {
        text += outlineToText(node.children, depth + 1)
      }
    }
    return text
  }

  // ========== 步骤2 -> 步骤3：开始流式生成 ==========
  const handleStartStream = async () => {
    if (!taskId) return
    setStep('generate')
    setGenerating(true)
    setStreamParagraphs([])
    setActiveParagraphId(null)
    setError('')

    try {
      abortRef.current = new AbortController()
      const response = await workspaceApi.streamSectionGenerate(taskId)

      if (!response.body) throw new Error('无响应流')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // 解析SSE：按 \n\n 分割事件
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const event of events) {
          const lines = event.split('\n')
          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed.startsWith('data:')) continue
            const dataStr = trimmed.slice(5).trim()
            if (!dataStr || dataStr === '[DONE]') continue
            try {
              const evt = JSON.parse(dataStr)
              handleSSEEvent(evt)
            } catch {
              // 忽略解析错误
            }
          }
        }
      }

      setGenerating(false)

      // 生成完成后刷新任务详情，进入编辑步骤
      const detail = await workspaceApi.getSectionTask(taskId)
      setTaskDetail(detail)
      setStep('edit')
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        setError(e?.message || '生成失败，请重试')
      }
      setGenerating(false)
    }
  }

  const handleSSEEvent = (evt: any) => {
    switch (evt.type) {
      case 'paragraph_start': {
        const newPara: StreamParagraph = {
          paragraph_id: evt.paragraph_id,
          title: evt.title,
          level: evt.level,
          content: '',
          status: 'generating',
        }
        setStreamParagraphs(prev => [...prev, newPara])
        setActiveParagraphId(evt.paragraph_id)
        break
      }
      case 'token': {
        setStreamParagraphs(prev => prev.map(p =>
          p.paragraph_id === evt.paragraph_id
            ? { ...p, content: p.content + (evt.content || '') }
            : p
        ))
        break
      }
      case 'paragraph_end': {
        setStreamParagraphs(prev => prev.map(p =>
          p.paragraph_id === evt.paragraph_id
            ? { ...p, status: 'completed' as const }
            : p
        ))
        setActiveParagraphId(null)
        break
      }
      case 'done': {
        // 全部完成
        setStreamParagraphs(prev => prev.map(p => ({ ...p, status: 'completed' as const })))
        setActiveParagraphId(null)
        break
      }
      case 'error': {
        setError(evt.message || '生成出错')
        break
      }
    }
  }

  const handleStopStream = () => {
    abortRef.current?.abort()
    setGenerating(false)
  }

  // ========== 步骤4：段落操作 ==========
  const handleEditDraft = (draft: SectionDraft) => {
    setEditingDraftId(draft.id)
    setEditingContent(draft.content)
  }

  const handleSaveDraft = async (draftId: number) => {
    setSavingDraft(draftId)
    try {
      await workspaceApi.updateSectionDraft(draftId, { content: editingContent })
      // 更新本地状态
      setTaskDetail(prev => {
        if (!prev) return prev
        return {
          ...prev,
          drafts: prev.drafts.map(d =>
            d.id === draftId ? { ...d, content: editingContent } : d
          ),
        }
      })
      setEditingDraftId(null)
      setEditingContent('')
    } catch (e: any) {
      setError(e?.response?.data?.detail || '保存失败')
    } finally {
      setSavingDraft(null)
    }
  }

  const handleAcceptDraft = async (draftId: number) => {
    setAcceptingDraft(draftId)
    try {
      await workspaceApi.acceptSectionDraft(draftId)
      setTaskDetail(prev => {
        if (!prev) return prev
        return {
          ...prev,
          drafts: prev.drafts.map(d =>
            d.id === draftId ? { ...d, status: 'accepted' } : d
          ),
        }
      })
    } catch (e: any) {
      setError(e?.response?.data?.detail || '采纳失败')
    } finally {
      setAcceptingDraft(null)
    }
  }

  const handleSkipDraft = async (draftId: number) => {
    setSkippingDraft(draftId)
    try {
      // 跳过：将状态设为skipped（通过update接口）
      await workspaceApi.updateSectionDraft(draftId, { content: '' })
      setTaskDetail(prev => {
        if (!prev) return prev
        return {
          ...prev,
          drafts: prev.drafts.map(d =>
            d.id === draftId ? { ...d, status: 'skipped', content: '' } : d
          ),
        }
      })
    } catch (e: any) {
      setError(e?.response?.data?.detail || '操作失败')
    } finally {
      setSkippingDraft(null)
    }
  }

  // ========== 步骤5：导出 ==========
  const handleExport = async () => {
    if (!taskId) return
    setExporting(true)
    setError('')
    try {
      const url = workspaceApi.exportSection(taskId)
      setExportUrl(url)
      window.open(url, '_blank')
    } catch (e: any) {
      setError(e?.response?.data?.detail || '导出失败')
    } finally {
      setExporting(false)
    }
  }

  // ========== 重置 ==========
  const reset = () => {
    abortRef.current?.abort()
    setStep('select')
    setCheckedNodes(new Set())
    setSelectedDocIds(new Set())
    setTaskId(null)
    setTaskDetail(null)
    setOutline(null)
    setOutlineText('')
    setGenerating(false)
    setStreamParagraphs([])
    setActiveParagraphId(null)
    setEditingDraftId(null)
    setEditingContent('')
    setExportUrl('')
    setError('')
  }

  // ========== 渲染模板树 ==========
  const renderTemplateTree = (items: SectionTemplate[], depth = 0): ReactNode => {
    return items.map(node => {
      const hasChildren = node.children && node.children.length > 0
      const isOpen = expanded[node.id] ?? depth < 1
      const checkState = getCheckState(node)

      return (
        <div key={node.id}>
          <div
            className={`flex items-center gap-1.5 px-3 py-2 rounded text-sm transition-colors hover:bg-neutral-50`}
            style={{ paddingLeft: `${12 + depth * 16}px` }}
          >
            {hasChildren ? (
              <button
                onClick={e => { e.stopPropagation(); toggleExpand(node.id) }}
                className="text-neutral-400 hover:text-neutral-600 flex-shrink-0"
              >
                {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>
            ) : (
              <span className="w-3.5 flex-shrink-0" />
            )}
            <label className="flex items-center gap-2 cursor-pointer flex-1 min-w-0">
              <input
                type="checkbox"
                checked={checkState === 'checked'}
                ref={el => { if (el) el.indeterminate = checkState === 'indeterminate' }}
                onChange={() => toggleCheck(node)}
                className="w-3.5 h-3.5 rounded border-neutral-300 text-brand-600 focus:ring-brand-500 flex-shrink-0"
              />
              {node.level != null && node.level > 0 ? (
                <span className="text-xs font-mono text-neutral-400 flex-shrink-0">
                  {node.chapter_number}
                </span>
              ) : null}
              <ListOrdered className={`w-3.5 h-3.5 flex-shrink-0 ${hasChildren ? 'text-brand-500' : 'text-neutral-400'}`} />
              <span className={`truncate ${checkState !== 'none' ? 'text-brand-700 font-medium' : 'text-neutral-700'}`}>
                {node.title}
              </span>
              {node.description && (
                <span className="text-xs text-neutral-400 truncate ml-1 hidden md:inline">
                  {node.description}
                </span>
              )}
            </label>
          </div>
          {hasChildren && isOpen && renderTemplateTree(node.children!, depth + 1)}
        </div>
      )
    })
  }

  // ========== 渲染流式段落 ==========
  const renderStreamParagraph = (para: StreamParagraph) => {
    const isActive = para.paragraph_id === activeParagraphId
    const headingClass = para.level === 1 ? 'text-xl font-bold text-neutral-900 mt-6 mb-3' :
      para.level === 2 ? 'text-lg font-semibold text-neutral-900 mt-5 mb-2' :
      para.level === 3 ? 'text-base font-semibold text-neutral-800 mt-4 mb-2' :
      'text-sm font-medium text-neutral-700 mt-3 mb-1'

    return (
      <div key={para.paragraph_id} className={`${isActive ? 'animate-pulse-subtle' : ''}`}>
        {(para.title || para.level) && (
          <div className={`${headingClass} flex items-center gap-2`}>
            {para.title && <span>{para.title}</span>}
            {isActive && (
              <span className="inline-block w-1.5 h-5 bg-brand-500 animate-pulse rounded-sm" />
            )}
            {para.status === 'completed' && (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            )}
          </div>
        )}
        <div className="prose prose-sm max-w-none text-neutral-700 leading-relaxed whitespace-pre-wrap">
          {para.content}
          {isActive && !para.title && (
            <span className="inline-block w-1.5 h-4 bg-brand-500 animate-pulse ml-0.5 align-middle rounded-sm" />
          )}
        </div>
      </div>
    )
  }

  // ========== 获取段落状态标签 ==========
  const getDraftStatusBadge = (status: string) => {
    switch (status) {
      case 'accepted':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-green-50 text-green-700"><Check className="w-2.5 h-2.5" />已采纳</span>
      case 'completed':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700">待确认</span>
      case 'generating':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700"><Loader2 className="w-2.5 h-2.5 animate-spin" />生成中</span>
      case 'skipped':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-neutral-100 text-neutral-500">已跳过</span>
      case 'pending':
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-neutral-100 text-neutral-500">等待中</span>
    }
  }

  // ========== 步骤定义 ==========
  const steps = [
    { key: 'select', label: '选择章节', icon: FileText },
    { key: 'outline', label: '确认大纲', icon: ListOrdered },
    { key: 'generate', label: 'AI 生成', icon: Sparkles },
    { key: 'edit', label: '编辑采纳', icon: Edit3 },
    { key: 'export', label: '导出文档', icon: Download },
  ] as const

  // ========== 渲染 ==========
  return (
    <div className="space-y-6">
      <StepWizard steps={steps} activeStep={step} className="mb-6" />

      {/* 错误提示 */}
      {error && (
        <div className="border border-red-200 bg-red-50 px-4 py-3 flex items-start gap-2.5 rounded-lg">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" strokeWidth={1.75} />
          <p className="text-sm text-red-800 flex-1">{error}</p>
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ========== 步骤1：选择章节模板 & 参考文档 ========== */}
      {step === 'select' && (
        <div className="space-y-4">
          {/* 章节模板选择 */}
          <div className="panel p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
                选择要生成的章节
              </h2>
              <button
                onClick={loadTemplates}
                disabled={templatesLoading}
                className="btn-ghost text-xs flex items-center gap-1"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${templatesLoading ? 'animate-spin' : ''}`} />
                刷新
              </button>
            </div>

            {templatesLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
                <span className="ml-2 text-sm text-neutral-500">加载章节模板中...</span>
              </div>
            ) : templates.length === 0 ? (
              <div className="empty-state py-10">
                <FileText className="empty-state-icon" strokeWidth={1.5} />
                <p className="empty-state-text">暂无可用章节模板</p>
                <p className="text-xs text-neutral-400 mt-1">请联系管理员配置适用于当前项目类型的报告模板</p>
              </div>
            ) : (
              <div className="border border-neutral-200 rounded max-h-[360px] overflow-y-auto">
                {renderTemplateTree(templates)}
              </div>
            )}
            <p className="text-xs text-neutral-400 mt-2">
              已选择 {checkedNodes.size} 个章节节点
            </p>
          </div>

          {/* 参考文档选择 */}
          <div className="panel p-5">
            <h2 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
              选择参考文档
            </h2>
            <p className="text-xs text-neutral-500 mb-3">
              选择已上传的项目文档作为 AI 生成的参考资料（可多选，也可不选）
            </p>

            {documentsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-brand-500" />
                <span className="ml-2 text-sm text-neutral-500">加载文档中...</span>
              </div>
            ) : documents.length === 0 ? (
              <div className="border border-dashed border-neutral-200 rounded-lg py-6 text-center">
                <File className="w-7 h-7 text-neutral-300 mx-auto mb-2" strokeWidth={1.5} />
                <p className="text-sm text-neutral-500">当前项目暂无已上传文档</p>
                <p className="text-xs text-neutral-400 mt-1">可先去「资料管理」上传参考文档，或直接跳过生成</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {documents.map(doc => {
                  const isSelected = selectedDocIds.has(doc.id)
                  return (
                    <label
                      key={doc.id}
                      className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                        isSelected
                          ? 'border-brand-300 bg-brand-50/30'
                          : 'border-neutral-200 hover:border-neutral-300'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {
                          setSelectedDocIds(prev => {
                            const next = new Set(prev)
                            if (next.has(doc.id)) next.delete(doc.id)
                            else next.add(doc.id)
                            return next
                          })
                        }}
                        className="w-3.5 h-3.5 rounded border-neutral-300 text-brand-600 focus:ring-brand-500 flex-shrink-0"
                      />
                      <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                        <FileText className="w-4 h-4 text-blue-600" strokeWidth={1.5} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-neutral-900 truncate">{doc.title}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-neutral-400">{formatFileSize(doc.file_size)}</span>
                          {doc.total_pages && (
                            <span className="text-xs text-neutral-400">{doc.total_pages} 页</span>
                          )}
                          {doc.is_report && (
                            <span className="inline-flex items-center px-1 py-0.5 rounded text-[10px] font-medium bg-green-50 text-green-600">
                              设计报告
                            </span>
                          )}
                        </div>
                      </div>
                    </label>
                  )
                })}
              </div>
            )}
          </div>

          {/* 提示 */}
          <div className="border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-2.5 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" strokeWidth={1.75} />
            <p className="text-xs text-amber-800">
              AI 生成内容仅供参考，请结合工程实际进行校核和修改后使用。
            </p>
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleGenerateOutline}
              disabled={loading || checkedNodes.size === 0}
              className="btn-primary px-6 flex items-center gap-1.5"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" strokeWidth={1.75} />
              )}
              生成大纲
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ========== 步骤2：确认/编辑大纲 ========== */}
      {step === 'outline' && taskDetail && (
        <div className="panel p-5 space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-neutral-900 mb-1 flex items-center gap-2">
              <ListOrdered className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
              章节大纲
              <span className="text-xs font-normal text-neutral-400 ml-1">
                {taskDetail.template_title}
              </span>
            </h2>
            <p className="text-xs text-neutral-500">
              AI 已根据模板和参考文档生成写作大纲，您可以在下方编辑调整后再开始生成正文
            </p>
          </div>

          {/* 大纲预览 */}
          {outline && (
            <div className="border border-neutral-200 rounded-lg p-4 bg-neutral-50/50 mb-4">
              <div className="flex items-center gap-2 mb-2">
                <Eye className="w-3.5 h-3.5 text-neutral-400" />
                <span className="text-xs font-medium text-neutral-500">大纲结构预览</span>
              </div>
              <div className="prose prose-sm max-w-none">
                <MarkdownRenderer content={outlineText} />
              </div>
            </div>
          )}

          {/* 大纲编辑 */}
          <div>
            <label className="text-xs font-medium text-neutral-600 mb-1.5 block">
              大纲编辑（Markdown 格式，# 号表示层级）
            </label>
            <textarea
              value={outlineText}
              onChange={e => setOutlineText(e.target.value)}
              rows={12}
              className="input font-mono text-sm"
              placeholder="# 一级标题\n## 二级标题\n### 三级标题"
            />
          </div>

          <div className="border border-blue-200 bg-blue-50 px-4 py-3 flex items-start gap-2.5 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" strokeWidth={1.75} />
            <p className="text-xs text-blue-800">
              确认大纲后，AI 将按章节顺序逐段生成正文内容，生成过程中您可以实时查看进度。
            </p>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep('select')} className="btn-ghost text-sm flex items-center gap-1">
              <ArrowLeft className="w-4 h-4" />
              返回
            </button>
            <button
              onClick={handleStartStream}
              className="btn-primary px-6 flex items-center gap-1.5"
            >
              <Sparkles className="w-4 h-4" strokeWidth={1.75} />
              开始生成正文
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ========== 步骤3：流式生成 ========== */}
      {step === 'generate' && (
        <div className="panel p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
              {generating ? (
                <Loader2 className="w-4 h-4 text-brand-600 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-green-600" />
              )}
              {taskDetail?.template_title || '正在生成章节内容'}
            </h2>
            {generating && (
              <button onClick={handleStopStream} className="btn-ghost text-xs text-red-600">
                停止生成
              </button>
            )}
          </div>

          <div className="border border-neutral-200 rounded-lg p-6 min-h-[400px] max-h-[600px] overflow-y-auto bg-white">
            {streamParagraphs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-neutral-400">
                <Sparkles className="w-8 h-8 mb-3 animate-pulse" strokeWidth={1.5} />
                <p className="text-sm">AI 正在准备生成内容...</p>
              </div>
            ) : (
              <div className="space-y-1">
                {streamParagraphs.map(renderStreamParagraph)}
              </div>
            )}
          </div>

          {!generating && streamParagraphs.length > 0 && (
            <div className="flex justify-end mt-4">
              <button
                onClick={async () => {
                  if (taskId) {
                    const detail = await workspaceApi.getSectionTask(taskId)
                    setTaskDetail(detail)
                  }
                  setStep('edit')
                }}
                className="btn-primary px-6 flex items-center gap-1.5"
              >
                下一步：编辑审阅
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* ========== 步骤4：编辑/采纳段落 ========== */}
      {step === 'edit' && taskDetail && (
        <div className="space-y-4">
          <div className="panel p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
                编辑与审阅
                <span className="text-xs font-normal text-neutral-400 ml-1">
                  {taskDetail.template_title}
                </span>
              </h2>
              <div className="flex items-center gap-3 text-xs text-neutral-500">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500" />
                  已采纳 {taskDetail.drafts.filter(d => d.status === 'accepted').length}
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  待确认 {taskDetail.drafts.filter(d => d.status === 'completed').length}
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-neutral-300" />
                  已跳过 {taskDetail.drafts.filter(d => d.status === 'skipped').length}
                </span>
                <span>/ 共 {taskDetail.drafts.length} 段</span>
              </div>
            </div>

            <div className="space-y-3">
              {taskDetail.drafts
                .slice()
                .sort((a, b) => a.sort_order - b.sort_order)
                .map((draft) => {
                  const isEditing = editingDraftId === draft.id
                  const isHeading = draft.paragraph_type === 'heading' || draft.level != null

                  return (
                    <div
                      key={draft.id}
                      className={`border rounded-lg p-4 transition-colors ${
                        draft.status === 'accepted' ? 'border-green-200 bg-green-50/20' :
                        draft.status === 'skipped' ? 'border-neutral-200 bg-neutral-50 opacity-60' :
                        'border-neutral-200 bg-white hover:border-neutral-300'
                      }`}
                    >
                      {/* 段落头部 */}
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2 min-w-0">
                          {isHeading ? (
                            <span className="text-sm font-semibold text-neutral-800 truncate">
                              {draft.content.split('\n')[0]?.replace(/^#+\s*/, '') || `段落 ${draft.sort_order + 1}`}
                            </span>
                          ) : (
                            <span className="text-xs text-neutral-400">
                              段落 {draft.sort_order + 1}
                            </span>
                          )}
                          {getDraftStatusBadge(draft.status)}
                        </div>
                        {draft.status !== 'skipped' && !isEditing && (
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <button
                              onClick={() => handleEditDraft(draft)}
                              className="p-1.5 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded transition-colors"
                              title="编辑"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                            </button>
                            {draft.status === 'completed' && (
                              <>
                                <button
                                  onClick={() => handleAcceptDraft(draft.id)}
                                  disabled={acceptingDraft === draft.id}
                                  className="p-1.5 text-neutral-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors disabled:opacity-50"
                                  title="采纳"
                                >
                                  {acceptingDraft === draft.id ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  ) : (
                                    <Check className="w-3.5 h-3.5" />
                                  )}
                                </button>
                                <button
                                  onClick={() => handleSkipDraft(draft.id)}
                                  disabled={skippingDraft === draft.id}
                                  className="p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded transition-colors disabled:opacity-50"
                                  title="跳过"
                                >
                                  <SkipForward className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </div>

                      {/* 段落内容 */}
                      {draft.status === 'skipped' ? (
                        <p className="text-sm text-neutral-400 italic">此段已跳过，不纳入最终文档</p>
                      ) : isEditing ? (
                        <div className="space-y-2">
                          <textarea
                            value={editingContent}
                            onChange={e => setEditingContent(e.target.value)}
                            rows={Math.max(4, Math.ceil(editingContent.length / 80))}
                            className="input font-mono text-sm w-full"
                            placeholder="输入 Markdown 内容..."
                          />
                          <div className="flex items-center gap-2 justify-end">
                            <button
                              onClick={() => { setEditingDraftId(null); setEditingContent('') }}
                              className="btn-ghost text-xs"
                            >
                              取消
                            </button>
                            <button
                              onClick={() => handleSaveDraft(draft.id)}
                              disabled={savingDraft === draft.id}
                              className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1"
                            >
                              {savingDraft === draft.id ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                <Save className="w-3 h-3" />
                              )}
                              保存
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="prose prose-sm max-w-none text-neutral-700 leading-relaxed">
                          <MarkdownRenderer content={draft.content} />
                        </div>
                      )}
                    </div>
                  )
                })}
            </div>
          </div>

          <div className="flex justify-between">
            <button onClick={reset} className="btn-ghost text-sm flex items-center gap-1">
              <RefreshCw className="w-4 h-4" />
              重新生成
            </button>
            <button
              onClick={() => setStep('export')}
              className="btn-primary px-6 flex items-center gap-1.5"
            >
              进入导出
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ========== 步骤5：导出 ========== */}
      {step === 'export' && taskDetail && (
        <div className="max-w-xl mx-auto">
          <div className="panel px-8 py-12 text-center">
            <div className="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-5">
              <CheckCircle2 className="w-8 h-8 text-green-600" strokeWidth={1.5} />
            </div>
            <h2 className="text-lg font-semibold text-neutral-900 mb-2">章节内容已就绪</h2>
            <p className="text-sm text-neutral-500 mb-1">{taskDetail.template_title}</p>
            {taskDetail.output_filename && (
              <p className="text-xs text-neutral-400 mb-6">{taskDetail.output_filename}</p>
            )}

            {/* 统计 */}
            <div className="flex items-center justify-center gap-4 mb-6 text-xs">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-neutral-500">
                  已采纳 {taskDetail.drafts.filter(d => d.status === 'accepted').length} 段
                </span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span className="text-neutral-500">
                  待确认 {taskDetail.drafts.filter(d => d.status === 'completed').length} 段
                </span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-neutral-300" />
                <span className="text-neutral-500">
                  共 {taskDetail.drafts.length} 段
                </span>
              </span>
            </div>

            {exportUrl && (
              <div className="border border-green-200 bg-green-50 px-4 py-3 rounded-lg mb-4 text-left">
                <p className="text-xs text-green-800 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  导出已就绪，如浏览器未自动下载，请点击下方按钮
                </p>
              </div>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={() => setStep('edit')}
                className="btn-secondary flex items-center gap-1.5"
              >
                <ArrowLeft className="w-4 h-4" />
                返回编辑
              </button>
              <button onClick={reset} className="btn-secondary flex items-center gap-1.5">
                <RefreshCw className="w-4 h-4" strokeWidth={1.75} />
                生成其他章节
              </button>
              {taskId && (
                <button
                  onClick={handleExport}
                  disabled={exporting}
                  className="btn-primary px-6 flex items-center gap-1.5"
                >
                  {exporting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" strokeWidth={1.75} />
                  )}
                  导出 Word 文档
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
