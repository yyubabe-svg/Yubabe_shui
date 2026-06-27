import { useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  MessageSquare,
  Upload,
  FolderSearch,
  ShieldAlert,
  FileCheck2,
  PanelLeftClose,
  PanelLeft,
  FileSpreadsheet,
  Crown,
  Box,
  Sparkles,
  Briefcase,
} from 'lucide-react'
import UsageBadge from './UsageBadge'
import { useAuth } from '../context/AuthContext'

interface NavItem {
  path: string
  label: string
  icon: any
  pro?: boolean
  badge?: string
}

interface NavGroup {
  title: string
  items: NavItem[]
}

const navGroups: NavGroup[] = [
  {
    title: '项目工作台',
    items: [
      { path: '/workspace', label: '我的项目', icon: Briefcase, badge: '推荐' },
    ]
  },
  {
    title: 'AI工具',
    items: [
      { path: '/agent', label: '智能助手', icon: Sparkles },
      { path: '/qa', label: '知识问答', icon: MessageSquare },
      { path: '/upload', label: '文档入库', icon: Upload },
      { path: '/iso', label: 'ISO填表', icon: FileSpreadsheet },
      { path: '/review', label: '合规审查', icon: FileCheck2, pro: true },
      { path: '/flood', label: '防汛预案', icon: ShieldAlert },
      { path: '/cad', label: '智能CAD', icon: Box },
    ]
  },
  {
    title: '其他',
    items: [
      { path: '/projects', label: '历史工程库', icon: FolderSearch },
    ]
  }
]

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const { user, openUpgrade } = useAuth()

  return (
    <div className="h-screen flex bg-neutral-50 text-neutral-900">
      {/* 侧边栏 */}
      <aside
        className={`${collapsed ? 'w-[60px]' : 'w-[220px]'} flex flex-col bg-white border-r border-neutral-200 transition-[width] duration-200 flex-shrink-0`}
      >
        {/* Logo 区 */}
        <div className="h-14 flex items-center justify-between px-3.5 border-b border-neutral-200 flex-shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <img src="/logo.jpg" alt="logo" className="w-8 h-8 rounded-full object-cover flex-shrink-0 border border-neutral-200" />
            {!collapsed && (
              <span className="font-semibold text-[15px] text-neutral-900 tracking-tight truncate">
                蜀水智库
              </span>
            )}
          </div>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded flex-shrink-0"
          >
            {collapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
          </button>
        </div>

        {/* 导航 */}
        <nav className="flex-1 p-2 overflow-y-auto">
          {navGroups.map((group, gi) => (
            <div key={group.title} className={gi > 0 ? 'mt-4' : ''}>
              {!collapsed && (
                <div className="px-3 py-1.5 text-[11px] font-medium text-neutral-400 uppercase tracking-wider">
                  {group.title}
                </div>
              )}
              <div className="space-y-0.5">
                {group.items.map(item => {
                  const Icon = item.icon
                  // 匹配 /workspace 和 /workspace/:id 都算激活
                  const isActive = item.path === '/workspace' 
                    ? location.pathname.startsWith('/workspace')
                    : location.pathname === item.path
                  const isProLocked = item.pro && user && !user.is_pro
                  const isHighlighted = item.badge === '推荐'
                  
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={`nav-item ${isActive ? 'nav-item-active' : ''} ${collapsed ? 'justify-center px-0' : ''} ${isProLocked ? 'opacity-70' : ''} ${isHighlighted && !isActive ? 'bg-brand-50/50' : ''}`}
                      title={collapsed ? item.label : undefined}
                      onClick={e => {
                        if (isProLocked) {
                          e.preventDefault()
                          openUpgrade('合规审查为Pro专属功能')
                        }
                      }}
                    >
                      <Icon className={`w-[18px] h-[18px] flex-shrink-0 ${isHighlighted && !isActive ? 'text-brand-600' : ''}`} strokeWidth={1.75} />
                      {!collapsed && (
                        <>
                          <span className="truncate flex-1">{item.label}</span>
                          {item.badge && !isActive && (
                            <span className="text-[9px] px-1 py-0.5 bg-brand-100 text-brand-700 rounded font-medium">
                              {item.badge}
                            </span>
                          )}
                          {isProLocked && (
                            <Crown className="w-3 h-3 text-amber-500 flex-shrink-0" strokeWidth={2} />
                          )}
                        </>
                      )}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* 底部用户状态 */}
        {!collapsed && <UsageBadge />}
        {collapsed && (
          <div className="px-3 py-3 border-t border-neutral-200 flex-shrink-0 flex justify-center">
            <button
              onClick={() => {
                if (user && !user.is_pro) openUpgrade()
              }}
              className={`w-8 h-8 rounded-md flex items-center justify-center ${
                user?.is_pro ? 'bg-brand-50 text-brand-600' : 'bg-neutral-100 text-neutral-500'
              }`}
              title={user?.is_pro ? 'Pro' : '免费版'}
            >
              {user?.is_pro ? (
                <Crown className="w-4 h-4" strokeWidth={1.75} />
              ) : (
                <span className="text-[10px] font-medium">免</span>
              )}
            </button>
          </div>
        )}
      </aside>

      {/* 主区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 页面内容 */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
