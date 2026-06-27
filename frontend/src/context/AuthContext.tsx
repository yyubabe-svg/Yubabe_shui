import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import api, { STORAGE_KEY, setUserName as saveUserName, clearUserName as clearStoredUser } from '../api/client'

export interface UsageData {
  name: string
  is_pro: boolean
  pro_expire_at: string | null
  pro_days_remaining: number | null
  total_upload_bytes: number
  total_storage_limit: number
  daily_qa_count: number
  daily_qa_limit: number
  daily_qa_remaining: number
  iso_used_count: number
  iso_free_limit: number
  has_pin: boolean
}

interface AuthContextType {
  user: UsageData | null
  userName: string | null
  isLoading: boolean
  showUpgrade: boolean
  upgradeReason: string
  login: (name: string, pin?: string, isNewPin?: boolean) => Promise<UsageData>
  logout: () => void
  activateCode: (code: string) => Promise<UsageData>
  refreshUsage: () => Promise<void>
  refreshProStatus: () => Promise<void>
  openUpgrade: (reason?: string) => void
  closeUpgrade: () => void
  checkFeature: (feature: string, fileSize?: number) => Promise<{ allowed: boolean; reason?: string }>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UsageData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showUpgrade, setShowUpgrade] = useState(false)
  const [upgradeReason, setUpgradeReason] = useState('')

  // 从localStorage读取保存的用户
  const getStoredUser = (): { name: string } | null => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) return JSON.parse(raw)
    } catch {}
    return null
  }

  // 初始化：尝试自动登录
  useEffect(() => {
    const stored = getStoredUser()
    if (stored?.name) {
      // 先保存到内存缓存
      saveUserName(stored.name)
      api.get('/usage/status')
        .then(res => {
          setUser(res.data)
          saveUserName(res.data.name)
        })
        .catch(() => {
          clearStoredUser()
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  // 监听全局升级事件
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      setUpgradeReason(detail?.reason || '')
      setShowUpgrade(true)
    }
    const authHandler = () => {
      setUser(null)
      clearStoredUser()
    }
    window.addEventListener('showUpgradeModal', handler)
    window.addEventListener('authError', authHandler)
    return () => {
      window.removeEventListener('showUpgradeModal', handler)
      window.removeEventListener('authError', authHandler)
    }
  }, [])

  const login = useCallback(async (name: string, pin?: string, isNewPin?: boolean): Promise<UsageData> => {
    console.log('[Auth] login called with name:', name)
    const res = await api.post('/usage/register', {
      name: name.trim(),
      pin: pin || undefined,
      is_new_pin: !!isNewPin,
    })
    const userData: UsageData = res.data
    console.log('[Auth] register response, userData:', userData)
    setUser(userData)
    console.log('[Auth] calling saveUserName with:', userData.name)
    saveUserName(userData.name)
    console.log('[Auth] login complete, user should be saved')
    return userData
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    clearStoredUser()
  }, [])

  const activateCode = useCallback(async (code: string): Promise<UsageData> => {
    const res = await api.post('/usage/activate', { code: code.trim() })
    const userData: UsageData = res.data
    setUser(userData)
    saveUserName(userData.name)
    return userData
  }, [])

  const refreshUsage = useCallback(async () => {
    try {
      const res = await api.get('/usage/status')
      setUser(res.data)
      saveUserName(res.data.name)
    } catch {}
  }, [])

  const refreshProStatus = refreshUsage

  const userName = user?.name || getStoredUser()?.name || null

  const openUpgrade = useCallback((reason?: string) => {
    setUpgradeReason(reason || '')
    setShowUpgrade(true)
  }, [])

  const closeUpgrade = useCallback(() => {
    setShowUpgrade(false)
    setUpgradeReason('')
  }, [])

  const checkFeature = useCallback(async (feature: string, fileSize?: number): Promise<{ allowed: boolean; reason?: string }> => {
    try {
      const params: Record<string, string | number> = { feature }
      if (fileSize) params.file_size = fileSize
      const res = await api.get('/usage/check', { params })
      return { allowed: res.data.allowed, reason: res.data.reason }
    } catch {
      return { allowed: false }
    }
  }, [])

  return (
    <AuthContext.Provider value={{
      user,
      userName,
      isLoading,
      showUpgrade,
      upgradeReason,
      login,
      logout,
      activateCode,
      refreshUsage,
      refreshProStatus,
      openUpgrade,
      closeUpgrade,
      checkFeature,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
