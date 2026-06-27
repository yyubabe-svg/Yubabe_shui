import { useState } from 'react'
import {
  Search, FileText, BookOpen, MessageSquare, Loader2,
  ChevronRight, Send, BookMarked, FileSpreadsheet, AlertCircle,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import { workspaceApi, type SearchResult, type AskResponse } from '../../api/workspace'
import MarkdownRenderer from '../../components/MarkdownRenderer'

const FILE_TYPE_OPTIONS = [
  { value: '', label: '全部类型' },
  { value: '水利规范', label: '规范标准' },
  { value: '历史工程报告', label: '工程报告' },
  { value: '设计说明书', label: '设计说明' },
  { value: '审查意见', label: '审查意见' },
  { value: '防汛预案', label: '防汛预案' },
]

type Mode = 'search' | 'qa'

export default function SearchPanel() {
  const { currentProject } = useProject()
  const [mode, setMode] = useState<Mode>('search')
  const [query, setQuery] = useState('')
  const [fileType, setFileType] = useState('')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<SearchResult[]>([])
  const [hasSearched, setHasSearched] = useState(false)

  // Q&A state
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [qaResult, setQaResult] = useState<AskResponse | null>(null)

  const projectId = currentProject?.id

  const handleSearch = async () => {
    if (!query.trim() || !projectId) return
    setSearching(true)
    setHasSearched(true)
    try {
      const res = await workspaceApi.search({
        q: query,
        project_id: projectId,
        file_types: fileType || undefined,
        limit: 20,
      })
      setResults(res.items)
    } catch (e: any) {
      console.error('搜索失败:', e)
      setResults([])
    } finally {
      setSearching(false)
    }
  }

  const handleAsk = async () => {
    if (!question.trim() || !projectId) return
    setAsking(true)
    try {
      const res = await workspaceApi.ask({
        question,
        project_id: projectId,
      })
      setQaResult(res)
    } catch (e: any) {
      console.error('问答失败:', e)
    } finally {
      setAsking(false)
    }
  }

  const getFileIcon = (title?: string) => {
    if (!title) return FileText
    const name = title.toLowerCase()
    if (name.includes('规范') || name.includes('标准') || name.includes('规程')) return BookOpen
    if (name.includes('审查') || name.includes('意见')) return AlertCircle
    if (name.includes('表格') || name.includes('清单')) return FileSpreadsheet
    return FileText
  }

  const highlightText = (text: string, keyword: string) => {
    if (!keyword.trim()) return text
    const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
    const parts = text.split(regex)
    return parts.map((part, i) =>
      regex.test(part) ? <mark key={i} className="bg-yellow-200 text-neutral-900 px-0.5 rounded">{part}</mark> : part
    )
  }

  return (
    <div className="space-y-5">
      {/* 模式切换 */}
      <div className="panel p-1 inline-flex gap-1">
        <button
          onClick={() => setMode('search')}
          className={`flex items-center gap-1.5 px-4 py-1.5 text-sm rounded transition-colors ${
            mode === 'search' ? 'bg-brand-600 text-white' : 'text-neutral-600 hover:bg-neutral-100'
          }`}
        >
          <Search className="w-4 h-4" strokeWidth={1.75} />
          资料检索
        </button>
        <button
          onClick={() => setMode('qa')}
          className={`flex items-center gap-1.5 px-4 py-1.5 text-sm rounded transition-colors ${
            mode === 'qa' ? 'bg-brand-600 text-white' : 'text-neutral-600 hover:bg-neutral-100'
          }`}
        >
          <MessageSquare className="w-4 h-4" strokeWidth={1.75} />
          知识问答
        </button>
      </div>

      {mode === 'search' ? (
        <>
          {/* 搜索框 */}
          <div className="panel p-4">
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                <input
                  type="text"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  placeholder="输入关键词搜索规范、报告、计算书、审查意见…"
                  className="input pl-9"
                />
              </div>
              <select value={fileType} onChange={e => setFileType(e.target.value)} className="input max-w-[140px]">
                {FILE_TYPE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <button onClick={handleSearch} disabled={searching || !query.trim()} className="btn-primary px-5">
                {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" strokeWidth={2} />}
                搜索
              </button>
            </div>
            <p className="text-xs text-neutral-400 mt-2">
              提示：搜索范围包含项目内资料和水利规范知识库，项目内文档优先返回
            </p>
          </div>

          {/* 搜索结果 */}
          {searching ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 text-brand-600 animate-spin" />
            </div>
          ) : hasSearched ? (
            results.length === 0 ? (
              <div className="panel">
                <div className="empty-state py-12">
                  <BookMarked className="empty-state-icon" strokeWidth={1.5} />
                  <p className="empty-state-text">未找到相关资料，试试换个关键词</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-xs text-neutral-500">
                  找到 <span className="font-semibold text-neutral-700">{results.length}</span> 条结果
                </div>
                {results.map((r, i) => {
                  const Icon = getFileIcon(r.title)
                  return (
                    <div key={i} className="panel p-4 hover:border-brand-300 transition-colors">
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded bg-brand-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Icon className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <h4 className="text-sm font-medium text-neutral-900 truncate">{r.title}</h4>
                            {r.page_number && (
                              <span className="text-xs text-neutral-400">第 {r.page_number} 页</span>
                            )}
                            {r.section_title && (
                              <span className="text-xs text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded">
                                {r.section_title}
                              </span>
                            )}
                            {r.score !== undefined && (
                              <span className="text-xs text-neutral-400 ml-auto">
                                相关度: {(r.score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-neutral-600 leading-relaxed line-clamp-3">
                            {highlightText(r.text || '', query)}
                          </p>
                          {r.chapter_path && (
                            <p className="text-xs text-neutral-400 mt-1.5">{r.chapter_path}</p>
                          )}
                        </div>
                        <ChevronRight className="w-4 h-4 text-neutral-300 flex-shrink-0 mt-1" />
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          ) : (
            <div className="panel">
              <div className="empty-state py-12">
                <Search className="empty-state-icon" strokeWidth={1.5} />
                <p className="empty-state-text">输入关键词开始搜索项目资料</p>
                <div className="flex flex-wrap gap-2 justify-center mt-4">
                  {['防洪标准', '工程等级', '护岸结构', '设计洪峰流量', '糙率选取', '堤顶高程'].map(kw => (
                    <button
                      key={kw}
                      onClick={() => { setQuery(kw); setTimeout(handleSearch, 100) }}
                      className="text-xs px-3 py-1 rounded-full bg-neutral-100 text-neutral-600 hover:bg-brand-50 hover:text-brand-600 transition-colors"
                    >
                      {kw}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          {/* 知识问答 */}
          <div className="panel p-4">
            <div className="flex gap-3">
              <div className="relative flex-1">
                <MessageSquare className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                <input
                  type="text"
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleAsk()}
                  placeholder="向水利专家助手提问，如：小型水库除险加固初设报告一般包含哪些章节？"
                  className="input pl-9"
                />
              </div>
              <button onClick={handleAsk} disabled={asking || !question.trim()} className="btn-primary px-5">
                {asking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" strokeWidth={2} />}
                提问
              </button>
            </div>
            <p className="text-xs text-neutral-400 mt-2">
              基于项目内资料和水利规范知识库回答，引用规范条文时会注明来源
            </p>
          </div>

          {/* 问答结果 */}
          {asking ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 text-brand-600 animate-spin" />
              <span className="ml-2 text-sm text-neutral-500">AI 正在思考…</span>
            </div>
          ) : qaResult ? (
            <div className="space-y-4">
              <div className="panel p-5">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center">
                    <MessageSquare className="w-3.5 h-3.5 text-white" strokeWidth={2} />
                  </div>
                  <span className="text-sm font-medium text-neutral-900">AI 回答</span>
                </div>
                <div className="prose prose-sm max-w-none text-neutral-700 leading-relaxed">
                  <MarkdownRenderer content={qaResult.answer} />
                </div>
              </div>

              {qaResult.sources && qaResult.sources.length > 0 && (
                <div className="panel p-4">
                  <h4 className="text-sm font-medium text-neutral-900 mb-3 flex items-center gap-1.5">
                    <BookOpen className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
                    参考来源
                  </h4>
                  <div className="space-y-2">
                    {qaResult.sources.map((s, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm p-2 rounded bg-neutral-50">
                        <FileText className="w-3.5 h-3.5 text-neutral-400 mt-0.5 flex-shrink-0" />
                        <div className="min-w-0">
                          <span className="text-neutral-700 font-medium">{s.title}</span>
                          {s.page_number && <span className="text-neutral-400 ml-2">第{s.page_number}页</span>}
                          {s.section && <span className="text-brand-600 ml-2 text-xs">{s.section}</span>}
                          {s.snippet && (
                            <p className="text-xs text-neutral-500 mt-1 line-clamp-2">{s.snippet}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="panel">
              <div className="empty-state py-12">
                <MessageSquare className="empty-state-icon" strokeWidth={1.5} />
                <p className="empty-state-text">向 AI 助手提问，获取专业解答</p>
                <div className="flex flex-wrap gap-2 justify-center mt-4">
                  {[
                    '山洪沟治理需要重点引用哪些规范？',
                    '防洪标准怎么确定？',
                    '明渠均匀流怎么计算？',
                    '工程特性表包含哪些内容？',
                  ].map(q => (
                    <button
                      key={q}
                      onClick={() => { setQuestion(q); setTimeout(handleAsk, 100) }}
                      className="text-xs px-3 py-1 rounded-full bg-neutral-100 text-neutral-600 hover:bg-brand-50 hover:text-brand-600 transition-colors max-w-full"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
