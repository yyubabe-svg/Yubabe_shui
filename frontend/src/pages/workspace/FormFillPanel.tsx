import { useEffect, useState, useRef, useCallback } from 'react'
import {
  FileSpreadsheet, CheckCircle2, Download, Loader2,
  ChevronRight, AlertTriangle, FileText,
  FolderOpen, RefreshCw, Edit3, Sparkles, ArrowRight,
  ArrowLeft, Info, X,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import {
  workspaceApi,
  type FormTemplate,
  type FormFillTaskDetail,
  type ProjectDocument,
} from '../../api/workspace'
import StepWizard from '../../components/common/StepWizard'

type Step = 'select-template' | 'select-document' | 'extract' | 'confirm' | 'download'

// 置信度颜色工具
function getConfidenceColor(confidence?: number): string {
  if (confidence === undefined || confidence === null) return 'bg-neutral-100 text-neutral-500 border-neutral-200'
  if (confidence > 0.8) return 'bg-green-50 text-green-700 border-green-200'
  if (confidence >= 0.5) return 'bg-amber-50 text-amber-700 border-amber-200'
  return 'bg-red-50 text-red-700 border-red-200'
}

function getConfidenceLabel(confidence?: number): string {
  if (confidence === undefined || confidence === null) return '未提取'
  if (confidence > 0.8) return '高置信度'
  if (confidence >= 0.5) return '中置信度'
  return '低置信度'
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

export default function FormFillPanel() {
  const { currentProject } = useProject()

  // 步骤状态
  const [step, setStep] = useState<Step>('select-template')

  // 模板相关
  const [templates, setTemplates] = useState<FormTemplate[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<FormTemplate | null>(null)

  // 文档相关
  const [documents, setDocuments] = useState<ProjectDocument[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null)

  // 任务相关
  const [taskId, setTaskId] = useState<number | null>(null)
  const [taskDetail, setTaskDetail] = useState<FormFillTaskDetail | null>(null)
  const [extractProgress, setExtractProgress] = useState(0)

  // 字段编辑
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({})

  // 填充生成
  const [filling, setFilling] = useState(false)
  const [outputFile, setOutputFile] = useState('')

  // 通用状态
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 轮询定时器
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ========== 加载模板列表 ==========
  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true)
    setError('')
    try {
      const projectType = currentProject?.project_type
      const res = await workspaceApi.listFormTemplates(projectType || undefined)
      setTemplates(res.items || [])
    } catch (e: any) {
      setError(e?.response?.data?.detail || '加载模板列表失败')
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

  // ========== 轮询任务状态 ==========
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  const pollTask = useCallback(async (tid: number) => {
    try {
      const detail = await workspaceApi.getFormTask(tid)
      setTaskDetail(detail)
      setExtractProgress(detail.progress || 0)

      if (detail.status === 'completed' || detail.status === 'fields_extracted') {
        stopPolling()
        // 将提取的字段填入 fieldValues
        const values: Record<string, string> = {}
        detail.fields.forEach(f => {
          values[f.field_key] = f.confirmed_value ?? f.extracted_value ?? ''
        })
        setFieldValues(values)
        setStep('confirm')
      } else if (detail.status === 'failed' || detail.status === 'error') {
        stopPolling()
        setError(detail.error_message || '字段提取失败')
      }
    } catch (e: any) {
      stopPolling()
      setError(e?.response?.data?.detail || '获取任务状态失败')
    }
  }, [stopPolling])

  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  // ========== 步骤1：选择模板后进入步骤2 ==========
  const handleSelectTemplate = (tpl: FormTemplate) => {
    setSelectedTemplate(tpl)
    setError('')
    loadDocuments()
    setStep('select-document')
  }

  // ========== 步骤2：选择文档（跳过也可以），创建任务并开始提取 ==========
  const handleStartExtract = async () => {
    if (!currentProject || !selectedTemplate) return
    setLoading(true)
    setError('')
    try {
      // 创建任务
      const createData: { template_id: number; document_id?: number } = {
        template_id: selectedTemplate.id,
      }
      if (selectedDocumentId !== null) {
        createData.document_id = selectedDocumentId
      }
      const createRes = await workspaceApi.createFormTask(currentProject.id, createData)
      const tid = createRes.task_id
      setTaskId(tid)

      // 开始提取
      setExtractProgress(0)
      setStep('extract')
      await workspaceApi.extractFormFields(tid)

      // 开始轮询
      pollTimerRef.current = setInterval(() => pollTask(tid), 2000)
      // 立即轮询一次
      pollTask(tid)
    } catch (e: any) {
      setError(e?.response?.data?.detail || '创建提取任务失败')
    } finally {
      setLoading(false)
    }
  }

  // ========== 步骤4：更新字段值 ==========
  const updateFieldValue = (key: string, value: string) => {
    setFieldValues(prev => ({ ...prev, [key]: value }))
  }

  // ========== 步骤5：提交字段并填充模板 ==========
  const handleFillTemplate = async () => {
    if (!taskId) return
    setFilling(true)
    setError('')
    try {
      // 先更新字段
      await workspaceApi.updateFormFields(taskId, fieldValues)
      // 再填充模板
      const res = await workspaceApi.fillFormTemplate(taskId)
      setOutputFile(res.output_file || '')
      setStep('download')
    } catch (e: any) {
      setError(e?.response?.data?.detail || '填充模板失败')
    } finally {
      setFilling(false)
    }
  }

  // ========== 重置 ==========
  const reset = () => {
    stopPolling()
    setStep('select-template')
    setSelectedTemplate(null)
    setSelectedDocumentId(null)
    setTaskId(null)
    setTaskDetail(null)
    setExtractProgress(0)
    setFieldValues({})
    setFilling(false)
    setOutputFile('')
    setError('')
  }

  // 步骤导航定义
  const steps = [
    { key: 'select-template', label: '选择模板', icon: FileSpreadsheet },
    { key: 'select-document', label: '选择文档', icon: FolderOpen },
    { key: 'extract', label: '提取字段', icon: Sparkles },
    { key: 'confirm', label: '确认信息', icon: Edit3 },
    { key: 'download', label: '下载文档', icon: Download },
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

      {/* ========== 步骤1：选择表单模板 ========== */}
      {step === 'select-template' && (
        <div className="panel p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
              选择表单模板
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
              <span className="ml-2 text-sm text-neutral-500">加载模板中...</span>
            </div>
          ) : templates.length === 0 ? (
            <div className="empty-state py-10">
              <FileSpreadsheet className="empty-state-icon" strokeWidth={1.5} />
              <p className="empty-state-text">暂无可用表单模板</p>
              <p className="text-xs text-neutral-400 mt-1">请联系管理员配置适用于当前项目类型的模板</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {templates.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleSelectTemplate(tpl)}
                  className="panel p-4 text-left hover:border-brand-300 hover:bg-brand-50/20 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-green-50 flex items-center justify-center flex-shrink-0">
                      <FileSpreadsheet className="w-5 h-5 text-green-600" strokeWidth={1.5} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-neutral-900 truncate group-hover:text-brand-700">
                        {tpl.template_name}
                      </p>
                      {tpl.template_code && (
                        <p className="text-xs text-neutral-500 font-mono">{tpl.template_code}</p>
                      )}
                      {tpl.description && (
                        <p className="text-xs text-neutral-500 mt-1 line-clamp-2">{tpl.description}</p>
                      )}
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-neutral-100 text-neutral-600">
                          {tpl.field_count} 个字段
                        </span>
                        {tpl.version && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-600">
                            v{tpl.version}
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-neutral-400 flex-shrink-0 group-hover:text-brand-500 transition-colors" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========== 步骤2：选择参考文档 ========== */}
      {step === 'select-document' && selectedTemplate && (
        <div className="panel p-5">
          <h2 className="text-sm font-semibold text-neutral-900 mb-1 flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
            选择参考文档
          </h2>
          <p className="text-xs text-neutral-500 mb-4">
            已选模板：<span className="font-medium text-neutral-700">{selectedTemplate.template_name}</span>
            （{selectedTemplate.field_count} 个字段）
          </p>
          <p className="text-sm text-neutral-600 mb-4">
            选择一份已上传的项目文档作为字段提取的数据来源。也可以跳过此步骤，后续手动填写所有字段。
          </p>

          {documentsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-brand-500" />
              <span className="ml-2 text-sm text-neutral-500">加载文档中...</span>
            </div>
          ) : documents.length === 0 ? (
            <div className="border border-dashed border-neutral-200 rounded-lg py-8 text-center">
              <FileText className="w-8 h-8 text-neutral-300 mx-auto mb-2" strokeWidth={1.5} />
              <p className="text-sm text-neutral-500">当前项目暂无已上传文档</p>
              <p className="text-xs text-neutral-400 mt-1">您可以跳过此步骤直接开始，或先去「资料管理」上传文档</p>
            </div>
          ) : (
            <div className="space-y-2 mb-4">
              {/* 不选择文档的选项 */}
              <button
                onClick={() => setSelectedDocumentId(null)}
                className={`w-full panel p-3 text-left flex items-center gap-3 transition-colors ${
                  selectedDocumentId === null
                    ? 'border-brand-300 bg-brand-50/30'
                    : 'hover:border-neutral-300'
                }`}
              >
                <div className="w-9 h-9 rounded-lg bg-neutral-50 flex items-center justify-center flex-shrink-0">
                  <Edit3 className="w-4 h-4 text-neutral-500" strokeWidth={1.5} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-neutral-700">手动填写（不使用文档提取）</p>
                  <p className="text-xs text-neutral-400">跳过自动提取，后续手动输入所有字段值</p>
                </div>
                {selectedDocumentId === null && (
                  <CheckCircle2 className="w-5 h-5 text-brand-600 flex-shrink-0" />
                )}
              </button>

              {documents.map(doc => (
                <button
                  key={doc.id}
                  onClick={() => setSelectedDocumentId(doc.id)}
                  className={`w-full panel p-3 text-left flex items-center gap-3 transition-colors ${
                    selectedDocumentId === doc.id
                      ? 'border-brand-300 bg-brand-50/30'
                      : 'hover:border-neutral-300'
                  }`}
                >
                  <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
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
                      {doc.parse_status !== 'completed' && (
                        <span className="inline-flex items-center px-1 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-600">
                          解析中
                        </span>
                      )}
                    </div>
                  </div>
                  {selectedDocumentId === doc.id && (
                    <CheckCircle2 className="w-5 h-5 text-brand-600 flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>
          )}

          <div className="flex justify-between">
            <button onClick={() => setStep('select-template')} className="btn-ghost text-sm flex items-center gap-1">
              <ArrowLeft className="w-4 h-4" />
              返回
            </button>
            <button
              onClick={handleStartExtract}
              disabled={loading}
              className="btn-primary px-6 flex items-center gap-1.5"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" strokeWidth={1.75} />
              )}
              {selectedDocumentId === null ? '手动创建任务' : '开始智能提取'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ========== 步骤3：自动提取字段（显示进度） ========== */}
      {step === 'extract' && selectedTemplate && (
        <div className="panel p-5">
          <h2 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
            正在智能提取字段
          </h2>
          <p className="text-sm text-neutral-500 mb-6">
            模板：<span className="font-medium text-neutral-700">{selectedTemplate.template_name}</span>
          </p>

          <div className="max-w-md mx-auto py-8">
            <div className="flex items-center justify-center mb-6">
              <div className="relative">
                <Loader2 className="w-16 h-16 animate-spin text-brand-500" strokeWidth={1} />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-bold text-brand-700">{extractProgress}%</span>
                </div>
              </div>
            </div>

            <div className="w-full bg-neutral-100 rounded-full h-2 mb-4">
              <div
                className="bg-brand-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${extractProgress}%` }}
              />
            </div>

            <p className="text-center text-sm text-neutral-500">
              {extractProgress < 30 && '正在分析文档结构...'}
              {extractProgress >= 30 && extractProgress < 60 && '正在识别关键字段...'}
              {extractProgress >= 60 && extractProgress < 90 && '正在匹配字段值...'}
              {extractProgress >= 90 && '即将完成...'}
            </p>
          </div>

          <div className="border border-blue-200 bg-blue-50 px-4 py-3 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" strokeWidth={1.75} />
            <p className="text-xs text-blue-800">
              AI 正在从参考文档中自动识别和提取表单字段，提取完成后您可以在下一步逐一确认和修改。
            </p>
          </div>
        </div>
      )}

      {/* ========== 步骤4：确认字段值 ========== */}
      {step === 'confirm' && taskDetail && (
        <div className="panel p-5">
          <h2 className="text-sm font-semibold text-neutral-900 mb-1 flex items-center gap-2">
            <Edit3 className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
            确认填报信息
            <span className="text-xs font-normal text-neutral-400 ml-1">
              共 {taskDetail.fields.length} 个字段
            </span>
          </h2>
          <p className="text-xs text-neutral-500 mb-4">
            请检查 AI 提取的字段值，必要时手动修改。低置信度字段请重点核对。
          </p>

          {/* 置信度图例 */}
          <div className="flex items-center gap-3 mb-4 text-xs">
            <span className="text-neutral-400">置信度：</span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
              <span className="text-green-700">高 {'>'} 0.8</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span className="text-amber-700">中 0.5~0.8</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
              <span className="text-red-700">低 {'<'} 0.5</span>
            </span>
          </div>

          <div className="space-y-3">
            {taskDetail.fields.map(field => {
              const confidence = field.confidence
              const confColor = getConfidenceColor(confidence)
              const confLabel = getConfidenceLabel(confidence)
              const currentValue = fieldValues[field.field_key] ?? ''

              return (
                <div key={field.id} className="border border-neutral-200 rounded-lg p-4 hover:border-neutral-300 transition-colors">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="min-w-0 flex-1">
                      <label className="text-sm font-medium text-neutral-800 flex items-center gap-1.5">
                        {field.field_label}
                        {field.required && <span className="text-red-500">*</span>}
                        <span className="text-xs text-neutral-400 font-mono font-normal">
                          {field.field_key}
                        </span>
                      </label>
                    </div>
                    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${confColor} flex-shrink-0`}>
                      {confLabel}
                      {confidence !== undefined && (
                        <span className="ml-1">{(confidence * 100).toFixed(0)}%</span>
                      )}
                    </span>
                  </div>

                  {/* 来源位置 */}
                  {(field.source_page || field.source_section) && (
                    <div className="flex items-center gap-2 mb-2 text-xs text-neutral-400">
                      <Info className="w-3 h-3" strokeWidth={1.5} />
                      <span>
                        来源：
                        {field.source_section && <span>{field.source_section}</span>}
                        {field.source_page && <span> · 第 {field.source_page} 页</span>}
                      </span>
                    </div>
                  )}

                  {/* 原文片段 */}
                  {field.source_text && (
                    <div className="bg-neutral-50 border-l-2 border-neutral-200 px-3 py-1.5 mb-2 text-xs text-neutral-500 italic">
                      "{field.source_text.length > 120 ? field.source_text.slice(0, 120) + '...' : field.source_text}"
                    </div>
                  )}

                  {/* 输入框 */}
                  {field.field_type === 'textarea' ? (
                    <textarea
                      value={currentValue}
                      onChange={e => updateFieldValue(field.field_key, e.target.value)}
                      rows={2}
                      className="input"
                      placeholder={`请输入${field.field_label}`}
                    />
                  ) : field.field_type === 'select' ? (
                    <input
                      type="text"
                      value={currentValue}
                      onChange={e => updateFieldValue(field.field_key, e.target.value)}
                      className="input"
                      placeholder={`请输入${field.field_label}`}
                      list={`options-${field.field_key}`}
                    />
                  ) : (
                    <input
                      type={field.field_type === 'number' ? 'number' : field.field_type === 'date' ? 'date' : 'text'}
                      value={currentValue}
                      onChange={e => updateFieldValue(field.field_key, e.target.value)}
                      className={`input ${confidence !== undefined && confidence < 0.5 ? 'border-red-200 focus:border-red-400' : ''}`}
                      placeholder={`请输入${field.field_label}`}
                    />
                  )}
                </div>
              )
            })}
          </div>

          <div className="flex justify-between mt-6">
            <button onClick={reset} className="btn-ghost text-sm flex items-center gap-1">
              <ArrowLeft className="w-4 h-4" />
              重新开始
            </button>
            <button
              onClick={handleFillTemplate}
              disabled={filling}
              className="btn-primary px-6 flex items-center gap-1.5"
            >
              {filling ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileSpreadsheet className="w-4 h-4" strokeWidth={1.75} />
              )}
              确认并生成文档
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ========== 步骤5（内嵌在fill步骤显示过渡）：填充中 → 步骤6：下载 ========== */}
      {step === 'download' && taskDetail && (
        <div className="max-w-xl mx-auto">
          <div className="panel px-8 py-12 text-center">
            <div className="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-5">
              <CheckCircle2 className="w-8 h-8 text-green-600" strokeWidth={1.5} />
            </div>
            <h2 className="text-lg font-semibold text-neutral-900 mb-2">文档生成完成</h2>
            <p className="text-sm text-neutral-500 mb-1">{taskDetail.template_name}</p>
            {outputFile && (
              <p className="text-xs text-neutral-400 mb-6">{outputFile}</p>
            )}

            {/* 字段统计 */}
            <div className="flex items-center justify-center gap-4 mb-6 text-xs">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-neutral-500">
                  {taskDetail.fields.filter(f => (f.confidence ?? 0) > 0.8).length} 高置信度
                </span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span className="text-neutral-500">
                  {taskDetail.fields.filter(f => (f.confidence ?? 0) >= 0.5 && (f.confidence ?? 0) <= 0.8).length} 中置信度
                </span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-neutral-500">
                  {taskDetail.fields.filter(f => (f.confidence ?? 0) < 0.5).length} 低置信度
                </span>
              </span>
            </div>

            <div className="flex gap-3 justify-center">
              <button onClick={reset} className="btn-secondary flex items-center gap-1.5">
                <RefreshCw className="w-4 h-4" strokeWidth={1.75} />
                继续填报
              </button>
              {taskId && (
                <a
                  href={workspaceApi.downloadFormResult(taskId)}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-primary px-6 flex items-center gap-1.5"
                >
                  <Download className="w-4 h-4" strokeWidth={1.75} />
                  下载 Word 文档
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
