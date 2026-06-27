import { useState, useRef, useEffect } from 'react'
import {
  Map, Upload, Loader2, AlertTriangle, CheckCircle2,
  Layers, FileText, Mountain, Droplets, Info, X,
} from 'lucide-react'
import { toolsApi, type GisAnalysisResult } from '../../api/tools'

type AnalysisType = 'basic' | 'slope' | 'watershed' | 'flood'

const ANALYSIS_OPTIONS: { key: AnalysisType; label: string; desc: string; icon: any; disabled?: boolean }[] = [
  { key: 'basic', label: '基础信息统计', desc: '要素数量、面积/长度、CRS、属性预览', icon: Layers },
  { key: 'slope', label: 'DEM坡度分析', desc: '坡度分级、坡向统计（需上传DEM）', icon: Mountain },
  { key: 'watershed', label: '汇水流域提取', desc: '流域范围、汇水面积（开发中）', icon: Droplets, disabled: true },
  { key: 'flood', label: '洪水淹没模拟', desc: '基于SFINCS快速淹没模拟（开发中）', icon: Droplets, disabled: true },
]

export default function GISPanel() {
  const [files, setFiles] = useState<File[]>([])
  const [analysisType, setAnalysisType] = useState<AnalysisType>('basic')
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<GisAnalysisResult | null>(null)
  const [gisAvailable, setGisAvailable] = useState<boolean | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    toolsApi.gisInfo().then(info => {
      setGisAvailable(info.status === 'available')
    }).catch(() => setGisAvailable(false))
  }, [])

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return
    const arr = Array.from(fileList).filter(f => {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase()
      return ['.shp', '.geojson', '.json', '.gpkg', '.zip', '.tif', '.tiff', '.dem', '.asc'].includes(ext)
    })
    setFiles(prev => [...prev, ...arr])
    setResult(null)
  }

  const removeFile = (idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx))
    setResult(null)
  }

  const handleAnalyze = async () => {
    if (files.length === 0) return
    setAnalyzing(true)
    try {
      const res = await toolsApi.gisAnalyze(files, analysisType)
      setResult(res)
    } catch (e: any) {
      console.error('GIS分析失败:', e)
      alert('分析失败：' + (e.message || '未知错误'))
    } finally {
      setAnalyzing(false)
    }
  }

  const getFileExt = (name: string) => (name.split('.').pop() || '').toLowerCase()

  const isVector = (ext: string) => ['shp', 'geojson', 'json', 'gpkg', 'zip'].includes(ext)
  const isRaster = (ext: string) => ['tif', 'tiff', 'dem', 'asc'].includes(ext)

  return (
    <div className="space-y-5">
      {/* GIS状态提示 */}
      {gisAvailable === false && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
          <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-amber-700">
            <p className="font-medium">GIS 依赖库未安装</p>
            <p className="mt-1">如需完整空间分析功能，请安装：pip install geopandas rasterio shapely pyproj</p>
            <p>当前可上传文件，返回基础文件信息。</p>
          </div>
        </div>
      )}

      {/* 分析类型选择 */}
      <div className="panel p-4">
        <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
          <Map className="w-4 h-4 text-brand-600" strokeWidth={1.75} />
          GIS 空间分析与一键出图
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {ANALYSIS_OPTIONS.map(opt => {
            const Icon = opt.icon
            return (
              <button
                key={opt.key}
                onClick={() => !opt.disabled && setAnalysisType(opt.key)}
                disabled={opt.disabled}
                className={`p-3 rounded-lg border text-left transition-all ${
                  analysisType === opt.key
                    ? 'border-brand-400 bg-brand-50'
                    : opt.disabled
                    ? 'border-neutral-100 bg-neutral-50 opacity-50 cursor-not-allowed'
                    : 'border-neutral-200 hover:border-brand-300 hover:bg-neutral-50'
                }`}
              >
                <Icon className={`w-5 h-5 mb-2 ${analysisType === opt.key ? 'text-brand-600' : 'text-neutral-400'}`} strokeWidth={1.75} />
                <p className={`text-sm font-medium ${analysisType === opt.key ? 'text-brand-700' : 'text-neutral-700'}`}>
                  {opt.label}
                  {opt.disabled && <span className="ml-1 text-xs text-neutral-400">(开发中)</span>}
                </p>
                <p className="text-xs text-neutral-400 mt-0.5">{opt.desc}</p>
              </button>
            )
          })}
        </div>
      </div>

      {/* 上传区 */}
      <div className="panel p-5">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
            dragOver ? 'border-brand-400 bg-brand-50' : 'border-neutral-200 hover:border-brand-300'
          }`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="w-10 h-10 text-neutral-300 mx-auto mb-2" strokeWidth={1.5} />
          <p className="text-sm text-neutral-600">点击或拖拽空间数据文件到此处</p>
          <p className="text-xs text-neutral-400 mt-1">
            矢量：SHP(打包为ZIP)/GeoJSON/GPKG　|　栅格：TIFF/DEM/ASC
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".shp,.geojson,.json,.gpkg,.zip,.tif,.tiff,.dem,.asc"
            multiple
            className="hidden"
            onChange={e => handleFiles(e.target.files)}
          />
        </div>

        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs text-neutral-500">已选择 {files.length} 个文件：</p>
            {files.map((f, i) => {
              const ext = getFileExt(f.name)
              return (
                <div key={i} className="flex items-center gap-2 p-2 bg-neutral-50 rounded text-sm">
                  {isVector(ext) ? (
                    <Layers className="w-4 h-4 text-blue-500 flex-shrink-0" />
                  ) : isRaster(ext) ? (
                    <Mountain className="w-4 h-4 text-green-600 flex-shrink-0" />
                  ) : (
                    <FileText className="w-4 h-4 text-neutral-400 flex-shrink-0" />
                  )}
                  <span className="flex-1 truncate text-neutral-700">{f.name}</span>
                  <span className="text-xs text-neutral-400">
                    {isVector(ext) ? '矢量' : isRaster(ext) ? '栅格' : ''} · {(f.size / 1024).toFixed(1)} KB
                  </span>
                  <button
                    onClick={e => { e.stopPropagation(); removeFile(i) }}
                    className="p-1 hover:bg-neutral-200 rounded"
                  >
                    <X className="w-3.5 h-3.5 text-neutral-400" />
                  </button>
                </div>
              )
            })}
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="btn-primary mt-3 w-full flex items-center justify-center gap-2"
            >
              {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              {analyzing ? '分析中...' : `开始分析（${ANALYSIS_OPTIONS.find(o => o.key === analysisType)?.label}）`}
            </button>
          </div>
        )}
      </div>

      {/* 分析结果 */}
      {result && (
        <div className="space-y-4">
          <div className="panel p-5">
            <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
              {result.success ? (
                <CheckCircle2 className="w-4 h-4 text-green-600" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-600" />
              )}
              分析结果（{result.file_count}个文件）
            </h3>

            {!result.success && result.message && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700 mb-4">
                {result.message}
                {result.install_hint && (
                  <p className="text-xs mt-1 font-mono bg-white px-2 py-1 rounded mt-2">{result.install_hint}</p>
                )}
              </div>
            )}

            <div className="space-y-4">
              {result.results.map((r, i) => (
                <div key={i} className="p-4 bg-neutral-50 rounded-lg">
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div>
                      <p className="text-sm font-medium text-neutral-800">{r.filename}</p>
                      <p className="text-xs text-neutral-400 mt-0.5">
                        {(r.file_size / 1024).toFixed(1)} KB · {r.ext.toUpperCase()} ·
                        <span className={`ml-1 ${
                          r.status === 'processed' ? 'text-green-600' :
                          r.status === 'error' ? 'text-red-600' : 'text-neutral-500'
                        }`}>
                          {r.status === 'processed' ? '已分析' : r.status === 'error' ? '分析失败' : r.status}
                        </span>
                      </p>
                    </div>
                  </div>

                  {r.status === 'error' && r.error && (
                    <p className="text-xs text-red-600 bg-red-50 p-2 rounded">{r.error}</p>
                  )}

                  {r.status === 'unsupported' && r.message && (
                    <p className="text-xs text-neutral-500">{r.message}</p>
                  )}

                  {r.status === 'processed' && (
                    <div className="space-y-2">
                      {/* 矢量数据结果 */}
                      {r.feature_count !== undefined && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          <div className="p-2 bg-white rounded border border-neutral-100">
                            <p className="text-xs text-neutral-400">要素数量</p>
                            <p className="text-sm font-semibold text-neutral-800">{r.feature_count}</p>
                          </div>
                          {r.area_km2 !== undefined && (
                            <div className="p-2 bg-white rounded border border-neutral-100">
                              <p className="text-xs text-neutral-400">总面积</p>
                              <p className="text-sm font-semibold text-neutral-800">{r.area_km2} km²</p>
                            </div>
                          )}
                          {r.length_km !== undefined && (
                            <div className="p-2 bg-white rounded border border-neutral-100">
                              <p className="text-xs text-neutral-400">总长度</p>
                              <p className="text-sm font-semibold text-neutral-800">{r.length_km} km</p>
                            </div>
                          )}
                          {r.crs && (
                            <div className="p-2 bg-white rounded border border-neutral-100">
                              <p className="text-xs text-neutral-400">坐标系</p>
                              <p className="text-sm font-semibold text-neutral-800 truncate" title={r.crs}>{r.crs.replace('EPSG:', 'EPSG:')}</p>
                            </div>
                          )}
                        </div>
                      )}

                      {/* 栅格数据结果 */}
                      {r.raster_width !== undefined && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          <div className="p-2 bg-white rounded border border-neutral-100">
                            <p className="text-xs text-neutral-400">尺寸</p>
                            <p className="text-sm font-semibold text-neutral-800">{r.raster_width}×{r.raster_height}</p>
                          </div>
                          <div className="p-2 bg-white rounded border border-neutral-100">
                            <p className="text-xs text-neutral-400">分辨率</p>
                            <p className="text-sm font-semibold text-neutral-800">{r.resolution?.map(v => v.toFixed(2)).join('×')} m</p>
                          </div>
                          <div className="p-2 bg-white rounded border border-neutral-100">
                            <p className="text-xs text-neutral-400">高程范围</p>
                            <p className="text-sm font-semibold text-neutral-800">{r.min_value?.toFixed(1)}~{r.max_value?.toFixed(1)} m</p>
                          </div>
                          <div className="p-2 bg-white rounded border border-neutral-100">
                            <p className="text-xs text-neutral-400">平均高程</p>
                            <p className="text-sm font-semibold text-neutral-800">{r.mean_value?.toFixed(1)} m</p>
                          </div>
                        </div>
                      )}

                      {/* 坡度分析结果 */}
                      {r.slope_classes && (
                        <div className="mt-3">
                          <p className="text-xs font-medium text-neutral-600 mb-2">坡度分级</p>
                          <div className="space-y-1">
                            {Object.entries(r.slope_classes).map(([label, pct]) => (
                              <div key={label} className="flex items-center gap-2">
                                <span className="text-xs text-neutral-600 w-28">{label}</span>
                                <div className="flex-1 h-4 bg-neutral-100 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-500 rounded-full"
                                    style={{ width: `${pct}%` }}
                                  />
                                </div>
                                <span className="text-xs text-neutral-500 w-12 text-right">{pct.toFixed(1)}%</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* 属性预览 */}
                      {r.attribute_preview && r.attribute_preview.length > 0 && (
                        <details className="mt-2">
                          <summary className="text-xs text-neutral-500 cursor-pointer hover:text-brand-600">
                            属性表预览（前{r.attribute_preview.length}行）
                          </summary>
                          <div className="mt-2 overflow-x-auto">
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="border-b border-neutral-200">
                                  {Object.keys(r.attribute_preview[0] || {}).map(k => (
                                    <th key={k} className="text-left py-1 px-2 font-medium text-neutral-500">{k}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {r.attribute_preview.map((row, j) => (
                                  <tr key={j} className="border-b border-neutral-100">
                                    {Object.values(row).map((v, k) => (
                                      <td key={k} className="py-1 px-2 text-neutral-700 truncate max-w-[120px]" title={String(v)}>
                                        {v === null ? '—' : String(v)}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 未来功能提示 */}
          <div className="panel p-4">
            <h4 className="text-sm font-medium text-neutral-700 mb-2">🚧 后续功能规划</h4>
            <ul className="text-xs text-neutral-500 space-y-1 list-disc list-inside">
              {result.future_features?.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        </div>
      )}

      {!result && files.length === 0 && (
        <div className="panel p-5">
          <h4 className="text-sm font-medium text-neutral-800 mb-3">支持的分析功能</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div className="p-3 bg-neutral-50 rounded-lg">
              <p className="font-medium text-neutral-700 flex items-center gap-2"><Layers className="w-4 h-4 text-blue-500" />矢量数据</p>
              <ul className="text-xs text-neutral-500 mt-1.5 space-y-1 list-disc list-inside">
                <li>要素数量、几何类型统计</li>
                <li>面积/长度自动计算（等积投影）</li>
                <li>坐标系识别、边界范围</li>
                <li>属性表预览</li>
              </ul>
            </div>
            <div className="p-3 bg-neutral-50 rounded-lg">
              <p className="font-medium text-neutral-700 flex items-center gap-2"><Mountain className="w-4 h-4 text-green-600" />栅格DEM</p>
              <ul className="text-xs text-neutral-500 mt-1.5 space-y-1 list-disc list-inside">
                <li>高程范围、分辨率统计</li>
                <li>坡度计算与分级</li>
                <li>坡向分析（开发中）</li>
                <li>流域提取（开发中）</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
