import { useEffect, useRef } from 'react'
import { useAgentChat } from '../hooks/useAgentChat'
import { useSessions } from '../hooks/useSessions'
import ChatMessage from '../components/chat/ChatMessage'
import ChatInput from '../components/chat/ChatInput'
import ThinkingProcess from '../components/chat/ThinkingProcess'
import SessionSidebar from '../components/chat/SessionSidebar'

const WELCOME_SUGGESTIONS = [
  '库容800万m³的水库，工程等别是多少？',
  'V等工程主要建筑物级别是多少？防洪标准怎么定？',
  '5级土石坝坝顶安全超高是多少？',
  '堤防工程边坡安全系数要求是多少？',
  '帮我查找《防洪标准》GB 50201-2014',
  '管涌险情怎么抢护？',
]

export default function Agent() {
  const {
    messages,
    streamingContent,
    thinkingSteps,
    isStreaming,
    currentSessionId,
    sources,
    error,
    sendMessage,
    stopGenerating,
    startNewSession,
    loadSession,
  } = useAgentChat()

  const { sessions, loading: sessionsLoading, loadSessions, deleteSession } = useSessions()

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent, thinkingSteps])

  // 会话变化时刷新列表
  useEffect(() => {
    if (currentSessionId) {
      loadSessions()
    }
  }, [currentSessionId, loadSessions])

  const handleSelectSession = async (id: string) => {
    await loadSession(id)
  }

  const handleNewSession = () => {
    startNewSession()
  }

  const handleDeleteSession = async (id: string) => {
    const success = await deleteSession(id)
    if (success && currentSessionId === id) {
      startNewSession()
    }
    loadSessions()
  }

  const isWelcome = messages.length === 0 && !isStreaming && !streamingContent

  return (
    <div className="h-[calc(100vh-4rem)] -m-8 flex overflow-hidden">
      {/* 会话侧边栏 */}
      <SessionSidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        loading={sessionsLoading}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
      />

      {/* 主聊天区 */}
      <div className="flex-1 flex flex-col bg-white">
        {/* 顶部标题 */}
        <div className="h-14 border-b border-neutral-200 flex items-center px-6 flex-shrink-0">
          <div className="flex items-center gap-2">
            <img src="/logo.jpg" alt="logo" className="w-8 h-8 rounded-lg object-cover border border-neutral-200" />
            <div>
              <h1 className="font-semibold text-[15px] text-neutral-900">智能助手</h1>
              <p className="text-[11px] text-neutral-500">基于Agent的多步推理水利专家</p>
            </div>
          </div>
        </div>

        {/* 消息区域 */}
        <div className="flex-1 overflow-y-auto">
          {isWelcome ? (
            // 欢迎界面
            <div className="h-full flex flex-col items-center justify-center px-6 py-12">
              <img src="/logo.jpg" alt="logo" className="w-20 h-20 rounded-2xl object-cover mb-6 shadow-lg border border-neutral-200" />
              <h2 className="text-2xl font-bold text-neutral-900 mb-2">你好，我是蜀水智能助手</h2>
              <p className="text-neutral-500 mb-8 text-center max-w-md">
                我可以检索水利规范、计算工程参数、匹配历史案例、查询防汛预案，帮您解决水利工程相关问题
              </p>
              <div className="grid grid-cols-2 gap-3 w-full max-w-xl">
                {WELCOME_SUGGESTIONS.map((suggestion, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(suggestion)}
                    className="text-left p-4 rounded-xl border border-neutral-200 hover:border-brand-300 hover:bg-brand-50 transition-all text-sm text-neutral-700 group"
                  >
                    <span className="group-hover:text-brand-700">{suggestion}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            // 消息列表
            <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">
              {messages.map((msg, i) => {
                const isLast = i === messages.length - 1
                const showStreaming = isLast && msg.role === 'assistant' && isStreaming
                return (
                  <div key={i}>
                    <ChatMessage
                      message={msg}
                      isStreaming={showStreaming}
                      streamingText={showStreaming ? streamingContent : undefined}
                      sources={isLast && !isStreaming ? sources : undefined}
                    />
                    {isLast && msg.role === 'assistant' && thinkingSteps.length > 0 && !isStreaming && (
                      <div className="ml-11 mt-2">
                        <ThinkingProcess steps={thinkingSteps} />
                      </div>
                    )}
                  </div>
                )
              })}

              {/* 流式中的思考过程 */}
              {isStreaming && thinkingSteps.length > 0 && (
                <div className="ml-11">
                  <ThinkingProcess steps={thinkingSteps} />
                </div>
              )}

              {/* 流式中的AI消息占位 */}
              {isStreaming && (messages.length === 0 || messages[messages.length - 1].role === 'user') && (
                <ChatMessage
                  message={{ role: 'assistant', content: '' }}
                  isStreaming={true}
                  streamingText={streamingContent}
                />
              )}

              {/* 错误提示 */}
              {error && (
                <div className="ml-11 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
                  {error}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区 */}
        <ChatInput
          onSend={sendMessage}
          onStop={stopGenerating}
          isStreaming={isStreaming}
          disabled={false}
        />
      </div>
    </div>
  )
}
