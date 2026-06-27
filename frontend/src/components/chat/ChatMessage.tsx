import { User } from 'lucide-react'
import MarkdownRenderer from '../MarkdownRenderer'
import StreamingText from './StreamingText'
import SourceList from './SourceList'
import type { Message, Source } from '../../types/agent'

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
  streamingText?: string
  sources?: Source[]
}

export default function ChatMessage({ message, isStreaming, streamingText, sources }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center overflow-hidden ${isUser ? 'bg-brand-600 text-white' : 'bg-white border border-neutral-200'}`}>
        {isUser ? <User className="w-4 h-4" /> : <img src="/logo.jpg" alt="AI" className="w-full h-full object-cover" />}
      </div>
      <div className={`flex-1 min-w-0 ${isUser ? 'flex flex-col items-end' : ''}`}>
        <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${isUser ? 'bg-brand-600 text-white rounded-tr-sm' : 'bg-white border border-neutral-200 rounded-tl-sm'}`}>
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <>
              {isStreaming && streamingText !== undefined ? (
                <div className="text-sm text-neutral-800">
                  <StreamingText text={streamingText} />
                </div>
              ) : (
                <MarkdownRenderer content={message.content} className={isUser ? 'text-white prose-p:text-white prose-headings:text-white' : 'text-neutral-800'} />
              )}
              {!isStreaming && sources && sources.length > 0 && (
                <SourceList sources={sources} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
