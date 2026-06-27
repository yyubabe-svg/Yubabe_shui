import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function WelcomeScreen() {
  const { login } = useAuth()
  const [name, setName] = useState('')
  const [pin, setPin] = useState('')
  const [showPin, setShowPin] = useState(false)
  const [isNewPin, setIsNewPin] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || name.trim().length < 2) {
      setError('请输入姓名（至少2个字）')
      return
    }
    setLoading(true)
    setError('')
    try {
      await login(name.trim(), pin || undefined, isNewPin)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '登录失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-neutral-50 flex items-center justify-center z-50">
      <div className="w-full max-w-sm px-8">
        {/* Logo & Brand */}
        <div className="text-center mb-10">
          <img src="/logo.jpg" alt="logo" className="w-16 h-16 rounded-xl object-cover mx-auto mb-5 shadow-md border border-neutral-200" />
          <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight mb-1.5">蜀水智库 AI</h1>
          <p className="text-sm text-neutral-500">水利勘测设计智能助手</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">您的姓名</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="input"
              placeholder="请输入真实姓名，如：张三"
              autoFocus
              maxLength={20}
            />
          </div>

          {!showPin ? (
            <button
              type="button"
              onClick={() => { setShowPin(true); setIsNewPin(false) }}
              className="text-xs text-neutral-500 hover:text-brand-600 transition-colors"
            >
              设置/输入PIN码（防止同名，可选）
            </button>
          ) : (
            <div>
              <label className="label">PIN码（4-6位数字）</label>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={pin}
                  onChange={e => setPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="input flex-1"
                  placeholder={isNewPin ? '设置新PIN码' : '请输入PIN码'}
                  maxLength={6}
                  inputMode="numeric"
                />
                <button
                  type="button"
                  onClick={() => { setShowPin(false); setPin(''); setIsNewPin(false) }}
                  className="btn-ghost px-2 text-xs"
                >
                  取消
                </button>
              </div>
              <label className="flex items-center gap-1.5 mt-2 text-xs text-neutral-500 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isNewPin}
                  onChange={e => setIsNewPin(e.target.checked)}
                  className="rounded border-neutral-300"
                />
                首次设置PIN码（新用户勾选）
              </label>
            </div>
          )}

          {error && (
            <div className="text-xs text-danger bg-red-50 border border-red-100 px-3 py-2 rounded">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !name.trim()}
            className="btn-primary w-full py-2.5"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                进入中…
              </>
            ) : '开始使用'}
          </button>
        </form>

        <p className="text-xs text-neutral-400 text-center mt-6 leading-relaxed">
          首次使用输入姓名即可，换设备输入相同姓名可恢复数据。
          <br />
          知识库文档为单位内部共享资源。
        </p>
      </div>
    </div>
  )
}
