import { useState } from 'react'
import { FileCheck2, Upload as UploadIcon, Crown, Lock, Loader2, AlertCircle } from 'lucide-react'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Review() {
  const { user, openUpgrade } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<string>('')
  const [error, setError] = useState('')

  if (!user) return null

  // 免费用户显示升级门
  if (!user.is_pro) {
    return (
      <div className="page-container max-w-2xl">
        <div className="page-header">
          <h1>合规审查</h1>
          <p>上传设计文件，AI 自动识别关键参数并进行合规性初审</p>
        </div>
        <div className="border border-neutral-200 bg-white px-8 py-16 text-center">
          <div className="w-14 h-14 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-5">
            <Lock className="w-7 h-7 text-amber-500" strokeWidth={1.5} />
          </div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-2">Pro 专属功能</h2>
          <p className="text-sm text-neutral-500 mb-1 max-w-sm mx-auto">
            合规审查需要消耗大量 Token 进行长文档分析，升级 Pro 版即可使用
          </p>
          <p className="text-xs text-neutral-400 mb-6">
            自动识别工程参数 · 规范条文比对 · 疑似风险提示 · 修改建议
          </p>
          <button onClick={() => openUpgrade('合规审查为Pro专属功能')} className="btn-primary">
            <Crown className="w-4 h-4" strokeWidth={1.75} />
            升级 Pro 解锁
          </button>
        </div>
      </div>
    )
  }

  // Pro 用户功能
  const handleUpload = async (f: File) => {
    setFile(f)
    setResult('')
    setError('')
    setAnalyzing(true)

    try {
      const formData = new FormData()
      formData.append('file', f)
      const uploadRes = await api.post('/review/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      const analyzeRes = await api.post('/review/analyze', {
        file_path: uploadRes.data.file_path,
        file_name: uploadRes.data.file_name,
      })

      setResult(analyzeRes.data.review_text)
    } catch (e: any) {
      setError(e?.response?.data?.detail || '审查失败，请重试')
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="page-container max-w-3xl">
      <div className="page-header">
        <h1>合规审查</h1>
        <p>上传设计文件，AI 自动识别关键参数并进行合规性初审</p>
      </div>

      {/* 上传区 */}
      <div
        className="border border-dashed border-neutral-300 bg-white px-8 py-10 text-center cursor-pointer hover:border-neutral-400 transition-colors mb-5"
        onClick={() => document.getElementById('review-file')?.click()}
      >
        <input
          id="review-file"
          type="file"
          accept=".pdf,.doc,.docx"
          className="hidden"
          onChange={e => {
            const f = e.target.files?.[0]
            if (f) handleUpload(f)
          }}
        />
        {analyzing ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
            <p className="text-sm text-neutral-600">正在分析文档，请稍候...</p>
          </div>
        ) : file ? (
          <div className="flex items-center justify-center gap-3">
            <FileCheck2 className="w-8 h-8 text-brand-600" strokeWidth={1.5} />
            <div className="text-left">
              <p className="text-sm font-medium text-neutral-900">{file.name}</p>
              <p className="text-xs text-neutral-500 mt-0.5">
                {result ? '分析完成' : '准备分析'}
              </p>
            </div>
          </div>
        ) : (
          <>
            <UploadIcon className="w-9 h-9 text-neutral-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-sm text-neutral-700 mb-1">点击上传设计说明书</p>
            <p className="text-xs text-neutral-400">支持 PDF / Word 格式</p>
          </>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 text-sm text-danger bg-red-50 border border-red-100 px-4 py-3 rounded mb-5">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* 审查结果 */}
      {result && (
        <div className="border border-neutral-200 bg-white p-6">
          <h3 className="text-sm font-medium text-neutral-900 mb-4 flex items-center gap-2">
            <FileCheck2 className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
            初审结果
          </h3>
          <div className="text-sm text-neutral-700 whitespace-pre-wrap leading-relaxed">
            {result}
          </div>
        </div>
      )}
    </div>
  )
}
