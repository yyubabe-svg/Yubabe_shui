import { useEffect, useState, useRef, useCallback, type ReactNode } from 'react'
import {
  Upload, FileText, Trash2, Star, StarOff, CheckCircle, Loader2, AlertCircle,
  FileSpreadsheet, File as FileIcon,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import { workspaceApi, type ProjectDocument } from '../../api/workspace'

const ACCEPTED_TYPES = '.pdf,.docx,.doc,.txt,.xlsx'
const ACCEPTED_EXTS = ['pdf', 'docx', 'doc', 'txt', 'xlsx']

// ─── 工具函数 ───────────────────────────────────────────────

function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (['doc', 'docx'].includes(ext || '')) return <FileText className="w-5 h-5 text-blue-500" strokeWidth={1.5} />
  if (['xls', 'xlsx'].includes(ext || '')) return <FileSpreadsheet className="w-5 h-5 text-green-600" strokeWidth={1.5} />
  if (ext === 'pdf') return <FileText className="w-5 h-5 text-red-500" strokeWidth={1.5} />
  if (ext === 'txt') return <FileText className="w-5 h-5 text-neutral-500" strokeWidth={1.5} />
  return <FileIcon className="w-5 h-5 text-neutral-500" strokeWidth={1.5} />
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ts
  }
}

// 解析状态映射
function getParseStatusInfo(status: string): { label: string; className: string; icon: ReactNode } {
  switch (status) {
    case 'pending':
      return {
        label: '待解析',
        className: 'bg-neutral-100 text-neutral-600',
        icon: <div className="w-1.5 h-1.5 rounded-full bg-neutral-400" />,
      }
    case 'parsing':
      return {
        label: '解析中',
        className: 'bg-blue-50 text-blue-600',
        icon: <Loader2 className="w-3 h-3 animate-spin" />,
      }
    case 'completed':
      return {
        label: '已完成',
        className: 'bg-green-50 text-green-600',
        icon: <CheckCircle className="w-3 h-3" />,
      }
    case 'failed':
      return {
        label: '失败',
        className: 'bg-red-50 text-red-600',
        icon: <AlertCircle className="w-3 h-3" />,
      }
    default:
      return {
        label: status || '未知',
        className: 'bg-neutral-100 text-neutral-600',
        icon: <div className="w-1.5 h-1.5 rounded-full bg-neutral-400" />,
      }
  }
}

// ─── 主组件 ─────────────────────────────────────────────────

export default function DocumentsPanel() {
  const { currentProject } = useProject()
  const [docs, setDocs] = useState<ProjectDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadFileName, setUploadFileName] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 加载文档列表
  const loadDocs = useCallback(async () => {
    if (!currentProject) return
    setLoading(true)
    setError('')
    try {
      const res = await workspaceApi.listDocuments(currentProject.id)
      setDocs(res.items)
    } catch (e: any) {
      setError(e?.response?.data?.detail || '加载文档失败')
    } finally {
      setLoading(false)
    }
  }, [currentProject])

  useEffect(() => {
    loadDocs()
  }, [loadDocs])

  // 验证文件类型
  const validateFile = (file: File): boolean => {
    const ext = file.name.split('.').pop()?.toLowerCase() || ''
    if (!ACCEPTED_EXTS.includes(ext)) {
      setError(`不支持的文件格式：${file.name}，请上传 PDF / Word / Excel / TXT 文件`)
      return false
    }
    return true
  }

  // 上传文件
  const handleUploadFiles = async (files: FileList | File[]) => {
    if (!currentProject || files.length === 0) return
    const validFiles = Array.from(files).filter(validateFile)
    if (validFiles.length === 0) return

    setUploading(true)
    setError('')
    setUploadProgress(0)

    try {
      for (let i = 0; i < validFiles.length; i++) {
        const f = validFiles[i]
        setUploadFileName(f.name)
        await workspaceApi.uploadDocument(currentProject.id, f, (percent) => {
          // 多文件时按比例分配进度
          const base = (i / validFiles.length) * 100
          const portion = (percent / 100) * (100 / validFiles.length)
          setUploadProgress(Math.round(base + portion))
        })
      }
      setUploadProgress(100)
      await loadDocs()
    } catch (e: any) {
      setError(e?.response?.data?.detail || '上传失败')
    } finally {
      setUploading(false)
      setUploadProgress(0)
      setUploadFileName('')
    }
  }

  // 点击上传区域
  const handleClick = () => {
    if (!uploading) fileInputRef.current?.click()
  }

  // 文件选择
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) handleUploadFiles(e.target.files)
    e.target.value = ''
  }

  // 拖拽事件
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    if (!uploading) setDragOver(true)
  }
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (uploading) return
    if (e.dataTransfer.files) handleUploadFiles(e.dataTransfer.files)
  }

  // 删除文档
  const handleDelete = async (docId: number) => {
    if (!currentProject) return
    if (!confirm('确定删除该文档？')) return
    try {
      await workspaceApi.deleteDocument(currentProject.id, docId)
      setDocs(prev => prev.filter(d => d.id !== docId))
    } catch (e: any) {
      setError(e?.response?.data?.detail || '删除失败')
    }
  }

  // 标记为主报告
  const handleSetReport = async (docId: number, isReport: boolean) => {
    if (!currentProject) return
    try {
      await workspaceApi.setDocumentAsReport(currentProject.id, docId)
      // 切换状态：如果当前已标记，则取消（需要后端支持，这里先刷新）
      await loadDocs()
    } catch (e: any) {
      setError(e?.response?.data?.detail || '操作失败')
    }
  }

  // 标记为专家意见
  const handleSetExpertOpinion = async (docId: number) => {
    if (!currentProject) return
    try {
      await workspaceApi.setDocumentAsExpertOpinion(currentProject.id, docId)
      await loadDocs()
    } catch (e: any) {
      setError(e?.response?.data?.detail || '操作失败')
    }
  }

  return (
    <div className="space-y-6">
      {/* ── 上传区域 ── */}
      <div className="panel p-5">
        <h2 className="text-sm font-semibold text-neutral-900 flex items-center gap-2 mb-4">
          <Upload className="w-4 h-4 text-brand-600" strokeWidth={2} />
          上传资料
        </h2>

        <div
          onClick={handleClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`
            relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
            ${dragOver
              ? 'border-brand-500 bg-brand-50'
              : 'border-neutral-300 hover:border-brand-400 hover:bg-neutral-50'
            }
            ${uploading ? 'pointer-events-none opacity-70' : ''}
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            multiple
            onChange={handleFileChange}
            className="hidden"
          />

          {uploading ? (
            <div className="space-y-3">
              <Loader2 className="w-8 h-8 text-brand-600 animate-spin mx-auto" strokeWidth={1.5} />
              <p className="text-sm text-neutral-600">
                正在上传 <span className="font-medium text-neutral-900">{uploadFileName}</span>
              </p>
              <div className="max-w-xs mx-auto">
                <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-600 rounded-full transition-all duration-200"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-xs text-neutral-500 mt-1">{uploadProgress}%</p>
              </div>
            </div>
          ) : (
            <>
              <Upload className="w-10 h-10 text-neutral-400 mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-sm text-neutral-700 font-medium mb-1">
                拖拽文件到此处，或点击选择文件
              </p>
              <p className="text-xs text-neutral-400">
                支持 PDF / Word (.doc, .docx) / Excel (.xlsx) / TXT，单文件不超过 100MB
              </p>
            </>
          )}
        </div>

        {error && (
          <div className="flex items-center gap-2 mt-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* ── 文档列表 ── */}
      <div className="panel">
        <div className="flex items-center justify-between px-5 py-3 border-b border-neutral-200">
          <h2 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
            <FileText className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
            资料列表
            <span className="text-xs font-normal text-neutral-400">({docs.length} 份)</span>
          </h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-brand-600 animate-spin" />
          </div>
        ) : docs.length === 0 ? (
          <div className="empty-state py-16">
            <FileText className="empty-state-icon" strokeWidth={1.5} />
            <p className="empty-state-text">还没有上传资料</p>
            <p className="text-xs text-neutral-400 mt-1">上传设计报告、基础资料等文件开始工作</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th className="w-8"></th>
                <th>文件名</th>
                <th className="w-20">类型</th>
                <th className="w-20">大小</th>
                <th className="w-24">解析状态</th>
                <th className="w-16">页数</th>
                <th className="w-28">标记</th>
                <th className="w-32 text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {docs.map(doc => {
                const statusInfo = getParseStatusInfo(doc.parse_status)
                return (
                  <tr key={doc.id}>
                    {/* 文件图标 */}
                    <td>{getFileIcon(doc.original_filename)}</td>

                    {/* 文件名 */}
                    <td>
                      <p className="text-sm text-neutral-900 truncate" title={doc.original_filename}>
                        {doc.original_filename}
                      </p>
                      <p className="text-xs text-neutral-400">{formatTime(doc.created_at)}</p>
                    </td>

                    {/* 类型 */}
                    <td>
                      <span className="text-xs text-neutral-500 uppercase">
                        {doc.file_type || doc.original_filename.split('.').pop()}
                      </span>
                    </td>

                    {/* 大小 */}
                    <td className="text-xs text-neutral-500">{formatSize(doc.file_size)}</td>

                    {/* 解析状态 */}
                    <td>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusInfo.className}`}>
                        {statusInfo.icon}
                        {statusInfo.label}
                      </span>
                    </td>

                    {/* 页数 */}
                    <td className="text-xs text-neutral-500">
                      {doc.total_pages ? `${doc.total_pages} 页` : '-'}
                    </td>

                    {/* 标记 */}
                    <td>
                      <div className="flex items-center gap-1">
                        {doc.is_report && (
                          <span
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-600"
                            title="主报告"
                          >
                            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                            主报告
                          </span>
                        )}
                        {doc.is_expert_opinion && (
                          <span
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-600"
                            title="专家意见"
                          >
                            <Star className="w-3 h-3 fill-purple-400 text-purple-400" />
                            意见
                          </span>
                        )}
                        {!doc.is_report && !doc.is_expert_opinion && (
                          <span className="text-xs text-neutral-300">-</span>
                        )}
                      </div>
                    </td>

                    {/* 操作 */}
                    <td className="text-right">
                      <div className="flex items-center justify-end gap-0.5">
                        <button
                          onClick={() => handleSetReport(doc.id, doc.is_report)}
                          className={`p-1.5 rounded transition-colors ${
                            doc.is_report
                              ? 'text-amber-500 hover:bg-amber-50'
                              : 'text-neutral-400 hover:text-amber-500 hover:bg-amber-50'
                          }`}
                          title={doc.is_report ? '取消主报告标记' : '标记为主报告'}
                        >
                          {doc.is_report ? <StarOff className="w-4 h-4" /> : <Star className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => handleSetExpertOpinion(doc.id)}
                          className={`p-1.5 rounded transition-colors ${
                            doc.is_expert_opinion
                              ? 'text-purple-500 hover:bg-purple-50'
                              : 'text-neutral-400 hover:text-purple-500 hover:bg-purple-50'
                          }`}
                          title={doc.is_expert_opinion ? '取消专家意见标记' : '标记为专家意见'}
                        >
                          <FileText className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="p-1.5 text-neutral-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
