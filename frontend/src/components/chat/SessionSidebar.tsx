import { Plus, MessageSquare, Trash2, Loader2 } from 'lucide-react'
import type { ChatSession } from '../../types/agent'

interface SessionSidebarProps {
  sessions: ChatSession[]
  currentSessionId: string | null
  loading: boolean
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}

export default function SessionSidebar({ sessions, currentSessionId, loading, onSelect, onNew, onDelete }: SessionSidebarProps) {
  return (
    <div className="w-64 flex-shrink-0 bg-neutral-50 border-r border-neutral-200 flex flex-col">
      <div className="p-3 border-b border-neutral-200">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 transition-colors"
        >
          <Plus className="w-4 h-4" />
          新对话
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {loading && (
          <div className="flex items-center justify-center py-8 text-neutral-400">
            <Loader2 className="w-5 h-5 animate-spin" />
          </div>
        )}
        {sessions.map(session => (
          <div
            key={session.id}
            className={`group flex items-center gap-2 rounded-lg px-3 py-2 text-sm cursor-pointer transition-colors ${
              currentSessionId === session.id
                ? 'bg-brand-50 text-brand-700 font-medium'
                : 'text-neutral-600 hover:bg-neutral-100'
            }`}
            onClick={() => onSelect(session.id)}
          >
            <MessageSquare className="w-4 h-4 flex-shrink-0" />
            <span className="flex-1 truncate">{session.title || '新对话'}</span>
            <button
              onClick={e => {
                e.stopPropagation()
                onDelete(session.id)
              }}
              className="opacity-0 group-hover:opacity-100 p-1 text-neutral-400 hover:text-red-500 transition-all"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
        {!loading && sessions.length === 0 && (
          <div className="text-center text-xs text-neutral-400 py-8">
            暂无历史对话
          </div>
        )}
      </div>
    </div>
  )
}
