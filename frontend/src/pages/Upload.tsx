import { useState, useRef } from 'react'
import { Upload as UploadIcon, FileText, CheckCircle2, X, HardDrive, AlertTriangle } from 'lucide-react'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

export default function Upload() {
  const { user, openUpgrade, refreshUsage } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [docType, setDocType] = useState('水利规范')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [parsing, setParsing] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedDocId, setUploadedDocId] = useState<number | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  if (!user) return null

  const freeMaxSize = 5 * 1024 * 1024 // 5MB
  const proMaxSize = 50 * 1024 * 1024 // 50MB
  const maxSize = user.is_pro ? proMaxSize : freeMaxSize
  const maxSizeMB = maxSize / 1024 / 1024
  const storagePercent = Math.min(100, (user.total_upload_bytes / user.total_storage_limit) * 100)
  const storageFull = user.total_upload_bytes >= user.total_storage_limit

  const handleFileSelect = (f: File | null) => {
    if (!f) return
    setError('')
    // 前端预检文件大小
    if (f.size > maxSize) {
      setError(`文件大小超过${maxSizeMB}MB限制${!user.is_pro ? '，升级Pro可上传最大50MB文件' : ''}`)
      if (!user.is_pro) {
        openUpgrade(`免费版单文件上限${maxSizeMB}MB，升级Pro可上传最大50MB文件`)
      }
      return
    }
    if (storageFull && !user.is_pro) {
      setError('存储空间不足，请升级Pro或删除部分文档')
      openUpgrade('存储空间不足，升级Pro获得500MB存储')
      return
    }
    setFile(f)
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setUploadProgress(0)
    setError('')
    const formData = new FormData()
    formData.append('file', file)
    if (title) formData.append('title', title)
    formData.append('doc_type', docType)
    try {
      const res = await api.post('/upload', formData, {
        timeout: 300000,
        onUploadProgress: (e: any) => {
          if (e.total) {
            setUploadProgress(Math.round((e.loaded / e.total) * 100))
          }
        },
      })
      setUploadedDocId(res.data.doc_id)
      // 自动解析入库
      setParsing(true)
      setError(null)
      try {
        await api.post(`/documents/${res.data.doc_id}/parse`, {}, { timeout: 300000 })
        setSuccess(true)
      } catch (parseErr: any) {
        console.error('文档解析失败:', parseErr)
        setError(`文档上传成功，但解析过程出现问题：${parseErr?.response?.data?.detail || parseErr?.message || '未知错误'}。您可以稍后在文档列表中查看。`)
      } finally {
        setParsing(false)
      }
      refreshUsage()
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(detail || '上传失败，请重试')
      if (detail?.includes('升级') || detail?.includes('超限')) {
        openUpgrade(detail)
      }
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const reset = () => {
    setFile(null); setTitle(''); setSuccess(false); setError('')
    setUploadedDocId(null); setParsing(false); setUploadProgress(0)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="page-container max-w-2xl">
      <div className="page-header">
        <h1>文档入库</h1>
        <p>上传规范、报告、预案等文档，系统将自动解析、分块并向量化</p>
      </div>

      {/* 存储空间 */}
      <div className="border border-neutral-200 bg-white px-5 py-3 mb-5">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5 text-xs text-neutral-500">
            <HardDrive className="w-3.5 h-3.5" strokeWidth={1.75} />
            存储空间
            {!user.is_pro && <span className="text-neutral-400">（免费版）</span>}
            {user.is_pro && <span className="text-brand-600 font-medium">（Pro）</span>}
          </div>
          <span className={`text-xs tabular-nums ${storagePercent > 80 ? 'text-warning' : 'text-neutral-500'}`}>
            {formatBytes(user.total_upload_bytes)} / {formatBytes(user.total_storage_limit)}
          </span>
        </div>
        <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${storagePercent > 80 ? 'bg-amber-500' : 'bg-brand-500'}`}
            style={{ width: `${storagePercent}%` }}
          />
        </div>
        {!user.is_pro && storagePercent > 60 && (
          <p className="text-[11px] text-amber-600 mt-1.5 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            存储空间即将用完，<button onClick={() => openUpgrade()} className="underline">升级Pro</button>获得500MB
          </p>
        )}
      </div>

      {success ? (
        <div className="border border-neutral-200 bg-white px-8 py-12 text-center">
          <CheckCircle2 className="w-12 h-12 text-success mx-auto mb-4" strokeWidth={1.5} />
          <p className="text-base font-medium text-neutral-900 mb-1">上传并解析成功</p>
          <p className="text-sm text-neutral-500 mb-6">文档已入库，可在知识库中检索</p>
          <button onClick={reset} className="btn-primary">继续上传</button>
        </div>
      ) : (
        <div className="space-y-5">
          {/* 拖拽上传区 */}
          <div
            className={`border border-dashed bg-white px-8 py-10 text-center cursor-pointer transition-colors ${
              isDragging ? 'border-brand-500 bg-brand-50/30' : 'border-neutral-300 hover:border-neutral-400'
            }`}
            onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={e => {
              e.preventDefault()
              setIsDragging(false)
              handleFileSelect(e.dataTransfer.files[0])
            }}
            onClick={() => inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt,.md"
              className="hidden"
              onChange={e => handleFileSelect(e.target.files?.[0] || null)}
            />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText className="w-8 h-8 text-brand-600" strokeWidth={1.5} />
                <div className="text-left">
                  <p className="text-sm font-medium text-neutral-900">{file.name}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">{formatBytes(file.size)}</p>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); setFile(null); setError('') }}
                  className="ml-4 p-1 text-neutral-400 hover:text-danger hover:bg-red-50 rounded"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <>
                <UploadIcon className="w-9 h-9 text-neutral-300 mx-auto mb-3" strokeWidth={1.5} />
                <p className="text-sm text-neutral-700 mb-1">点击或拖拽文件到此处上传</p>
                <p className="text-xs text-neutral-400">
                  支持 PDF / Word / TXT / Markdown，单文件最大 {maxSizeMB}MB
                  {!user.is_pro && <span className="text-amber-600">（免费版）</span>}
                </p>
              </>
            )}
          </div>

          {/* 表单字段 */}
          <div className="border border-neutral-200 bg-white p-6 space-y-4">
            <div>
              <label className="label">文档标题（可选）</label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                className="input"
                placeholder="留空则使用文件名"
              />
            </div>
            <div>
              <label className="label">文档类型</label>
              <select value={docType} onChange={e => setDocType(e.target.value)} className="input">
                <option>水利规范</option>
                <option>历史工程报告</option>
                <option>防汛预案</option>
                <option>设计说明书</option>
                <option>审查意见</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="text-sm text-danger bg-red-50 border border-red-100 px-4 py-2.5 rounded">
              {error}
            </div>
          )}

          {uploading && uploadProgress > 0 && (
            <div className="w-full">
              <div className="flex justify-between text-xs text-neutral-500 mb-1">
                <span>上传进度</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 rounded-full transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            {(uploading || parsing) && (
              <span className="text-xs text-neutral-400 self-center">
                {uploading ? `上传中 ${uploadProgress}%` : '解析中...'}
              </span>
            )}
            <button
              onClick={handleUpload}
              disabled={!file || uploading || parsing}
              className="btn-primary"
            >
              {(uploading || parsing) ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {uploading ? '上传中…' : '解析中…'}
                </>
              ) : (
                <>
                  <UploadIcon className="w-4 h-4" strokeWidth={1.75} />
                  上传并入库
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
