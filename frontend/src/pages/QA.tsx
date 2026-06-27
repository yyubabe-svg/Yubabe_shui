import { useState, useRef, useEffect } from 'react'
import { Send, FileText, AlertTriangle, Sparkles, Crown } from 'lucide-react'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'

interface Source {
  file_name: string
  page_number?: number
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
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const qaDisabled = !user?.is_pro && (user?.daily_qa_remaining ?? 0) <= 0

  const handleSend = async (question?: string) => {
    const q = (question || input).trim()
    if (!q || loading) return
    if (qaDisabled) {
      openUpgrade('今日免费问答次数已用完，升级Pro不限次数')
      return
    }

    setInput('')
    setLoading(true)
    setMessages(prev => [...prev, { role: 'user', content: q }])

    try {
      const res = await api.post('/qa/query', { question: q })
      setMessages(prev => [...prev, {
        role: 'ai',
        content: res.data.answer,
        sources: res.data.sources,
      }])
      // 刷新额度
      refreshUsage()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setMessages(prev => [...prev, {
        role: 'ai',
        content: detail?.includes('升级') ? detail : '抱歉，问答服务暂时不可用，请稍后重试。',
      }])
    } finally {
      setLoading(false)
    }
  }

  if (!user) return null

  return (
    <div className="page-container h-[calc(100vh-7rem)] flex flex-col">
      <div className="page-header mb-4 flex-shrink-0 flex items-start justify-between">
        <div>
          <h1>知识问答</h1>
          <p>基于本地知识库的 RAG 问答，回答附带来源引用</p>
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
                      {msg.sources.slice(0, 3).map((s, j) => (
                        <div key={j} className="text-xs bg-neutral-50 px-2.5 py-2 rounded">
                          <p className="font-medium text-neutral-700">
                            {s.file_name}
                            {s.page_number && <span className="text-neutral-400 ml-1">· 第{s.page_number}页</span>}
                          </p>
                          <p className="text-neutral-500 mt-0.5 leading-relaxed">{s.text?.substring(0, 120)}…</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
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
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white border border-neutral-200 text-neutral-600 rounded-md hover:border-brand-400 hover:text-brand-700 hover:bg-brand-50/50 transition-colors"
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
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder={qaDisabled ? "今日次数已用完，升级Pro继续使用" : "输入问题，按 Enter 发送..."}
          className="flex-1 input"
          disabled={loading || qaDisabled}
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
