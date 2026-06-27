import { useState, useRef } from 'react'
import {
  Upload,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Download,
  RefreshCw,
  FileText,
  Building2,
  Users,
  ClipboardList,
  ChevronLeft,
  Loader2,
  Crown,
  Lock,
} from 'lucide-react'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'

interface ProjectInfo {
  project_name: string
  project_code: string
  feature_code: string
  design_stage: string
  report_date?: string
  client?: string
  department: string
  work_scope?: string
  engineering_overview?: string
  design_basis?: string
  technical_points?: string
  risk_points?: string
  customer_requirements?: string
  external_resources?: string
  quality_level: string
  project_grade?: string
  building_level?: string
  flood_standard?: string
  drainage_standard?: string
  involved_majors: string[]
  excluded_majors: string[]
  applicable_codes: Array<{ name: string; code: string }>
  design_review_method: string
  design_verification_method: string
  design_confirmation_method: string
}

interface GenerateResult {
  task_id: string
  status: string
  project_info: ProjectInfo
  output_file?: string
  download_url?: string
  message?: string
  warnings: string[]
}

const ALL_MAJORS = [
  '工程测量', '工程地质', '水文', '规划/节水', '水工建筑物',
  '土建/管理/安全', '水机/暖通', '金属结构', '电气一次', '电气二次',
  '信息化', '消防', '施工/节能', '环境保护', '水土保持',
  '造价', '经济评价', '水文化', '其他专业'
]

const DESIGN_STAGES = ['初步设计', '可行性研究', '实施方案']
const QUALITY_LEVELS = ['A级', 'B级', 'C级']

export default function ISO() {
  const { user, openUpgrade, refreshUsage } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<GenerateResult | null>(null)
  const [activeStep, setActiveStep] = useState<'upload' | 'edit' | 'download'>('upload')
  const [editedInfo, setEditedInfo] = useState<ProjectInfo | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (!user) return null

  const isoRemaining = user.is_pro ? 999999 : Math.max(0, user.iso_free_limit - user.iso_used_count)
  const isoDisabled = !user.is_pro && isoRemaining <= 0

  const steps = [
    { key: 'upload', label: '上传报告', icon: Upload },
    { key: 'edit', label: '确认信息', icon: ClipboardList },
    { key: 'download', label: '下载文档', icon: Download },
  ] as const

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setError('')
      setFile(f)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    setError('')
    const f = e.dataTransfer.files[0]
    if (f && /\.(docx|doc)$/i.test(f.name)) setFile(f)
  }

  const handleGenerate = async () => {
    if (!file) return
    if (isoDisabled) {
      openUpgrade(`ISO文档免费体验次数已用完（${user.iso_free_limit}次），升级Pro无限使用`)
      return
    }
    setUploading(true)
    setError('')
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data } = await api.post('/iso/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      })
      setResult(data)
      setEditedInfo(data.project_info)
      setActiveStep('edit')
      refreshUsage()
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(detail || '文档生成失败，请重试')
      if (detail?.includes('升级') || detail?.includes('用完')) {
        openUpgrade(detail)
      }
    } finally {
      setUploading(false)
    }
  }

  const handleConfirm = async () => {
    if (!result || !editedInfo) return
    try {
      await api.post('/iso/fill', { task_id: result.task_id, project_info: editedInfo })
      setResult({ ...result, project_info: editedInfo })
      setActiveStep('download')
    } catch {
      setError('文档更新失败，请重试')
    }
  }

  const handleDownload = () => {
    if (result?.download_url) window.open(`/api${result.download_url}`, '_blank')
  }

  const updateField = <K extends keyof ProjectInfo>(field: K, value: ProjectInfo[K]) => {
    if (!editedInfo) return
    setEditedInfo({ ...editedInfo, [field]: value })
  }

  const toggleMajor = (major: string) => {
    if (!editedInfo) return
    const isInvolved = editedInfo.involved_majors.includes(major)
    setEditedInfo({
      ...editedInfo,
      involved_majors: isInvolved
        ? editedInfo.involved_majors.filter(m => m !== major)
        : [...editedInfo.involved_majors.filter(m => m !== major), major],
      excluded_majors: isInvolved
        ? [...editedInfo.excluded_majors.filter(m => m !== major), major]
        : editedInfo.excluded_majors.filter(m => m !== major),
    })
  }

  const reset = () => {
    setFile(null); setResult(null); setEditedInfo(null); setActiveStep('upload'); setError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const currentStepIdx = steps.findIndex(s => s.key === activeStep)

  // 免费用户次数用完显示升级门
  if (isoDisabled && activeStep === 'upload') {
    return (
      <div className="page-container max-w-2xl">
        <div className="page-header">
          <h1>ISO 管理体系文档</h1>
          <p>上传项目设计报告，自动填写管理体系附表（设计部分 TY01-TY04）</p>
        </div>
        <div className="border border-neutral-200 bg-white px-8 py-16 text-center">
          <div className="w-14 h-14 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-5">
            <Lock className="w-7 h-7 text-amber-500" strokeWidth={1.5} />
          </div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-2">免费体验次数已用完</h2>
          <p className="text-sm text-neutral-500 mb-1 max-w-sm mx-auto">
            免费版可体验 {user.iso_free_limit} 次ISO文档自动填写，升级 Pro 版无限使用
          </p>
          <p className="text-xs text-neutral-400 mb-6">
            TY01-TY04 全套表单 · 智能提取工程信息 · 自动勾选专业配置
          </p>
          <button onClick={() => openUpgrade('ISO文档免费体验次数已用完，升级Pro无限使用')} className="btn-primary">
            <Crown className="w-4 h-4" strokeWidth={1.75} />
            升级 Pro 解锁
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header flex items-start justify-between">
        <div>
          <h1>ISO 管理体系文档</h1>
          <p>上传项目设计报告，自动填写管理体系附表（设计部分 TY01-TY04）</p>
        </div>
        <div className="flex items-center gap-3">
          {!user.is_pro && (
            <div className="text-xs text-neutral-500 bg-neutral-50 border border-neutral-200 px-3 py-1.5 rounded">
              免费体验剩余 <span className={`font-semibold ${isoRemaining <= 1 ? 'text-warning' : 'text-neutral-700'}`}>{isoRemaining}</span> 次
            </div>
          )}
          {user.is_pro && (
            <div className="text-xs text-brand-600 bg-brand-50 border border-brand-100 px-3 py-1.5 rounded flex items-center gap-1">
              <Crown className="w-3 h-3" strokeWidth={2} />
              Pro 无限次
            </div>
          )}
        </div>
      </div>

      {/* 步骤指示器 - 极简线条式 */}
      <div className="flex items-center mb-8">
        {steps.map((step, i) => {
          const Icon = step.icon
          const isActive = activeStep === step.key
          const isDone = currentStepIdx > i
          return (
            <div key={step.key} className="flex items-center flex-1 last:flex-none">
              <div className="flex items-center gap-2">
                <div className={`step-dot ${
                  isDone ? 'bg-success text-white' :
                  isActive ? 'bg-brand-600 text-white' :
                  'bg-neutral-100 text-neutral-400'
                }`}>
                  {isDone ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-3.5 h-3.5" />}
                </div>
                <span className={`text-sm ${isActive ? 'text-neutral-900 font-medium' : isDone ? 'text-success' : 'text-neutral-400'}`}>
                  {step.label}
                </span>
              </div>
              {i < steps.length - 1 && (
                <div className={`step-line ${isDone ? 'bg-success' : 'bg-neutral-200'}`} />
              )}
            </div>
          )
        })}
      </div>

      {/* 步骤1：上传 */}
      {activeStep === 'upload' && (
        <div className="max-w-2xl">
          <div
            className={`border border-dashed bg-white px-8 py-12 text-center cursor-pointer transition-colors mb-5 ${
              isDragging ? 'border-brand-500 bg-brand-50/30' : 'border-neutral-300 hover:border-neutral-400'
            }`}
            onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input ref={fileInputRef} type="file" accept=".docx,.doc" className="hidden" onChange={handleFileSelect} />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileSpreadsheet className="w-8 h-8 text-brand-600" strokeWidth={1.5} />
                <div className="text-left">
                  <p className="text-sm font-medium text-neutral-900">{file.name}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">Word 文档</p>
                </div>
              </div>
            ) : (
              <>
                <Upload className="w-10 h-10 text-neutral-300 mx-auto mb-3" strokeWidth={1.5} />
                <p className="text-sm text-neutral-700 mb-1">点击或拖拽上传项目设计报告</p>
                <p className="text-xs text-neutral-400">支持 Word 格式（.docx / .doc）</p>
              </>
            )}
          </div>

          {error && (
            <div className="text-sm text-danger bg-red-50 border border-red-100 px-4 py-2.5 rounded mb-5">
              {error}
            </div>
          )}

          <div className="border border-neutral-200 bg-neutral-50 px-5 py-4 mb-5">
            <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" /> 可自动填写的表单
            </h3>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-neutral-600">
              <div>TY01 项目任务书</div>
              <div>TY02-1 工程项目策划表</div>
              <div>TY02-2 项目校审配置表</div>
              <div>TY03 互提资料单（基本信息）</div>
              <div>TY04-1 产品运行卡（专业）</div>
              <div>TY04-2 产品运行卡（项目）</div>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleGenerate}
              disabled={!file || uploading}
              className="btn-primary px-6"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  解析中…
                </>
              ) : (
                <>
                  <FileSpreadsheet className="w-4 h-4" strokeWidth={1.75} />
                  开始自动填写
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* 步骤2：确认信息 */}
      {activeStep === 'edit' && editedInfo && (
        <div className="space-y-5">
          {result?.warnings && result.warnings.length > 0 && (
            <div className="border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0 mt-0.5" strokeWidth={1.75} />
              <div className="text-sm text-amber-800">
                <p className="font-medium mb-1">需要人工确认</p>
                <ul className="space-y-0.5 text-amber-700">
                  {result.warnings.map((w, i) => <li key={i}>• {w}</li>)}
                </ul>
              </div>
            </div>
          )}

          {/* 项目基本信息 */}
          <div className="border border-neutral-200 bg-white">
            <div className="px-5 py-3.5 border-b border-neutral-200 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
              <h3 className="text-sm font-medium text-neutral-900">项目基本信息</h3>
            </div>
            <div className="p-5 grid grid-cols-2 gap-x-5 gap-y-4">
              <div>
                <label className="label">项目名称</label>
                <input type="text" value={editedInfo.project_name} onChange={e => updateField('project_name', e.target.value)} className="input" />
              </div>
              <div>
                <label className="label">项目编码</label>
                <input type="text" value={editedInfo.project_code} onChange={e => updateField('project_code', e.target.value)} className="input" />
              </div>
              <div>
                <label className="label">设计阶段</label>
                <select value={editedInfo.design_stage} onChange={e => updateField('design_stage', e.target.value)} className="input">
                  {DESIGN_STAGES.map(s => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="label">质量控制分级</label>
                <select value={editedInfo.quality_level} onChange={e => updateField('quality_level', e.target.value)} className="input">
                  {QUALITY_LEVELS.map(l => <option key={l}>{l}</option>)}
                </select>
              </div>
              <div>
                <label className="label">业主单位</label>
                <input type="text" value={editedInfo.client || ''} onChange={e => updateField('client', e.target.value)} placeholder="业主/建设单位" className="input" />
              </div>
              <div>
                <label className="label">报告日期</label>
                <input type="text" value={editedInfo.report_date || ''} onChange={e => updateField('report_date', e.target.value)} placeholder="如：2026年1月" className="input" />
              </div>
            </div>
          </div>

          {/* 工程概况 */}
          <div className="border border-neutral-200 bg-white">
            <div className="px-5 py-3.5 border-b border-neutral-200 flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
              <h3 className="text-sm font-medium text-neutral-900">工程概况与内容</h3>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="label">工作内容</label>
                <textarea value={editedInfo.work_scope || ''} onChange={e => updateField('work_scope', e.target.value)} rows={2} className="input" />
              </div>
              <div>
                <label className="label">工程概况及主要任务</label>
                <textarea value={editedInfo.engineering_overview || ''} onChange={e => updateField('engineering_overview', e.target.value)} rows={3} className="input" />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="label">工程等别</label>
                  <input type="text" value={editedInfo.project_grade || ''} onChange={e => updateField('project_grade', e.target.value)} placeholder="如：Ⅳ等" className="input" />
                </div>
                <div>
                  <label className="label">建筑物级别</label>
                  <input type="text" value={editedInfo.building_level || ''} onChange={e => updateField('building_level', e.target.value)} placeholder="如：4级" className="input" />
                </div>
                <div>
                  <label className="label">防洪标准</label>
                  <input type="text" value={editedInfo.flood_standard || ''} onChange={e => updateField('flood_standard', e.target.value)} placeholder="如：20年一遇" className="input" />
                </div>
              </div>
            </div>
          </div>

          {/* 专业配置 */}
          <div className="border border-neutral-200 bg-white">
            <div className="px-5 py-3.5 border-b border-neutral-200 flex items-center gap-2">
              <Users className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
              <h3 className="text-sm font-medium text-neutral-900">专业配置</h3>
              <span className="text-xs text-neutral-400 ml-1">不涉及的专业自动填 "/" </span>
            </div>
            <div className="p-5">
              <div className="flex flex-wrap gap-2">
                {ALL_MAJORS.map(major => {
                  const involved = editedInfo.involved_majors.includes(major)
                  return (
                    <button
                      key={major}
                      type="button"
                      onClick={() => toggleMajor(major)}
                      className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                        involved
                          ? 'bg-brand-50 border-brand-200 text-brand-700'
                          : 'bg-white border-neutral-200 text-neutral-500 hover:border-neutral-300'
                      }`}
                    >
                      {major}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => { setActiveStep('upload'); setResult(null); setEditedInfo(null) }}
              className="btn-ghost text-sm"
            >
              <ChevronLeft className="w-4 h-4" />
              返回重新上传
            </button>
            <button onClick={handleConfirm} className="btn-primary px-6">
              <CheckCircle2 className="w-4 h-4" strokeWidth={1.75} />
              确认并生成文档
            </button>
          </div>
        </div>
      )}

      {/* 步骤3：下载 */}
      {activeStep === 'download' && result && (
        <div className="max-w-xl mx-auto">
          <div className="border border-neutral-200 bg-white px-8 py-12 text-center">
            <div className="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-5">
              <CheckCircle2 className="w-8 h-8 text-success" strokeWidth={1.5} />
            </div>
            <h2 className="text-lg font-semibold text-neutral-900 mb-2">文档生成完成</h2>
            <p className="text-sm text-neutral-500 mb-6">
              项目：{editedInfo?.project_name || result.project_info.project_name}
            </p>
            <div className="space-y-2 text-xs text-neutral-500 mb-8 bg-neutral-50 border border-neutral-200 px-5 py-4 text-left">
              <p className="flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4 text-brand-600" />
                TY01-TY04 管理体系附表已自动填写
              </p>
              <p className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-warning" />
                签名和日期字段需人工手动签署
              </p>
              <p className="flex items-center gap-2">
                <Users className="w-4 h-4 text-neutral-400" />
                请核对专业配置和人员信息
              </p>
            </div>
            <div className="flex gap-3 justify-center">
              <button onClick={reset} className="btn-secondary">
                <RefreshCw className="w-4 h-4" strokeWidth={1.75} />
                继续生成
              </button>
              <button onClick={handleDownload} className="btn-primary px-6">
                <Download className="w-4 h-4" strokeWidth={1.75} />
                下载 Word 文档
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
