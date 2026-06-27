import { useState, useRef, type DragEvent, type ChangeEvent } from 'react'
import { Upload, File, X, Loader2, FileText, FileSpreadsheet, Image as ImageIcon } from 'lucide-react'

export interface UploadedFileInfo {
  name: string
  size: number
  type: string
  file: File
}

interface FileUploaderProps {
  accept?: string
  multiple?: boolean
  maxSize?: number       // bytes
  uploading?: boolean
  uploadProgress?: number
  hint?: string
  value?: UploadedFileInfo[]
  onChange?: (files: UploadedFileInfo[]) => void
  onUpload?: (files: File[]) => void
  className?: string
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (['doc', 'docx'].includes(ext || '')) return <FileText className="w-5 h-5 text-blue-500" strokeWidth={1.5} />
  if (['xls', 'xlsx', 'csv'].includes(ext || '')) return <FileSpreadsheet className="w-5 h-5 text-green-600" strokeWidth={1.5} />
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext || '')) return <ImageIcon className="w-5 h-5 text-purple-500" strokeWidth={1.5} />
  if (ext === 'pdf') return <FileText className="w-5 h-5 text-red-500" strokeWidth={1.5} />
  return <File className="w-5 h-5 text-neutral-500" strokeWidth={1.5} />
}

export default function FileUploader({
  accept = '*',
  multiple = false,
  maxSize,
  uploading = false,
  uploadProgress,
  hint,
  value,
  onChange,
  onUpload,
  className = '',
}: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const files = value || []

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return
    setError('')
    const newFiles: UploadedFileInfo[] = []
    for (let i = 0; i < fileList.length; i++) {
      const f = fileList[i]
      if (maxSize && f.size > maxSize) {
        setError(`文件 ${f.name} 超过大小限制（${formatSize(maxSize)}）`)
        continue
      }
      newFiles.push({ name: f.name, size: f.size, type: f.type, file: f })
    }
    if (newFiles.length === 0) return
    const updated = multiple ? [...files, ...newFiles] : newFiles
    onChange?.(updated)
    onUpload?.(newFiles.map(f => f.file))
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files)
    if (inputRef.current) inputRef.current.value = ''
  }

  const removeFile = (idx: number) => {
    const updated = files.filter((_, i) => i !== idx)
    onChange?.(updated)
  }

  return (
    <div className={className}>
      <div
        className={`border border-dashed bg-white px-6 py-10 text-center cursor-pointer transition-colors ${
          isDragging ? 'border-brand-500 bg-brand-50/30' : 'border-neutral-300 hover:border-neutral-400'
        } ${uploading ? 'pointer-events-none opacity-60' : ''}`}
        onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={handleChange}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-brand-600 animate-spin" strokeWidth={1.5} />
            <p className="text-sm text-neutral-700">上传中…</p>
            {typeof uploadProgress === 'number' && (
              <div className="w-48 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                <div className="h-full bg-brand-600 transition-all" style={{ width: `${uploadProgress}%` }} />
              </div>
            )}
          </div>
        ) : (
          <>
            <Upload className="w-9 h-9 text-neutral-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-sm text-neutral-700 mb-1">
              点击或拖拽文件{multiple ? '（可多选）' : ''}到此上传
            </p>
            {hint && <p className="text-xs text-neutral-400">{hint}</p>}
          </>
        )}
      </div>

      {error && (
        <div className="text-sm text-danger bg-red-50 border border-red-100 px-4 py-2 rounded mt-3">
          {error}
        </div>
      )}

      {files.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {files.map((f, i) => (
            <li key={i} className="flex items-center gap-2.5 px-3 py-2 bg-white border border-neutral-200 rounded text-sm">
              {getFileIcon(f.name)}
              <span className="flex-1 truncate text-neutral-800">{f.name}</span>
              <span className="text-xs text-neutral-400">{formatSize(f.size)}</span>
              <button
                type="button"
                onClick={e => { e.stopPropagation(); removeFile(i) }}
                className="text-neutral-400 hover:text-danger p-0.5"
                disabled={uploading}
              >
                <X className="w-4 h-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
