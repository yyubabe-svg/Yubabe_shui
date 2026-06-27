import { Loader2, CheckCircle2, AlertCircle, Clock, FileText, FileSpreadsheet, Search, MessageSquare, Upload } from 'lucide-react'
import type { WorkspaceTask } from '../../api/workspace'

interface TaskProgressCardProps {
  task: WorkspaceTask
  onRetry?: () => void
  onView?: () => void
}

const typeConfig: Record<string, { label: string; icon: typeof FileText; color: string }> = {
  section_gen:    { label: '章节生成', icon: FileText,     color: 'text-brand-600 bg-brand-50' },
  form_fill:      { label: '表格填报', icon: FileSpreadsheet, color: 'text-green-600 bg-green-50' },
  ai_review:      { label: 'AI 初审',  icon: Search,       color: 'text-purple-600 bg-purple-50' },
  expert_reply:   { label: '专家回复', icon: MessageSquare, color: 'text-amber-600 bg-amber-50' },
  document_upload:{ label: '文档上传', icon: Upload,       color: 'text-blue-600 bg-blue-50' },
}

function getStatusInfo(status: string) {
  switch (status) {
    case 'pending':
    case 'waiting':
      return { label: '等待中', icon: Clock, color: 'text-neutral-500' }
    case 'running':
    case 'extracting':
    case 'generating':
    case 'parsing':
    case 'reviewing':
      return { label: '进行中', icon: Loader2, color: 'text-brand-600' }
    case 'completed':
    case 'done':
    case 'filled':
    case 'generated':
      return { label: '已完成', icon: CheckCircle2, color: 'text-green-600' }
    case 'failed':
    case 'error':
      return { label: '失败', icon: AlertCircle, color: 'text-red-600' }
    default:
      return { label: status, icon: Clock, color: 'text-neutral-500' }
  }
}

function formatTime(ts?: string) {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return ts }
}

export default function TaskProgressCard({ task, onRetry, onView }: TaskProgressCardProps) {
  const tc = typeConfig[task.task_type] || typeConfig.form_fill
  const sc = getStatusInfo(task.status)
  const StatusIcon = sc.icon
  const TypeIcon = tc.icon
  const isRunning = ['running', 'extracting', 'generating', 'parsing', 'reviewing'].includes(task.status)
  const isDone = ['completed', 'done', 'filled', 'generated'].includes(task.status)
  const isFailed = ['failed', 'error'].includes(task.status)

  return (
    <div className="panel p-4">
      <div className="flex items-start gap-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${tc.color}`}>
          <TypeIcon className="w-5 h-5" strokeWidth={1.75} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <p className="text-sm font-medium text-neutral-900 truncate">{task.task_name}</p>
            <span className={`flex items-center gap-1 text-xs flex-shrink-0 ${sc.color}`}>
              <StatusIcon className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
              {sc.label}
            </span>
          </div>
          <p className="text-xs text-neutral-500 mb-2">{tc.label} · {formatTime(task.created_at)}</p>

          {isRunning && (
            <div className="w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-600 transition-all duration-300"
                style={{ width: `${task.progress || 0}%` }}
              />
            </div>
          )}

          {task.error_message && (
            <p className="text-xs text-red-500 mt-1.5 truncate">{task.error_message}</p>
          )}

          {(isDone || isFailed) && (
            <div className="flex gap-2 mt-2">
              {isDone && onView && (
                <button onClick={onView} className="text-xs text-brand-600 hover:text-brand-700 font-medium">
                  查看结果
                </button>
              )}
              {isFailed && onRetry && (
                <button onClick={onRetry} className="text-xs text-red-600 hover:text-red-700 font-medium">
                  重试
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
