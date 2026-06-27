import { Settings, Database, Users, Cog } from 'lucide-react'

const modules = [
  { title: '文档管理', desc: '查看、删除、重建知识库文档索引', icon: Database },
  { title: '用户管理', desc: '管理系统用户、权限和角色', icon: Users },
  { title: '系统配置', desc: 'LLM 模型配置、向量库重建、系统参数', icon: Cog },
]

export default function Admin() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1>系统管理</h1>
        <p>文档管理、用户管理与系统配置</p>
      </div>

      <div className="border border-neutral-200 bg-white divide-y divide-neutral-100">
        {modules.map(m => {
          const Icon = m.icon
          return (
            <div key={m.title} className="flex items-center gap-4 px-5 py-4 hover:bg-neutral-50 transition-colors cursor-pointer">
              <div className="w-9 h-9 rounded-md bg-neutral-100 flex items-center justify-center flex-shrink-0">
                <Icon className="w-[18px] h-[18px] text-neutral-600" strokeWidth={1.75} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-neutral-900">{m.title}</div>
                <div className="text-xs text-neutral-500 mt-0.5">{m.desc}</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
