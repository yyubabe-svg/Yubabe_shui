import { useState, useCallback, useEffect } from 'react'
import { agentApi } from '../api/agent'
import type { ChatSession } from '../types/agent'

export function useSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [loading, setLoading] = useState(false)

  const loadSessions = useCallback(async () => {
    setLoading(true)
    try {
      const res = await agentApi.listSessions()
      setSessions(res.sessions)
    } catch (e) {
      console.error('加载会话列表失败', e)
    } finally {
      setLoading(false)
    }
  }, [])

  const deleteSession = useCallback(async (id: string) => {
    try {
      await agentApi.deleteSession(id)
      setSessions(prev => prev.filter(s => s.id !== id))
      return true
    } catch (e) {
      console.error('删除会话失败', e)
      return false
    }
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  return { sessions, loading, loadSessions, deleteSession }
}
