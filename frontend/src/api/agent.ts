import api, { STORAGE_KEY } from './client'
import type { ChatSession, ChatSessionDetail, SyncChatResponse, ToolSchema, Message } from '../types/agent'

// 获取当前登录用户名
function getCurrentUserName(): string {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const data = JSON.parse(raw)
      if (data.name) return data.name
    }
  } catch {}
  return 'default_user'
}

export const agentApi = {
  // 同步对话
  chatSync: (message: string, sessionId?: string) =>
    api.post<SyncChatResponse>('/agent/chat/sync', {
      message,
      session_id: sessionId,
      user_name: getCurrentUserName(),
    }).then(r => r.data),

  // 获取会话列表
  listSessions: (limit = 50) =>
    api.get<{ sessions: ChatSession[]; total: number }>('/agent/sessions', {
      params: { user_name: getCurrentUserName(), limit },
    }).then(r => r.data),

  // 获取会话详情
  getSession: (sessionId: string) =>
    api.get<ChatSessionDetail>(`/agent/sessions/${sessionId}`).then(r => r.data),

  // 删除会话
  deleteSession: (sessionId: string) =>
    api.delete(`/agent/sessions/${sessionId}`).then(r => r.data),

  // 获取工具列表
  listTools: () =>
    api.get<{ tools: ToolSchema[]; total: number }>('/agent/tools').then(r => r.data),

  // SSE流式对话 - 返回fetch Response供流式读取
  chatStream: (message: string, sessionId?: string, signal?: AbortSignal) => {
    const userName = getCurrentUserName()
    const encodedUserName = encodeURIComponent(userName)
    return fetch('/api/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Name': encodedUserName,
        'X-Username': encodedUserName,
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        user_name: userName,
      }),
      signal,
    })
  },
}
