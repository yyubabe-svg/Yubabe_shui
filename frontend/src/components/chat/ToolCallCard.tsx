import { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Loader2, Search, Calculator, BookOpen, FolderSearch, ShieldAlert, FileText, Box, HelpCircle } from 'lucide-react'
import type { ThinkingStep } from '../../types/agent'

const toolIcons: Record<string, any> = {
  standard_search: Search,
  param_calculator: Calculator,
  code_lookup: BookOpen,
  project_matcher: FolderSearch,
  flood_plan_query: ShieldAlert,
  compliance_checker: ShieldAlert,
  doc_generator: FileText,
  cad_helper: Box,
  rag_query: Search,
}

const toolNames: Record<string, string> = {
  standard_search: '规范检索',
  param_calculator: '参数计算',
  code_lookup: '条文查找',
  project_matcher: '案例匹配',
  flood_plan_query: '预案查询',
  compliance_checker: '合规审查',
  doc_generator: '文档生成',
  cad_helper: 'CAD辅助',
  rag_query: '知识库检索',
}

interface ToolCallCardProps {
  step: ThinkingStep
}

export default function ToolCallCard({ step }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false)
  const Icon = toolIcons[step.tool || ''] || HelpCircle
  const toolName = toolNames[step.tool || ''] || step.tool || '工具'

  return (
    <div className="border border-neutral-200 rounded-lg bg-neutral-50 my-2 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-neutral-100 transition-colors"
      >
        {expanded ? <ChevronDown className="w-4 h-4 text-neutral-400 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-neutral-400 flex-shrink-0" />}
        <Icon className="w-4 h-4 text-brand-600 flex-shrink-0" />
        <span className="font-medium text-neutral-700">{toolName}</span>
        {step.status === 'running' && <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin flex-shrink-0" />}
        {step.status === 'success' && <CheckCircle className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />}
        {step.status === 'error' && <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />}
        {step.duration_ms && <span className="text-xs text-neutral-400 ml-auto">{step.duration_ms}ms</span>}
      </button>
      {expanded && (
        <div className="px-3 pb-3 pt-1 border-t border-neutral-200 bg-white">
          {step.arguments && Object.keys(step.arguments).length > 0 && (
            <div className="mb-2">
              <div className="text-xs text-neutral-500 mb-1">参数</div>
              <pre className="text-xs bg-neutral-50 p-2 rounded overflow-x-auto text-neutral-600">
                {JSON.stringify(step.arguments, null, 2)}
              </pre>
            </div>
          )}
          {step.result !== undefined && (
            <div>
              <div className="text-xs text-neutral-500 mb-1">结果</div>
              <div className="text-xs text-neutral-600 max-h-40 overflow-y-auto">
                {typeof step.result === 'string' ? step.result : (
                  <pre className="bg-neutral-50 p-2 rounded overflow-x-auto">{JSON.stringify(step.result, null, 2).slice(0, 1000)}</pre>
                )}
              </div>
            </div>
          )}
          {step.error && (
            <div className="text-xs text-red-600 mt-1">错误：{step.error}</div>
          )}
        </div>
      )}
    </div>
  )
}
