import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Send,
  ExternalLink,
  Copy,
  Check,
  Sparkles,
  Layers,
  Info,
  RefreshCw,
  Download,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import api from '../api/client'

interface CADTemplate {
  id: string
  name: string
  category: string
  description: string
  default_prompt: string
  icon: string
}

const CADAM_URL = 'https://adam.new/cadam'

export default function CAD() {
  const [description, setDescription] = useState('')
  const [generatedPrompt, setGeneratedPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [templates, setTemplates] = useState<CADTemplate[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedTemplate, setSelectedTemplate] = useState<CADTemplate | null>(null)
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({})
  const [showIframe, setShowIframe] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      const { data } = await api.get('/cad/templates')
      setTemplates(data.templates)
      setCategories(data.categories)
      // 默认展开第一个分类
      if (data.categories.length > 0) {
        setExpandedCategories({ [data.categories[0]]: true })
      }
    } catch (err) {
      console.error('加载模板失败:', err)
    }
  }

  const handleGenerate = async () => {
    if (!description.trim() && !selectedTemplate) return
    setLoading(true)
    try {
      const { data } = await api.post('/cad/generate-prompt', {
        description: description.trim(),
        template: selectedTemplate?.id || undefined,
      })
      setGeneratedPrompt(data.prompt)
      setShowIframe(true)
    } catch {
      // fallback: 使用模板默认 prompt 或简单构造
      const fallback = selectedTemplate
        ? selectedTemplate.default_prompt
        : `A parametric 3D model of ${description}, engineering details, high quality, manifold geometry suitable for 3D printing`
      setGeneratedPrompt(fallback)
      setShowIframe(true)
    } finally {
      setLoading(false)
    }
  }

  const handleTemplateClick = (template: CADTemplate) => {
    setSelectedTemplate(template)
    if (!description.trim()) {
      setDescription(template.description)
    }
  }

  const handleCopyPrompt = async () => {
    if (!generatedPrompt) return
    try {
      await navigator.clipboard.writeText(generatedPrompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }

  const handleOpenInCADAM = () => {
    // 在新窗口打开 CADAM
    window.open(CADAM_URL, '_blank')
  }

  const toggleCategory = (cat: string) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }))
  }

  const filteredTemplates = selectedCategory
    ? templates.filter(t => t.category === selectedCategory)
    : templates

  const groupedTemplates = categories.reduce<Record<string, CADTemplate[]>>((acc, cat) => {
    acc[cat] = templates.filter(t => t.category === cat)
    return acc
  }, {})

  return (
    <div className="h-full flex flex-col -m-8">
      {/* 页面头部 */}
      <div className="px-8 pt-8 pb-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
                <Box className="w-4 h-4 text-white" strokeWidth={1.75} />
              </div>
              <h1 className="text-xl font-semibold text-neutral-900">智能CAD设计</h1>
              <span className="px-2 py-0.5 text-[10px] font-medium bg-violet-50 text-violet-600 rounded border border-violet-200">
                Beta
              </span>
            </div>
            <p className="text-sm text-neutral-500 mt-1 ml-[42px]">
              基于 AI 的水利工程三维模型生成，自然语言描述即可创建参数化 CAD 模型
            </p>
          </div>
          <button
            onClick={handleOpenInCADAM}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            <ExternalLink className="w-4 h-4" strokeWidth={1.75} />
            在新窗口打开 CADAM
          </button>
        </div>
      </div>

      {/* 主体内容：左右分栏 */}
      <div className="flex-1 flex min-h-0 px-8 pb-8 gap-4">
        {/* 左侧面板：输入 + 模板 */}
        <div className="w-[360px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto">
          {/* 输入区 */}
          <div className="border border-neutral-200 bg-white rounded-lg p-4">
            <label className="block text-xs font-medium text-neutral-700 mb-2">
              <Sparkles className="w-3.5 h-3.5 inline mr-1 text-violet-500" strokeWidth={1.75} />
              描述您想要的模型（中文）
            </label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="例如：一座高30米的混凝土重力坝，带溢流堰和排水廊道"
              className="w-full h-24 px-3 py-2 text-sm border border-neutral-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 placeholder:text-neutral-400"
              onKeyDown={e => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  handleGenerate()
                }
              }}
            />
            <button
              onClick={handleGenerate}
              disabled={loading || (!description.trim() && !selectedTemplate)}
              className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-medium rounded-lg hover:from-violet-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" strokeWidth={1.75} />
                  生成提示词中...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" strokeWidth={1.75} />
                  生成CAD模型
                </>
              )}
            </button>
            <p className="mt-2 text-[11px] text-neutral-400 text-center">
              按 ⌘/Ctrl + Enter 快速生成
            </p>
          </div>

          {/* 生成的提示词 */}
          {generatedPrompt && (
            <div className="border border-violet-200 bg-violet-50/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-violet-700">
                  生成的英文提示词
                </label>
                <button
                  onClick={handleCopyPrompt}
                  className="flex items-center gap-1 px-2 py-1 text-[11px] text-violet-600 hover:bg-violet-100 rounded transition-colors"
                >
                  {copied ? (
                    <Check className="w-3 h-3" strokeWidth={2} />
                  ) : (
                    <Copy className="w-3 h-3" strokeWidth={1.75} />
                  )}
                  {copied ? '已复制' : '复制'}
                </button>
              </div>
              <p className="text-xs text-neutral-700 leading-relaxed bg-white p-3 rounded border border-violet-100">
                {generatedPrompt}
              </p>
              <p className="mt-2 text-[11px] text-violet-500 flex items-start gap-1">
                <Info className="w-3 h-3 mt-0.5 flex-shrink-0" strokeWidth={1.75} />
                提示词已就绪，可直接粘贴到右侧 CADAM 编辑器中使用
              </p>
            </div>
          )}

          {/* 构件模板 */}
          <div className="border border-neutral-200 bg-white rounded-lg p-4 flex-1">
            <div className="flex items-center gap-2 mb-3">
              <Layers className="w-4 h-4 text-neutral-500" strokeWidth={1.75} />
              <h3 className="text-sm font-medium text-neutral-800">水利构件模板</h3>
              <span className="ml-auto text-[11px] text-neutral-400">{templates.length} 个</span>
            </div>

            <div className="space-y-1">
              {categories.map(cat => (
                <div key={cat}>
                  <button
                    onClick={() => toggleCategory(cat)}
                    className="w-full flex items-center gap-1.5 px-2 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50 rounded transition-colors"
                  >
                    {expandedCategories[cat] ? (
                      <ChevronDown className="w-3 h-3 text-neutral-400" strokeWidth={2} />
                    ) : (
                      <ChevronRight className="w-3 h-3 text-neutral-400" strokeWidth={2} />
                    )}
                    {cat}
                    <span className="ml-auto text-[10px] text-neutral-400">
                      {groupedTemplates[cat]?.length || 0}
                    </span>
                  </button>
                  {expandedCategories[cat] && (
                    <div className="ml-4 space-y-0.5 mt-0.5">
                      {groupedTemplates[cat]?.map(t => (
                        <button
                          key={t.id}
                          onClick={() => handleTemplateClick(t)}
                          className={`w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded transition-colors text-left ${
                            selectedTemplate?.id === t.id
                              ? 'bg-violet-100 text-violet-800'
                              : 'text-neutral-600 hover:bg-neutral-50'
                          }`}
                        >
                          <span className="text-sm">{t.icon}</span>
                          <span className="truncate">{t.name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 使用说明 */}
          <div className="border border-neutral-200 bg-neutral-50 rounded-lg p-4">
            <h3 className="text-xs font-medium text-neutral-700 mb-2 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5" strokeWidth={1.75} />
              使用说明
            </h3>
            <ol className="space-y-1.5 text-[11px] text-neutral-500 leading-relaxed list-decimal list-inside">
              <li>用中文描述您想要的水利工程构件</li>
              <li>可从模板库选择常见构件快速开始</li>
              <li>点击"生成CAD模型"，AI 将生成专业英文提示词</li>
              <li>在右侧 CADAM 编辑器中粘贴提示词生成模型</li>
              <li>使用滑块调整参数，导出 STL/SCAD/DXF</li>
            </ol>
            <div className="mt-3 pt-3 border-t border-neutral-200 flex items-center gap-2 text-[10px] text-neutral-400">
              <Download className="w-3 h-3" strokeWidth={1.75} />
              支持导出 STL（3D打印）、SCAD、DXF 格式
            </div>
          </div>
        </div>

        {/* 右侧：CADAM 编辑器 */}
        <div className="flex-1 border border-neutral-200 bg-white rounded-lg flex flex-col min-w-0 overflow-hidden">
          {showIframe ? (
            <>
              <div className="h-10 px-4 flex items-center justify-between border-b border-neutral-200 bg-neutral-50 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="text-xs font-medium text-neutral-600">CADAM 编辑器</span>
                  {generatedPrompt && (
                    <span className="text-[10px] text-violet-600 bg-violet-50 px-1.5 py-0.5 rounded border border-violet-200">
                      提示词已就绪，请粘贴到输入框
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopyPrompt}
                    disabled={!generatedPrompt}
                    className="flex items-center gap-1 px-2 py-1 text-[11px] text-neutral-500 hover:text-neutral-800 hover:bg-neutral-100 rounded transition-colors disabled:opacity-40"
                  >
                    <Copy className="w-3 h-3" strokeWidth={1.75} />
                    复制提示词
                  </button>
                  <button
                    onClick={handleOpenInCADAM}
                    className="flex items-center gap-1 px-2 py-1 text-[11px] text-neutral-500 hover:text-neutral-800 hover:bg-neutral-100 rounded transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" strokeWidth={1.75} />
                    新窗口打开
                  </button>
                </div>
              </div>
              <iframe
                ref={iframeRef}
                src={CADAM_URL}
                className="flex-1 w-full border-0"
                title="CADAM Editor"
                allow="clipboard-write; clipboard-read"
              />
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-100 to-indigo-100 flex items-center justify-center mb-5">
                <Box className="w-10 h-10 text-violet-500" strokeWidth={1.25} />
              </div>
              <h3 className="text-lg font-semibold text-neutral-800 mb-2">
                开始创建您的 CAD 模型
              </h3>
              <p className="text-sm text-neutral-500 max-w-md mb-6 leading-relaxed">
                在左侧输入框中用中文描述您想要的水利工程构件，或从模板库中选择常见构件，
                点击"生成CAD模型"后，CADAM 编辑器将在此处加载。
              </p>
              <div className="grid grid-cols-2 gap-3 max-w-md w-full mb-6">
                {[
                  { icon: '🏔️', name: '拱坝' },
                  { icon: '🚪', name: '水闸' },
                  { icon: '🌊', name: '溢洪道' },
                  { icon: '〰️', name: '渠道' },
                ].map(item => (
                  <div
                    key={item.name}
                    className="flex items-center gap-2 px-3 py-2 bg-neutral-50 border border-neutral-200 rounded-lg text-sm text-neutral-600"
                  >
                    <span className="text-lg">{item.icon}</span>
                    {item.name}
                  </div>
                ))}
              </div>
              <button
                onClick={() => setShowIframe(true)}
                className="flex items-center gap-2 px-4 py-2 text-sm text-neutral-600 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition-colors"
              >
                <ExternalLink className="w-4 h-4" strokeWidth={1.75} />
                直接打开 CADAM 编辑器
              </button>
              <p className="mt-4 text-[11px] text-neutral-400">
                由 CADAM (GPL-3.0) 提供 3D 渲染引擎支持
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
