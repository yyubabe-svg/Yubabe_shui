import { useState, useRef } from 'react'
import {
  Box, Upload, FileText, AlertTriangle, CheckCircle2, AlertCircle,
  Loader2, ListOrdered, Download, FileSpreadsheet, X,
} from 'lucide-react'
import { toolsApi, type CadCheckResult } from '../../api/tools'

export default function CADPanel() {
  const [files, setFiles] = useState<File[]>([])
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState<CadCheckResult | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return
    const arr = Array.from(fileList).filter(f => f.name.toLowerCase().endsWith('.dxf'))
    setFiles(prev => [...prev, ...arr])
    setResult(null)
  }

  const removeFile = (idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx))
    setResult(null)
  }

  const handleCheck = async () => {
    if (files.length === 0) return
    setChecking(true)
    try {
      const res = await toolsApi.checkCadDrawings(files)
      setResult(res)
    } catch (e: any) {
      console.error('CAD检查失败:', e)
      alert('检查失败：' + (e.message || '未知错误'))
    } finally {
      setChecking(false)
    }
  }

  const getSeverityStyle = (s: string) => {
    switch (s) {
      case 'error': return 'bg-red-50 text-red-700 border-red-200'
      case 'major': return 'bg-amber-50 text-amber-700 border-amber-200'
      case 'minor': return 'bg-blue-50 text-blue-700 border-blue-200'
      case 'warning': return 'bg-neutral-50 text-neutral-600 border-neutral-200'
      default: return 'bg-neutral-50 text-neutral-600 border-neutral-200'
    }
  }

  const getSeverityIcon = (s: string) => {
    switch (s) {
      case 'error': return <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />
      case 'major': return <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
      case 'minor': return <AlertCircle className="w-3.5 h-3.5 text-blue-500 flex-shrink-0 mt-0.5" />
      default: return <AlertCircle className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0 mt-0.5" />
    }
  }

  return (
    <div className="space-y-5">
      {/* 上传区 */}
      <div className="panel p-5">
        <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
          <Box className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
          CAD 图纸批量检查
        </h3>
        <p className="text-xs text-neutral-500 mb-4">
          上传 DXF 图纸文件，自动识别图签信息，检查图号连续性、图名缺失、日期/专业/负责人一致性，生成图纸目录
        </p>

        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
            dragOver ? 'border-brand-400 bg-brand-50' : 'border-neutral-200 hover:border-brand-300'
          }`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="w-10 h-10 text-neutral-300 mx-auto mb-2" strokeWidth={1.5} />
          <p className="text-sm text-neutral-600">点击或拖拽 DXF 文件到此处</p>
          <p className="text-xs text-neutral-400 mt-1">支持批量上传，仅支持 DXF 格式</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".dxf"
            multiple
            className="hidden"
            onChange={e => handleFiles(e.target.files)}
          />
        </div>

        {/* 已选文件列表 */}
        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs text-neutral-500">已选择 {files.length} 个文件：</p>
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-2 p-2 bg-neutral-50 rounded text-sm">
                <FileText className="w-4 h-4 text-neutral-400 flex-shrink-0" />
                <span className="flex-1 truncate text-neutral-700">{f.name}</span>
                <span className="text-xs text-neutral-400">{(f.size / 1024).toFixed(1)} KB</span>
                <button
                  onClick={e => { e.stopPropagation(); removeFile(i) }}
                  className="p-1 hover:bg-neutral-200 rounded"
                >
                  <X className="w-3.5 h-3.5 text-neutral-400" />
                </button>
              </div>
            ))}
            <button
              onClick={handleCheck}
              disabled={checking}
              className="btn-primary mt-3 w-full flex items-center justify-center gap-2"
            >
              {checking ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              {checking ? '检查中...' : `开始检查 ${files.length} 张图纸`}
            </button>
          </div>
        )}
      </div>

      {/* 检查结果 */}
      {result && (
        <>
          {/* 摘要 */}
          <div className="panel p-5">
            <h3 className="text-sm font-semibold text-neutral-900 mb-3">检查结果摘要</h3>
            <div className="grid grid-cols-5 gap-3">
              <div className="p-3 bg-neutral-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-neutral-800">{result.summary.total}</p>
                <p className="text-xs text-neutral-500 mt-1">总文件</p>
              </div>
              <div className="p-3 bg-red-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-red-600">{result.summary.issues_critical}</p>
                <p className="text-xs text-red-500 mt-1">错误</p>
              </div>
              <div className="p-3 bg-amber-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-amber-600">{result.summary.issues_major}</p>
                <p className="text-xs text-amber-500 mt-1">重要问题</p>
              </div>
              <div className="p-3 bg-blue-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-blue-600">{result.summary.issues_minor}</p>
                <p className="text-xs text-blue-500 mt-1">一般问题</p>
              </div>
              <div className="p-3 bg-green-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-green-600">{result.parsed_count}</p>
                <p className="text-xs text-green-500 mt-1">已解析</p>
              </div>
            </div>
          </div>

          {/* 图纸目录 */}
          <div className="panel p-5">
            <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
              <ListOrdered className="w-4 h-4 text-brand-600" />
              图纸目录（自动生成）
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 text-xs text-neutral-500">
                    <th className="text-left py-2 px-2 font-medium">序号</th>
                    <th className="text-left py-2 px-2 font-medium">图号</th>
                    <th className="text-left py-2 px-2 font-medium">图名</th>
                    <th className="text-left py-2 px-2 font-medium">比例</th>
                    <th className="text-left py-2 px-2 font-medium">专业</th>
                    <th className="text-left py-2 px-2 font-medium">日期</th>
                    <th className="text-left py-2 px-2 font-medium">文件名</th>
                  </tr>
                </thead>
                <tbody>
                  {result.catalog.map((row, i) => (
                    <tr key={i} className="border-b border-neutral-100 hover:bg-neutral-50">
                      <td className="py-2 px-2 text-neutral-500">{row.index}</td>
                      <td className="py-2 px-2 font-mono text-xs">{row.drawing_number}</td>
                      <td className="py-2 px-2">{row.drawing_name}</td>
                      <td className="py-2 px-2 text-neutral-500">{row.scale}</td>
                      <td className="py-2 px-2 text-neutral-500">{row.major}</td>
                      <td className="py-2 px-2 text-neutral-500">{row.date}</td>
                      <td className="py-2 px-2 text-neutral-400 text-xs truncate max-w-[180px]" title={row.filename}>{row.filename}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 问题列表 */}
          {result.issues.length > 0 && (
            <div className="panel p-5">
              <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                发现的问题（{result.issues.length}项）
              </h3>
              <div className="space-y-2">
                {result.issues.map((issue, i) => (
                  <div key={i} className={`flex items-start gap-2 p-3 rounded-lg border ${getSeverityStyle(issue.severity)}`}>
                    {getSeverityIcon(issue.severity)}
                    <div className="flex-1 min-w-0">
                      {issue.file && (
                        <p className="text-xs font-medium opacity-70">{issue.file}</p>
                      )}
                      <p className="text-sm">{issue.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 解析详情 */}
          <div className="panel p-5">
            <h3 className="text-sm font-semibold text-neutral-900 mb-3">图纸解析详情</h3>
            <div className="space-y-3">
              {result.drawings.map((d, i) => (
                <div key={i} className="p-3 bg-neutral-50 rounded-lg">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-neutral-800">{d.filename}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      d.parse_status === 'parsed' ? 'bg-green-100 text-green-700' :
                      d.parse_status === 'error' ? 'bg-red-100 text-red-700' :
                      'bg-neutral-200 text-neutral-600'
                    }`}>
                      {d.parse_status === 'parsed' ? '已解析' :
                       d.parse_status === 'error' ? '解析失败' :
                       d.parse_status === 'ezdxf_not_installed' ? '需安装ezdxf' : '跳过'}
                    </span>
                  </div>
                  {d.parse_status === 'parsed' && (
                    <div className="grid grid-cols-3 md:grid-cols-4 gap-2 mt-2 text-xs">
                      <div><span className="text-neutral-400">图号：</span>{d.drawing_number || '—'}</div>
                      <div><span className="text-neutral-400">图名：</span>{d.drawing_name || '—'}</div>
                      <div><span className="text-neutral-400">比例：</span>{d.scale || '—'}</div>
                      <div><span className="text-neutral-400">日期：</span>{d.date || '—'}</div>
                      <div><span className="text-neutral-400">设计：</span>{d.designer || '—'}</div>
                      <div><span className="text-neutral-400">校核：</span>{d.reviewer || '—'}</div>
                      <div><span className="text-neutral-400">审查：</span>{d.chief || '—'}</div>
                      <div><span className="text-neutral-400">专业：</span>{d.major || '—'}</div>
                    </div>
                  )}
                  {d.error && <p className="text-xs text-red-600 mt-1">{d.error}</p>}
                  {d.warnings && d.warnings.map((w, j) => (
                    <p key={j} className="text-xs text-amber-600 mt-1">{w}</p>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {!result && files.length === 0 && (
        <div className="panel p-5">
          <h4 className="text-sm font-medium text-neutral-800 mb-3">功能说明</h4>
          <ul className="text-sm text-neutral-600 space-y-2 list-disc list-inside">
            <li>自动识别图签中的图号、图名、比例、日期、设计/校核/审查人员、专业</li>
            <li>检查图号连续性，自动识别缺号</li>
            <li>检查图名缺失、日期/专业/负责人一致性</li>
            <li>自动生成标准图纸目录表</li>
            <li>支持批量上传多张图纸一次检查</li>
          </ul>
          <p className="text-xs text-neutral-400 mt-3">注：需安装 ezdxf 库（pip install ezdxf）才能解析DXF；未安装时返回文件基本信息。</p>
        </div>
      )}
    </div>
  )
}
