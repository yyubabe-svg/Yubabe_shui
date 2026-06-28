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

  // SSE事件解析器：正确处理\r\n、空行分隔符、不完整片段
  const parseSSEEvents = (buffer: string): { events: Array<{ event: string; data: any }>; remaining: string } => {
    const events: Array<{ event: string; data: any }> = []
    const lines = buffer.split('\n')
    let currentEvent = 'message'
    let currentData = ''
    let i = 0

    for (; i < lines.length - 1; i++) {
      // 不处理最后一行（可能不完整）
      let line = lines[i].replace(/\r$/, '') // 去除CRLF的\r

      if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        currentData += line.slice(5).trim()
      } else if (line === '') {
        // 空行 - 事件结束分隔符
        if (currentData) {
          try {
            events.push({ event: currentEvent, data: JSON.parse(currentData) })
          } catch (e) {
            // 非JSON数据，作为纯文本推送
            events.push({ event: currentEvent, data: currentData })
          }
          currentData = ''
          currentEvent = 'message'
        }
      }
    }

    // 返回已处理的事件和剩余未处理的buffer
    const remaining = lines.slice(i).join('\n')
    return { events, remaining }
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

    // 修复5：在sendMessage开头创建AbortController
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    let buffer = ''
    let assistantContent = ''
    const steps: ThinkingStep[] = []
    const usedTools: string[] = []
    let finalSources: Source[] = []

    try {
      const response = await agentApi.chatStream(content.trim(), currentSessionId || undefined, abortController.signal)

      if (!response.ok || !response.body) {
        throw new Error(`请求失败: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 使用新的SSE解析器，正确维护buffer
        const { events, remaining } = parseSSEEvents(buffer)
        buffer = remaining

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

      // 修复6：先添加最终AI消息，再清空streamingContent
      if (assistantContent) {
        const aiMsg: Message = {
          role: 'assistant',
          content: assistantContent,
          tool_calls: usedTools.map(name => ({ name, arguments: {} })),
        }
        setMessages(prev => [...prev, aiMsg])
      }
      setStreamingContent('')
    } catch (e: any) {
      if (e.name === 'AbortError') {
        // 用户主动停止，将已有内容作为最终消息
        if (assistantContent) {
          const aiMsg: Message = {
            role: 'assistant',
            content: assistantContent,
            tool_calls: usedTools.map(name => ({ name, arguments: {} })),
          }
          setMessages(prev => [...prev, aiMsg])
        }
      } else {
        setError(e.message || '对话失败')
        console.error('对话错误:', e)
      }
    } finally {
      setIsStreaming(false)
      setStreamingContent('')
      abortControllerRef.current = null
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
