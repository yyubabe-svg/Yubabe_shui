import { useState } from 'react'
import { Eye, Edit3 } from 'lucide-react'
import MarkdownRenderer from '../MarkdownRenderer'

interface MarkdownEditorProps {
  value: string
  onChange: (val: string) => void
  placeholder?: string
  minHeight?: number
  className?: string
}

export default function MarkdownEditor({
  value,
  onChange,
  placeholder = '在此输入 Markdown 内容…',
  minHeight = 240,
  className = '',
}: MarkdownEditorProps) {
  const [mode, setMode] = useState<'edit' | 'preview' | 'split'>('edit')

  return (
    <div className={`border border-neutral-200 bg-white rounded-md overflow-hidden ${className}`}>
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-neutral-200 bg-neutral-50">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setMode('edit')}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded ${
              mode === 'edit' ? 'bg-white border border-neutral-200 text-neutral-900' : 'text-neutral-500 hover:text-neutral-700'
            }`}
          >
            <Edit3 className="w-3 h-3" />
            编辑
          </button>
          <button
            onClick={() => setMode('split')}
            className={`px-2.5 py-1 text-xs rounded ${
              mode === 'split' ? 'bg-white border border-neutral-200 text-neutral-900' : 'text-neutral-500 hover:text-neutral-700'
            }`}
          >
            分屏
          </button>
          <button
            onClick={() => setMode('preview')}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded ${
              mode === 'preview' ? 'bg-white border border-neutral-200 text-neutral-900' : 'text-neutral-500 hover:text-neutral-700'
            }`}
          >
            <Eye className="w-3 h-3" />
            预览
          </button>
        </div>
        <span className="text-xs text-neutral-400">Markdown</span>
      </div>

      {/* 内容区 */}
      <div className={`flex ${mode === 'split' ? 'divide-x divide-neutral-200' : ''}`}>
        {(mode === 'edit' || mode === 'split') && (
          <textarea
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder={placeholder}
            className={`flex-1 px-4 py-3 text-sm font-mono text-neutral-800 bg-white resize-none focus:outline-none ${mode === 'split' ? 'w-1/2' : 'w-full'}`}
            style={{ minHeight }}
          />
        )}
        {(mode === 'preview' || mode === 'split') && (
          <div
            className={`px-4 py-3 overflow-auto bg-white ${mode === 'split' ? 'w-1/2' : 'w-full'}`}
            style={{ minHeight }}
          >
            {value ? (
              <MarkdownRenderer content={value} />
            ) : (
              <p className="text-sm text-neutral-400">预览区域（暂无内容）</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
