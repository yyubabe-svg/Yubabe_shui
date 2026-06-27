import { AlertCircle, AlertTriangle, Info, CheckCircle2, MessageSquare, Filter } from 'lucide-react'
import type { ReviewIssue } from '../../api/workspace'
import { useState } from 'react'

interface IssueListProps {
  issues: ReviewIssue[]
  onStatusChange?: (id: number, status: ReviewIssue['status']) => void
  showExport?: boolean
  onExport?: () => void
  emptyHint?: string
}

const severityConfig = {
  critical: { icon: AlertCircle, label: '严重', color: 'text-red-600 bg-red-50 border-red-100', dot: 'bg-red-500' },
  major:    { icon: AlertTriangle, label: '重要', color: 'text-amber-700 bg-amber-50 border-amber-200', dot: 'bg-amber-500' },
  minor:    { icon: Info, label: '一般', color: 'text-blue-700 bg-blue-50 border-blue-200', dot: 'bg-blue-500' },
  suggestion: { icon: MessageSquare, label: '建议', color: 'text-neutral-600 bg-neutral-50 border-neutral-200', dot: 'bg-neutral-400' },
}

const categoryLabels: Record<string, string> = {
  code_ref: '规范引用',
  data_consistency: '数据一致性',
  design_depth: '设计深度',
  text: '文字表述',
  other: '其他',
}

export default function IssueList({ issues, onStatusChange, showExport, onExport, emptyHint }: IssueListProps) {
  const [filter, setFilter] = useState<'all' | ReviewIssue['severity']>('all')

  const filtered = filter === 'all' ? issues : issues.filter(i => i.severity === filter)
  const counts = {
    critical: issues.filter(i => i.severity === 'critical').length,
    major: issues.filter(i => i.severity === 'major').length,
    minor: issues.filter(i => i.severity === 'minor').length,
    suggestion: issues.filter(i => i.severity === 'suggestion').length,
  }

  if (issues.length === 0) {
    return (
      <div className="border border-neutral-200 bg-white">
        <div className="empty-state">
          <CheckCircle2 className="empty-state-icon" strokeWidth={1.5} />
          <p className="empty-state-text">{emptyHint || '暂无问题'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 筛选栏 */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-4 h-4 text-neutral-400" />
          <button
            onClick={() => setFilter('all')}
            className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
              filter === 'all' ? 'bg-neutral-900 text-white border-neutral-900' : 'bg-white text-neutral-600 border-neutral-200 hover:border-neutral-300'
            }`}
          >
            全部 ({issues.length})
          </button>
          {(Object.keys(severityConfig) as ReviewIssue['severity'][]).map(sev => (
            <button
              key={sev}
              onClick={() => setFilter(sev)}
              className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                filter === sev ? severityConfig[sev].color : 'bg-white text-neutral-600 border-neutral-200 hover:border-neutral-300'
              }`}
            >
              {severityConfig[sev].label} ({counts[sev]})
            </button>
          ))}
        </div>
        {showExport && onExport && (
          <button onClick={onExport} className="btn-secondary text-xs">
            导出审查报告
          </button>
        )}
      </div>

      {/* 问题列表 */}
      <div className="space-y-2">
        {filtered.map((issue, idx) => {
          const cfg = severityConfig[issue.severity]
          const Icon = cfg.icon
          return (
            <div key={issue.id} className="panel p-4">
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${cfg.color.split(' ')[1]}`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs font-mono text-neutral-400">#{idx + 1}</span>
                    <span className={`badge ${cfg.color.split(' ').slice(0, 2).join(' ')}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} mr-1`} />
                      {cfg.label}
                    </span>
                    {issue.category && (
                      <span className="badge-neutral">{categoryLabels[issue.category] || issue.category}</span>
                    )}
                    {issue.location_desc && (
                      <span className="text-xs text-neutral-500">{issue.location_desc}</span>
                    )}
                    {onStatusChange && (
                      <select
                        value={issue.status}
                        onChange={e => onStatusChange(issue.id, e.target.value as ReviewIssue['status'])}
                        className="ml-auto text-xs border border-neutral-200 rounded px-2 py-0.5 bg-white"
                      >
                        <option value="open">未处理</option>
                        <option value="resolved">已解决</option>
                        <option value="ignored">忽略</option>
                      </select>
                    )}
                  </div>
                  <p className="text-sm text-neutral-800 mb-1">{issue.description}</p>
                  {issue.suggestion && (
                    <p className="text-xs text-neutral-500 bg-neutral-50 px-3 py-2 rounded border-l-2 border-brand-400 mt-2">
                      <span className="text-neutral-400 mr-1">建议：</span>{issue.suggestion}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
