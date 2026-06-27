import { useState } from 'react'
import { ChevronDown, ChevronRight, Brain } from 'lucide-react'
import ToolCallCard from './ToolCallCard'
import type { ThinkingStep } from '../../types/agent'

interface ThinkingProcessProps {
  steps: ThinkingStep[]
}

export default function ThinkingProcess({ steps }: ThinkingProcessProps) {
  const [expanded, setExpanded] = useState(false)
  const toolCalls = steps.filter(s => s.type === 'tool_call')

  if (steps.length === 0) return null

  return (
    <div className="mb-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-700 transition-colors"
      >
        {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        <Brain className="w-3.5 h-3.5" />
        <span>已思考{steps.length > 0 ? Math.max(...steps.filter(s => s.step).map(s => s.step || 0)) : 0}步</span>
        {toolCalls.length > 0 && <span>，调用了{toolCalls.length}个工具</span>}
      </button>
      {expanded && (
        <div className="mt-2 space-y-1">
          {steps.filter(s => s.type === 'tool_call').map((step, i) => (
            <ToolCallCard key={i} step={step} />
          ))}
        </div>
      )}
    </div>
  )
}
