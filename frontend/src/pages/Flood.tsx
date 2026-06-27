import { useState } from 'react'
import { ShieldAlert, Send, AlertTriangle } from 'lucide-react'
import api from '../api/client'

export default function Flood() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)

  const handleQuery = async () => {
    if (!query.trim()) return
    setLoading(true)
    try {
      const { data } = await api.post('/flood/query', { query })
      setAnswer(data.answer)
    } catch {
      setAnswer('查询失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container max-w-3xl">
      <div className="page-header">
        <h1>防汛预案</h1>
        <p>查询防汛调度规程和应急预案相关内容</p>
      </div>

      <div className="border border-neutral-200 bg-white p-6">
        <div className="flex gap-2 mb-5">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleQuery()}
            placeholder="例如：水位超过汛限水位应如何调度？"
            className="flex-1 input"
          />
          <button onClick={handleQuery} disabled={loading} className="btn-primary px-4">
            {loading ? (
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Send className="w-4 h-4" strokeWidth={1.75} />
            )}
            查询
          </button>
        </div>

        {answer && (
          <div className="border-t border-neutral-100 pt-5">
            <div className="flex items-center gap-2 text-xs text-neutral-500 mb-2">
              <ShieldAlert className="w-3.5 h-3.5" strokeWidth={1.75} />
              查询结果
            </div>
            <div className="whitespace-pre-wrap text-sm text-neutral-800 leading-relaxed bg-neutral-50 p-4 rounded">
              {answer}
            </div>
          </div>
        )}

        <div className="mt-4 flex items-start gap-1.5 text-[11px] text-neutral-400">
          <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" strokeWidth={1.75} />
          <p>本系统仅提供辅助查询，最终调度决策应由防汛责任人确认</p>
        </div>
      </div>
    </div>
  )
}
