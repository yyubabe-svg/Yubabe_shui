import { FileText } from 'lucide-react'
import type { Source } from '../../types/agent'

interface SourceListProps {
  sources: Source[]
}

export default function SourceList({ sources }: SourceListProps) {
  if (!sources || sources.length === 0) return null

  // 去重
  const uniqueSources: Source[] = []
  const seen = new Set<string>()
  for (const s of sources) {
    const key = `${s.file_name}-${s.page_number}`
    if (!seen.has(key)) {
      seen.add(key)
      uniqueSources.push(s)
    }
  }

  return (
    <div className="mt-4 pt-3 border-t border-neutral-100">
      <div className="text-xs text-neutral-500 mb-2">参考来源</div>
      <div className="flex flex-wrap gap-2">
        {uniqueSources.slice(0, 6).map((source, i) => (
          <div
            key={i}
            className="inline-flex items-center gap-1 text-xs bg-neutral-100 text-neutral-600 px-2 py-1 rounded-md hover:bg-neutral-200 cursor-default"
            title={source.snippet || ''}
          >
            <FileText className="w-3 h-3 flex-shrink-0" />
            <span className="max-w-[200px] truncate">{source.file_name}</span>
            {source.page_number && <span className="text-neutral-400">P.{source.page_number}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
