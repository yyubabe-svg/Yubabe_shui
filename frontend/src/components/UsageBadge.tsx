import { useState } from 'react'
import { Crown, LogOut, ChevronUp, User } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

export default function UsageBadge() {
  const { user, openUpgrade, logout } = useAuth()
  const [showMenu, setShowMenu] = useState(false)

  if (!user) return null

  const isPro = user.is_pro
  const daysRemaining = user.pro_days_remaining
  const isExpiring = isPro && daysRemaining !== null && daysRemaining <= 3
  const storageUsed = formatBytes(user.total_upload_bytes)
  const storageLimit = formatBytes(user.total_storage_limit)

  return (
    <div className="px-3 py-3 border-t border-neutral-200 relative">
      <button
        onClick={() => {
          if (!isPro) {
            openUpgrade()
          } else {
            setShowMenu(!showMenu)
          }
        }}
        className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md transition-colors text-left ${
          isPro
            ? (isExpiring ? 'bg-amber-50 hover:bg-amber-100' : 'bg-brand-50 hover:bg-brand-100')
            : 'bg-neutral-50 hover:bg-neutral-100'
        }`}
      >
        {isPro ? (
          <Crown className={`w-4 h-4 flex-shrink-0 ${isExpiring ? 'text-amber-600' : 'text-brand-600'}`} strokeWidth={1.75} />
        ) : (
          <User className="w-4 h-4 flex-shrink-0 text-neutral-500" strokeWidth={1.75} />
        )}
        <div className="flex-1 min-w-0">
          <div className={`text-xs font-medium truncate ${isPro ? (isExpiring ? 'text-amber-800' : 'text-brand-700') : 'text-neutral-700'}`}>
            {user.name}
            {isPro && (
              <span className={`ml-1 ${isExpiring ? 'text-amber-600' : 'text-brand-500'}`}>
                · Pro
              </span>
            )}
          </div>
          <div className={`text-[11px] truncate ${isPro ? (isExpiring ? 'text-amber-600' : 'text-brand-500') : 'text-neutral-400'}`}>
            {isPro ? (
              isExpiring
                ? `Pro即将到期（${daysRemaining}天）`
                : `Pro · 剩余${daysRemaining}天`
            ) : (
              `今日剩余${user.daily_qa_remaining}次 · ${storageUsed}/${storageLimit}`
            )}
          </div>
        </div>
        {isPro && (
          <ChevronUp className={`w-3.5 h-3.5 flex-shrink-0 text-neutral-400 transition-transform ${showMenu ? '' : 'rotate-180'}`} />
        )}
      </button>

      {/* Pro 用户下拉菜单 */}
      {isPro && showMenu && (
        <div className="absolute bottom-full left-3 right-3 mb-1 bg-white border border-neutral-200 rounded-md shadow-lg overflow-hidden">
          <div className="px-3 py-2.5 border-b border-neutral-100">
            <div className="text-xs text-neutral-500">存储使用</div>
            <div className="mt-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full"
                style={{ width: `${Math.min(100, (user.total_upload_bytes / user.total_storage_limit) * 100)}%` }}
              />
            </div>
            <div className="text-[11px] text-neutral-400 mt-1">{storageUsed} / {storageLimit}</div>
          </div>
          <button
            onClick={() => { setShowMenu(false); logout() }}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" strokeWidth={1.75} />
            切换账号
          </button>
        </div>
      )}

      {/* 点击外部关闭菜单 */}
      {showMenu && (
        <div className="fixed inset-0 z-[-1]" onClick={() => setShowMenu(false)} />
      )}
    </div>
  )
}
