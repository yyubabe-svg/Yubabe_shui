import { useState, useCallback, useRef } from 'react'
import { agentApi } from '../api/agent'
import type { Message, ThinkingStep, ToolCall, Source, TokenUsage } from '../types/agent'

export function useAgentChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [sources, setSources] = useState<Source[]>([])
  const [toolsUsed, setToolsUsed] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const parseSSEEvents = (chunk: string): Array<{ event: string; data: any }> => {
    const events: Array<{ event: string; data: any }> = []
    const lines = chunk.split('\n')
    let currentEvent = 'message'
    let currentData = ''

    for (const line of lines) {
      if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        currentData += line.slice(5).trim()
      } else if (line === '') {
        if (currentData) {
          try {
            events.push({ event: currentEvent, data: JSON.parse(currentData) })
          } catch {
            events.push({ event: currentEvent, data: currentData })
          }
          currentData = ''
          currentEvent = 'message'
        }
      }
    }
    if (currentData) {
      try {
        events.push({ event: currentEvent, data: JSON.parse(currentData) })
      } catch {}
    }
    return events
  }

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isStreaming) return

    setError(null)
    setStreamingContent('')
    setThinkingSteps([])
    setSources([])
    setToolsUsed([])

    // 添加用户消息
    const userMsg: Message = { role: 'user', content: content.trim() }
    setMessages(prev => [...prev, userMsg])
    setIsStreaming(true)

    let buffer = ''
    let assistantContent = ''
    const steps: ThinkingStep[] = []
    const usedTools: string[] = []
    let finalSources: Source[] = []

    try {
      const response = await agentApi.chatStream(content.trim(), currentSessionId || undefined)

      if (!response.ok || !response.body) {
        throw new Error(`请求失败: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 处理完整的SSE事件
        const events = parseSSEEvents(buffer)
        // 保留最后不完整的部分
        const lastNewline = buffer.lastIndexOf('\n\n')
        if (lastNewline !== -1) {
          buffer = buffer.slice(lastNewline + 2)
        }

        for (const evt of events) {
          switch (evt.event) {
            case 'metadata':
              if (evt.data.session_id && !currentSessionId) {
                setCurrentSessionId(evt.data.session_id)
              }
              break
            case 'thinking':
              steps.push({ step: evt.data.step, thought: evt.data.thought, type: 'thinking' })
              setThinkingSteps([...steps])
              break
            case 'tool_call':
              steps.push({
                step: evt.data.step,
                type: 'tool_call',
                tool: evt.data.tool,
                arguments: evt.data.arguments,
              })
              setThinkingSteps([...steps])
              break
            case 'tool_result':
              const lastCall = [...steps].reverse().find(s => s.type === 'tool_call' && s.tool === evt.data.tool)
              if (lastCall) {
                lastCall.result = evt.data.result
                lastCall.duration_ms = evt.data.duration_ms
                lastCall.status = evt.data.success === false ? 'error' : 'success'
                if (evt.data.error) lastCall.error = evt.data.error
              }
              if (evt.data.tool && !usedTools.includes(evt.data.tool)) {
                usedTools.push(evt.data.tool)
              }
              setThinkingSteps([...steps])
              setToolsUsed([...usedTools])
              break
            case 'token':
              assistantContent += evt.data.content
              setStreamingContent(assistantContent)
              break
            case 'done':
              assistantContent = evt.data.content || assistantContent
              finalSources = evt.data.sources || []
              setSources(finalSources)
              setStreamingContent(assistantContent)
              break
            case 'error':
              setError(evt.data.error || '发生错误')
              break
          }
        }
      }

      // 添加AI回复
      if (assistantContent) {
        const aiMsg: Message = {
          role: 'assistant',
          content: assistantContent,
          tool_calls: usedTools.map(name => ({ name, arguments: {} })),
        }
        setMessages(prev => [...prev, aiMsg])
      }
    } catch (e: any) {
      setError(e.message || '对话失败')
      console.error('对话错误:', e)
    } finally {
      setIsStreaming(false)
      setStreamingContent('')
    }
  }, [currentSessionId, isStreaming])

  const stopGenerating = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setIsStreaming(false)
  }, [])

  const startNewSession = useCallback(() => {
    setMessages([])
    setStreamingContent('')
    setThinkingSteps([])
    setSources([])
    setToolsUsed([])
    setCurrentSessionId(null)
    setError(null)
  }, [])

  const loadSession = useCallback(async (sessionId: string) => {
    try {
      const detail = await agentApi.getSession(sessionId)
      setCurrentSessionId(sessionId)
      setMessages(detail.messages.map(m => ({
        role: m.role as any,
        content: m.content,
        tool_calls: m.tool_calls,
        created_at: m.created_at,
      })))
      setThinkingSteps([])
      setSources([])
      setStreamingContent('')
      setError(null)
    } catch (e) {
      console.error('加载会话失败', e)
    }
  }, [])

  return {
    messages,
    streamingContent,
    thinkingSteps,
    isStreaming,
    currentSessionId,
    sources,
    toolsUsed,
    error,
    sendMessage,
    stopGenerating,
    startNewSession,
    loadSession,
  }
}
