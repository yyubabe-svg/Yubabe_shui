import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  MessageSquare,
  Upload,
  ArrowRight,
  BookOpen,
  FolderSearch,
  ShieldAlert,
  FileCheck2,
  FileSpreadsheet,
  Database,
  Crown,
  HardDrive,
} from 'lucide-react'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'

interface Stats {
  total_documents: number
  total_qa_today: number
}

const actions = [
  { title: '知识问答', desc: '查询水利规范条文、工程参数', icon: BookOpen, path: '/qa', pro: false },
  { title: '文档入库', desc: '上传规范、报告、预案到知识库', icon: Upload, path: '/upload', pro: false },
  { title: '历史工程', desc: '检索历史工程档案与设计方案', icon: FolderSearch, path: '/projects', pro: false },
  { title: '防汛预案', desc: '查询防汛调度规程和应急预案', icon: ShieldAlert, path: '/flood', pro: false },
  { title: '合规审查', desc: '上传设计文件进行合规性初审', icon: FileCheck2, path: '/review', pro: true },
  { title: 'ISO 文档', desc: '自动填写ISO管理体系附表', icon: FileSpreadsheet, path: '/iso', pro: false },
]

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

export default function Dashboard() {
  const { user, openUpgrade } = useAuth()
  const [stats, setStats] = useState<Stats>({
    total_documents: 0,
    total_qa_today: 0,
  })

  useEffect(() => {
    api.get('/admin/stats')
      .then(res => setStats({
        total_documents: res.data.total_documents || 0,
        total_qa_today: res.data.total_qa_today || 0,
      }))
      .catch(() => {})
  }, [])

  if (!user) return null

  const storagePercent = Math.min(100, (user.total_upload_bytes / user.total_storage_limit) * 100)
  const qaPercent = user.is_pro ? 100 : (user.daily_qa_count / user.daily_qa_limit) * 100

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>工作台</h1>
        <p>你好，{user.name}！上传文档到知识库，然后通过问答快速查找信息</p>
      </div>

      {/* 个人额度 */}
      <div className="border border-neutral-200 bg-white mb-6">
        <div className="grid grid-cols-2 divide-x divide-neutral-200">
          <div className="px-6 py-4">
            <div className="flex items-center gap-2 text-neutral-500 text-xs mb-2">
              <MessageSquare className="w-3.5 h-3.5" strokeWidth={1.75} />
              {user.is_pro ? '知识问答（Pro 无限次）' : '今日问答'}
            </div>
            {user.is_pro ? (
              <div className="text-lg font-semibold text-brand-600 flex items-center gap-1.5">
                <Crown className="w-4 h-4" strokeWidth={1.75} />
                Pro 无限次
              </div>
            ) : (
              <>
                <div className="text-lg font-semibold text-neutral-900 tabular-nums">
                  {user.daily_qa_remaining} <span className="text-sm font-normal text-neutral-400">/ {user.daily_qa_limit} 次剩余</span>
                </div>
                <div className="mt-1.5 h-1 bg-neutral-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${qaPercent > 80 ? 'bg-amber-500' : 'bg-brand-500'}`}
                    style={{ width: `${qaPercent}%` }}
                  />
                </div>
              </>
            )}
          </div>
          <div className="px-6 py-4">
            <div className="flex items-center gap-2 text-neutral-500 text-xs mb-2">
              <HardDrive className="w-3.5 h-3.5" strokeWidth={1.75} />
              存储空间
            </div>
            <div className="text-lg font-semibold text-neutral-900 tabular-nums">
              {formatBytes(user.total_upload_bytes)} <span className="text-sm font-normal text-neutral-400">/ {formatBytes(user.total_storage_limit)}</span>
            </div>
            <div className="mt-1.5 h-1 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${storagePercent > 80 ? 'bg-amber-500' : 'bg-brand-500'}`}
                style={{ width: `${storagePercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* 知识库统计 */}
        <div className="grid grid-cols-2 divide-x divide-neutral-200 border-t border-neutral-100">
          <div className="px-6 py-3">
            <div className="flex items-center gap-2 text-neutral-500 text-xs mb-1">
              <Database className="w-3.5 h-3.5" strokeWidth={1.75} />
              知识库文档
            </div>
            <div className="text-base font-semibold text-neutral-700 tabular-nums">{stats.total_documents}</div>
          </div>
          <div className="px-6 py-3">
            <div className="flex items-center gap-2 text-neutral-500 text-xs mb-1">
              <MessageSquare className="w-3.5 h-3.5" strokeWidth={1.75} />
              今日问答（全系统）
            </div>
            <div className="text-base font-semibold text-neutral-700 tabular-nums">{stats.total_qa_today}</div>
          </div>
        </div>
      </div>

      {/* 升级提示条（免费版） */}
      {!user.is_pro && (
        <div className="flex items-center justify-between px-5 py-3 border border-amber-200 bg-amber-50 mb-6">
          <div className="flex items-center gap-2.5">
            <Crown className="w-4 h-4 text-amber-600" strokeWidth={1.75} />
            <div>
              <div className="text-sm font-medium text-amber-900">升级 Pro 解锁全部功能</div>
              <div className="text-xs text-amber-700 mt-0.5">无限问答 · 合规审查 · ISO文档 · 更大存储</div>
            </div>
          </div>
          <button onClick={() => openUpgrade()} className="btn-primary text-xs px-3 py-1.5">
            立即升级
          </button>
        </div>
      )}

      {/* 快捷功能 */}
      <div className="mb-8">
        <h2 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-3">功能入口</h2>
        <div className="border border-neutral-200 bg-white divide-y divide-neutral-100">
          {actions.map(action => {
            const Icon = action.icon
            const isLocked = action.pro && !user.is_pro
            return (
              <Link
                key={action.path}
                to={isLocked ? '#' : action.path}
                onClick={e => {
                  if (isLocked) {
                    e.preventDefault()
                    openUpgrade('合规审查为Pro专属功能')
                  }
                }}
                className="flex items-center gap-4 px-5 py-3.5 hover:bg-neutral-50 transition-colors group"
              >
                <Icon className="w-5 h-5 text-neutral-400 group-hover:text-brand-600 transition-colors flex-shrink-0" strokeWidth={1.75} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium text-neutral-900">{action.title}</span>
                    {isLocked && <Crown className="w-3 h-3 text-amber-500" strokeWidth={2} />}
                  </div>
                  <div className="text-xs text-neutral-500 mt-0.5">{action.desc}</div>
                </div>
                <ArrowRight className="w-4 h-4 text-neutral-300 group-hover:text-brand-600 group-hover:translate-x-0.5 transition-all" />
              </Link>
            )
          })}
        </div>
      </div>

      {/* 使用提示 */}
      <div className="flex items-center justify-between px-5 py-4 border border-neutral-200 bg-white">
        <div>
          <div className="text-sm font-medium text-neutral-900">开始使用</div>
          <div className="text-xs text-neutral-500 mt-0.5">先上传文档到知识库，再使用问答功能查询</div>
        </div>
        <Link to="/upload" className="btn-primary">
          <Upload className="w-4 h-4" strokeWidth={1.75} />
          上传文档
        </Link>
      </div>
    </div>
  )
}
