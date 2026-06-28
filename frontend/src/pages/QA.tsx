import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, FileText, AlertTriangle, Sparkles, Crown } from 'lucide-react'
import api, { getStoredUserName, triggerUpgrade, triggerAuthError } from '../api/client'
import { useAuth } from '../context/AuthContext'

interface Source {
  file_name: string
  page_number?: number
  section_title?: string
  text: string
  score: number
}

interface Message {
  role: 'user' | 'ai'
  content: string
  sources?: Source[]
}

const QUICK_QUESTIONS = [
  '小型水库除险加固设计需要重点参考哪些规范？',
  '堤防工程的防洪标准如何确定？',
  '水利工程质量控制分级标准是什么？',
]

// SSE事件解析器（与Agent页面一致的实现）
function parseSSEEvents(buffer: string): { events: Array<{event: string, data: any}>, remaining: string } {
  const events: Array<{event: string, data: any}> = []
  const lines = buffer.split('\n')
  let currentEvent = 'message'
  let currentData = ''
  let i = 0

  for (; i < lines.length - 1; i++) {
    let line = lines[i].replace(/\r$/, '')

    if (line.startsWith('event:')) {
      currentEvent = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      currentData += line.slice(5).trim()
    } else if (line === '') {
      if (currentData) {
        try {
          events.push({ event: currentEvent, data: JSON.parse(currentData) })
        } catch (e) {}
        currentData = ''
        currentEvent = 'message'
      }
    }
  }

  const remaining = lines.slice(i).join('\n')
  return { events, remaining }
}

export default function QA() {
  const { user, openUpgrade, refreshUsage } = useAuth()
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'ai',
      content: '您好，我是蜀水智库 AI 助手。可以查询水利规范条文、检索历史工程、解答防汛预案相关问题。请输入问题，或点击下方快捷问题开始。',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [currentSources, setCurrentSources] = useState<Source[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 自动滚动：流式期间瞬间跳转，完成后smooth
  useEffect(() => {
    if (loading || streamingContent) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
    } else {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, streamingContent, loading])

  const qaDisabled = !user?.is_pro && (user?.daily_qa_remaining ?? 0) <= 0

  const handleSend = useCallback(async (question?: string) => {
    const q = (question || input).trim()
    if (!q || loading) return
    if (qaDisabled) {
      openUpgrade('今日免费问答次数已用完，升级Pro不限次数')
      return
    }

    setInput('')
    setLoading(true)
    setStreamingContent('')
    setCurrentSources([])
    setMessages(prev => [...prev, { role: 'user', content: q }])

    const abortController = new AbortController()
    abortRef.current = abortController

    try {
      const name = getStoredUserName()
      const encodedName = name ? encodeURIComponent(name) : ''
      
      const response = await fetch('/api/qa/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': encodedName,
          'X-Username': encodedName,
        },
        body: JSON.stringify({ question: q, top_k: 5 }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorMsg = '抱歉，问答服务暂时不可用，请稍后重试。'
        try {
          const errJson = JSON.parse(errorText)
          if (errJson.detail) {
            errorMsg = errJson.detail
            if (errorMsg.includes('升级')) {
              triggerUpgrade(undefined, errorMsg)
              setLoading(false)
              setStreamingContent('')
              return
            }
          }
        } catch {}
        if (response.status === 401) {
          triggerAuthError()
          return
        }
        throw new Error(errorMsg)
      }

      if (!response.body) {
        throw new Error('响应体为空')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullAnswer = ''
      let sources: Source[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const { events, remaining } = parseSSEEvents(buffer)
        buffer = remaining

        for (const evt of events) {
          if (evt.event === 'sources') {
            sources = evt.data || []
            setCurrentSources(sources)
          } else if (evt.event === 'token') {
            const token = evt.data?.content || ''
            fullAnswer += token
            setStreamingContent(fullAnswer)
          } else if (evt.event === 'error') {
            throw new Error(evt.data?.error || 'AI回答生成失败')
          } else if (evt.event === 'done') {
            fullAnswer = evt.data?.content || fullAnswer
          }
        }
      }

      // 完成：添加最终消息
      setMessages(prev => [...prev, {
        role: 'ai',
        content: fullAnswer || '抱歉，未能生成有效回答。',
        sources: sources.length > 0 ? sources : undefined,
      }])
      setStreamingContent('')
      setCurrentSources([])
      refreshUsage()

    } catch (err: any) {
      if (err.name === 'AbortError') {
        // 用户主动停止，保留已生成内容
        if (streamingContent) {
          setMessages(prev => [...prev, {
            role: 'ai',
            content: streamingContent + '\n\n[已停止生成]',
            sources: currentSources.length > 0 ? currentSources : undefined,
          }])
        }
      } else {
        const detail = err?.message || '抱歉，问答服务暂时不可用，请稍后重试。'
        setMessages(prev => [...prev, {
          role: 'ai',
          content: detail.includes('升级') ? detail : '抱歉，问答服务暂时不可用，请稍后重试。',
        }])
      }
      setStreamingContent('')
      setCurrentSources([])
    } finally {
      setLoading(false)
      abortRef.current = null
      // 发送后自动聚焦输入框
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [input, loading, qaDisabled, openUpgrade, refreshUsage, streamingContent, currentSources])

  if (!user) return null

  return (
    <div className="page-container h-[calc(100vh-7rem)] flex flex-col">
      <div className="page-header mb-4 flex-shrink-0 flex items-start justify-between">
        <div>
          <h1>知识问答</h1>
          <p>基于本地知识库的 RAG 问答，回答附带来源引用（流式输出）</p>
        </div>
        {!user.is_pro && (
          <div className="text-xs text-neutral-500 bg-neutral-50 border border-neutral-200 px-3 py-1.5 rounded">
            今日剩余 <span className={`font-semibold ${user.daily_qa_remaining <= 3 ? 'text-warning' : 'text-neutral-700'}`}>{user.daily_qa_remaining}</span> 次
          </div>
        )}
        {user.is_pro && (
          <div className="text-xs text-brand-600 bg-brand-50 border border-brand-100 px-3 py-1.5 rounded flex items-center gap-1">
            <Crown className="w-3 h-3" strokeWidth={2} />
            Pro 无限次
          </div>
        )}
      </div>

      {/* 次数用完提示 */}
      {qaDisabled && (
        <div className="flex items-center justify-between px-5 py-3 border border-amber-200 bg-amber-50 mb-4 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <Crown className="w-4 h-4 text-amber-600" strokeWidth={1.75} />
            <div>
              <div className="text-sm font-medium text-amber-900">今日问答次数已用完</div>
              <div className="text-xs text-amber-700 mt-0.5">升级Pro版不限问答次数</div>
            </div>
          </div>
          <button onClick={() => openUpgrade('今日免费问答次数已用完')} className="btn-primary text-xs px-3 py-1.5">
            升级 Pro
          </button>
        </div>
      )}

      {/* 消息区域 */}
      <div className="flex-1 overflow-y-auto border border-neutral-200 bg-white px-6 py-5 mb-4">
        <div className="max-w-3xl mx-auto space-y-5">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] ${msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}`}>
                <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-neutral-200">
                    <p className="text-[11px] font-medium text-neutral-500 mb-2 flex items-center gap-1 uppercase tracking-wider">
                      <FileText className="w-3 h-3" /> 引用来源
                    </p>
                    <div className="space-y-1.5">
                      {msg.sources.slice(0, 5).map((s, j) => (
                        <div key={j} className="text-xs bg-neutral-50 px-2.5 py-2 rounded">
                          <p className="font-medium text-neutral-700">
                            {s.file_name}
                            {s.page_number && <span className="text-neutral-400 ml-1">· {s.page_number}</span>}
                          </p>
                          <p className="text-neutral-500 mt-0.5 leading-relaxed">{s.text?.substring(0, 150)}…</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {/* 流式输出中的消息 */}
          {loading && streamingContent && (
            <div className="flex justify-start">
              <div className="chat-bubble-ai max-w-[80%]">
                <div className="whitespace-pre-wrap leading-relaxed">{streamingContent}</div>
                <span className="inline-block w-2 h-4 bg-neutral-400 animate-pulse ml-0.5 align-middle" />
              </div>
            </div>
          )}

          {/* 加载中（等待首token） */}
          {loading && !streamingContent && (
            <div className="flex justify-start">
              <div className="chat-bubble-ai">
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" />
                  <div className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.12s' }} />
                  <div className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.24s' }} />
                </div>
              </div>
            </div>
          )}

          {/* 流式消息的引用来源（在token接收完之前显示） */}
          {loading && currentSources.length > 0 && streamingContent && (
            <div className="flex justify-start">
              <div className="chat-bubble-ai max-w-[80%] opacity-60">
                <p className="text-[11px] font-medium text-neutral-500 mb-2 flex items-center gap-1 uppercase tracking-wider">
                  <FileText className="w-3 h-3" /> 引用来源（生成中）
                </p>
                <div className="space-y-1.5">
                  {currentSources.slice(0, 5).map((s, j) => (
                    <div key={j} className="text-xs bg-neutral-50 px-2.5 py-2 rounded">
                      <p className="font-medium text-neutral-700">{s.file_name}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 快捷问题 */}
      {messages.length <= 1 && !qaDisabled && (
        <div className="mb-3 flex-shrink-0">
          <div className="flex flex-wrap gap-2">
            {QUICK_QUESTIONS.map((q, i) => (
              <button
                key={i}
                onClick={() => handleSend(q)}
                disabled={loading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white border border-neutral-200 text-neutral-600 rounded-md hover:border-brand-400 hover:text-brand-700 hover:bg-brand-50/50 transition-colors disabled:opacity-50"
              >
                <Sparkles className="w-3 h-3" strokeWidth={1.75} />
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 输入区 */}
      <div className="flex gap-2 flex-shrink-0">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder={qaDisabled ? "今日次数已用完，升级Pro继续使用" : "输入问题，按 Enter 发送..."}
          className="flex-1 input"
          disabled={loading || qaDisabled}
          autoFocus
        />
        <button
          onClick={() => handleSend()}
          disabled={loading || !input.trim() || qaDisabled}
          className="btn-primary px-4"
        >
          <Send className="w-4 h-4" strokeWidth={1.75} />
          发送
        </button>
      </div>

      {/* 免责声明 */}
      <div className="mt-2 flex items-start gap-1.5 text-[11px] text-neutral-400 flex-shrink-0">
        <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" strokeWidth={1.75} />
        <p>AI 回答仅供参考，涉及防汛调度、工程安全等重要决策，请以正式文件和专业人员判断为准。</p>
      </div>
    </div>
  )
}
