export interface Message {
  id?: number
  role: 'user' | 'assistant' | 'system' | 'tool' | 'thought'
  content: string
  tool_calls?: ToolCall[]
  token_usage?: TokenUsage
  created_at?: string
  step?: number
}

export interface ToolCall {
  name: string
  arguments: Record<string, any>
  result?: any
  status?: 'running' | 'success' | 'error'
  duration_ms?: number
  error?: string
}

export interface ThinkingStep {
  step: number
  thought?: string
  type: 'thinking' | 'tool_call' | 'tool_result'
  tool?: string
  arguments?: Record<string, any>
  result?: any
  duration_ms?: number
  error?: string
  status?: 'running' | 'success' | 'error'
  success?: boolean
}

export interface TokenUsage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
}

export interface Source {
  file_name: string
  page_number?: number | string
  snippet?: string
}

export interface ChatSession {
  id: string
  title: string
  mode: string
  created_at: string
  updated_at: string
  message_count: number
  summary?: string
}

export interface ChatSessionDetail extends ChatSession {
  messages: Message[]
}

export interface ToolSchema {
  name: string
  description: string
  parameters: Record<string, any>
}

export interface SyncChatResponse {
  session_id: string
  message_id: number
  content: string
  steps: number
  tools_used: string[]
  sources: Source[]
  usage?: TokenUsage
  duration_ms: number
}

export interface SSEEvent {
  event: 'metadata' | 'thinking' | 'tool_call' | 'tool_result' | 'token' | 'done' | 'error'
  data: any
}
