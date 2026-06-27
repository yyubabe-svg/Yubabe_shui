import { useState, useEffect } from 'react'
import {
  FolderSearch, Search, ChevronRight, Loader2, MapPin, Building2,
  FileText, Calculator, Star, StarOff, RefreshCw, Filter,
} from 'lucide-react'
import { useProject } from '../../context/ProjectContext'
import { toolsApi, type SimilarProject } from '../../api/tools'

const PROJECT_TYPE_OPTIONS = [
  { value: 'river_training', label: '河道治理' },
  { value: 'flash_flood', label: '山洪沟治理' },
  { value: 'reservoir', label: '水库除险加固' },
  { value: 'irrigation', label: '灌区续建配套' },
  { value: 'pump_station', label: '排涝泵站' },
  { value: 'urban_drainage', label: '城市内涝' },
  { value: 'flood_assessment', label: '防洪评价' },
  { value: 'soil_conservation', label: '水土保持' },
  { value: 'rural_water', label: '农村供水' },
  { value: 'farmland_water', label: '小型农田水利' },
  { value: 'levee', label: '堤防工程' },
  { value: 'sluice', label: '涵闸工程' },
  { value: 'water_resources', label: '水资源论证' },
]

export default function HistoryReusePanel() {
  const { currentProject } = useProject()
  const [projects, setProjects] = useState<SimilarProject[]>([])
  const [loading, setLoading] = useState(false)
  const [projectType, setProjectType] = useState('')
  const [locationKw, setLocationKw] = useState('')
  const [nameKw, setNameKw] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [recommendMode, setRecommendMode] = useState(true)

  const searchSimilar = async () => {
    setLoading(true)
    try {
      const res = await toolsApi.findSimilar({
        project_type: projectType || undefined,
        location_keyword: locationKw || undefined,
        project_type_name_keyword: nameKw || undefined,
        exclude_project_id: currentProject?.id,
        limit: 20,
      })
      setProjects(res.items)
      setLoaded(true)
      setRecommendMode(false)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const loadRecommendations = async () => {
    if (!currentProject) return
    setLoading(true)
    setRecommendMode(true)
    try {
      const res = await toolsApi.recommendForProject(currentProject.id, 8)
      setProjects(res.items)
      setLoaded(true)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (currentProject) {
      // 初始化时根据当前项目类型和位置自动推荐
      setProjectType(currentProject.project_type || '')
      const loc = currentProject.location || ''
      setLocationKw(loc.slice(0, 2))
      loadRecommendations()
    }
  }, [currentProject])

  return (
    <div className="space-y-5">
      {/* 搜索条件 */}
      <div className="panel p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
            <FolderSearch className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
            相似历史项目检索
          </h3>
          {currentProject && (
            <button
              onClick={loadRecommendations}
              className={`text-xs px-3 py-1 rounded-full transition-colors flex items-center gap-1 ${
                recommendMode ? 'bg-brand-600 text-white' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
              }`}
            >
              <RefreshCw className="w-3 h-3" />智能推荐
            </button>
          )}
        </div>

        <div className="flex gap-3 flex-wrap">
          <select
            value={projectType}
            onChange={e => setProjectType(e.target.value)}
            className="input max-w-[180px]"
          >
            <option value="">全部项目类型</option>
            {PROJECT_TYPE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <input
            type="text"
            value={locationKw}
            onChange={e => setLocationKw(e.target.value)}
            placeholder="地域关键词（如：成都、岷江）"
            className="input max-w-[180px]"
          />
          <input
            type="text"
            value={nameKw}
            onChange={e => setNameKw(e.target.value)}
            placeholder="工程名称关键词（如：堤防、泵站）"
            className="input flex-1 min-w-[200px]"
          />
          <button
            onClick={searchSimilar}
            disabled={loading}
            className="btn-primary px-5 flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            搜索
          </button>
        </div>

        {recommendMode && currentProject && (
          <p className="text-xs text-neutral-500 mt-3 flex items-center gap-1.5">
            <Star className="w-3.5 h-3.5 text-amber-500" />
            已根据当前项目「{currentProject.project_name}」的类型和位置智能推荐相似历史项目
          </p>
        )}
      </div>

      {/* 结果列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-brand-600 animate-spin" />
        </div>
      ) : !loaded ? (
        <div className="panel">
          <div className="empty-state py-12">
            <FolderSearch className="empty-state-icon" strokeWidth={1.5} />
            <p className="empty-state-text">输入条件查找历史相似项目</p>
            <p className="text-xs text-neutral-400 mt-2">可复用：报告章节、设计参数、专家意见、造价指标</p>
          </div>
        </div>
      ) : projects.length === 0 ? (
        <div className="panel">
          <div className="empty-state py-12">
            <FolderSearch className="empty-state-icon" strokeWidth={1.5} />
            <p className="empty-state-text">未找到匹配的历史项目</p>
            <p className="text-xs text-neutral-400 mt-2">尝试减少条件或更换关键词</p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="text-xs text-neutral-500">
            找到 <span className="font-semibold text-neutral-700">{projects.length}</span> 个相似项目
            {recommendMode && <span className="ml-2 text-amber-600">（按匹配度排序）</span>}
          </div>

          {projects.map(p => (
            <div key={p.id} className="panel p-4 hover:border-brand-300 transition-colors">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-brand-50 flex items-center justify-center flex-shrink-0">
                  <Building2 className="w-5 h-5 text-brand-600" strokeWidth={1.75} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h4 className="text-sm font-medium text-neutral-900 flex items-center gap-2">
                        {p.project_name}
                        <span className="text-xs px-1.5 py-0.5 bg-brand-50 text-brand-700 rounded">
                          {p.project_type_name}
                        </span>
                      </h4>
                      <div className="flex items-center gap-3 mt-1 text-xs text-neutral-500 flex-wrap">
                        {p.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />{p.location}
                          </span>
                        )}
                        {p.river_basin && (
                          <span>流域：{p.river_basin}</span>
                        )}
                        {p.total_investment && (
                          <span>投资：{p.total_investment}万元</span>
                        )}
                        <span className="flex items-center gap-1">
                          <FileText className="w-3 h-3" />{p.doc_count}份文档
                        </span>
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <div className="flex items-center gap-1 text-sm font-semibold text-brand-600">
                        <Star className="w-3.5 h-3.5" />
                        {p.match_score}分
                      </div>
                    </div>
                  </div>

                  {p.match_reasons && p.match_reasons.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {p.match_reasons.map((r, i) => (
                        <span key={i} className="text-xs px-2 py-0.5 bg-green-50 text-green-700 rounded-full">
                          {r}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <ChevronRight className="w-4 h-4 text-neutral-300 flex-shrink-0 mt-2" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
