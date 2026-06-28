import { useState, useEffect, useRef, useCallback } from 'react'
import { RotateCcw, Eye, Droplets, Layers, Ruler, Settings, Cuboid, Building2, Milestone } from 'lucide-react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { phase3Api, type SectionDesignResult } from '../../api/phase3'
import { useProject } from '../../context/ProjectContext'

function cn(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ')
}

type SectionType = 'trapezoidal' | 'rectangular' | 'compound'
type StructureType = 'none' | 'sluice' | 'culvert' | 'weir'

interface StructureInfo {
  type: StructureType
  position_m: number  // 沿河道位置(m)
  width_m: number
}

const DEFAULT_PARAMS: Record<string, any> = {
  trapezoidal: { design_water_level: 100, bed_elevation: 95, bed_width: 10, m_slope: 2.0, revetment_type: 'stone_mortar', freeboard: 1.0, crest_width: 5.0, foundation_depth: 0.6 },
  rectangular: { design_water_level: 100, bed_elevation: 95, bed_width: 8, wall_height: 6, wall_thickness: 0.6, wall_bottom_thickness: 1.8, revetment_type: 'concrete', freeboard: 1.0, crest_width: 3.0, foundation_depth: 1.0 },
  compound: { design_water_level: 100, bed_elevation: 94, main_channel_width: 12, main_channel_depth: 3.5, floodplain_width: 15, m_slope_main: 2.0, m_slope_flood: 2.5, revetment_type: 'stone_mortar', floodplain_revetment: 'grass', freeboard: 1.0, crest_width: 5.0, foundation_depth: 0.6 },
}

export default function Visual3DPanel() {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const animFrameRef = useRef<number>(0)
  const modelGroupRef = useRef<THREE.Group | null>(null)
  const waterMeshRef = useRef<THREE.Mesh | null>(null)
  const waterLevelRef = useRef(100)
  const showWaterRef = useRef(true)

  const { currentProject } = useProject()
  const [sectionType, setSectionType] = useState<SectionType>('trapezoidal')
  const [designResult, setDesignResult] = useState<SectionDesignResult | null>(null)
  const [designing, setDesigning] = useState(false)
  const [params, setParams] = useState<Record<string, any>>(DEFAULT_PARAMS.trapezoidal)
  const [waterLevel, setWaterLevel] = useState(100)
  const [channelLength, setChannelLength] = useState(200)
  const [autoRotate, setAutoRotate] = useState(false)
  const [viewMode, setViewMode] = useState<'perspective' | 'top' | 'front' | 'side'>('perspective')
  const [showWater, setShowWater] = useState(true)
  const [showGrid, setShowGrid] = useState(true)
  const [showStations, setShowStations] = useState(true)
  const [structure, setStructure] = useState<StructureInfo>({ type: 'sluice', position_m: 100, width_m: 8 })
  const [bedSlope, setBedSlope] = useState(0.001) // 纵坡 i=0.001

  const handleDesign = useCallback(async () => {
    setDesigning(true)
    try {
      const res = await phase3Api.designSection({ section_type: sectionType as any, ...params } as any, currentProject?.id)
      setDesignResult(res)
    } catch (e) { console.error(e) }
    finally { setDesigning(false) }
  }, [params, sectionType, currentProject?.id])

  useEffect(() => { handleDesign() }, [sectionType])
  useEffect(() => { waterLevelRef.current = waterLevel }, [waterLevel])
  useEffect(() => { showWaterRef.current = showWater }, [showWater])
  const autoRotateRef = useRef(autoRotate)
  useEffect(() => { autoRotateRef.current = autoRotate }, [autoRotate])

  const switchSection = (t: SectionType) => {
    setSectionType(t)
    setParams(DEFAULT_PARAMS[t])
    setWaterLevel(DEFAULT_PARAMS[t].design_water_level)
  }

  // 初始化Three.js
  useEffect(() => {
    if (!containerRef.current) return
    const container = containerRef.current
    const w = container.clientWidth, h = container.clientHeight
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xe8f0f5)
    scene.fog = new THREE.Fog(0xe8f0f5, 300, 800)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000)
    camera.position.set(120, 70, 180)
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(w, h)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.maxPolarAngle = Math.PI / 2.05
    controls.minDistance = 10
    controls.maxDistance = 600
    controlsRef.current = controls

    scene.add(new THREE.AmbientLight(0xffffff, 0.6))
    const dir = new THREE.DirectionalLight(0xffffff, 0.9)
    dir.position.set(120, 150, 80); dir.castShadow = true
    dir.shadow.mapSize.set(2048,2048)
    dir.shadow.camera.left=-200;dir.shadow.camera.right=200;dir.shadow.camera.top=200;dir.shadow.camera.bottom=-200
    dir.shadow.camera.near=0.5;dir.shadow.camera.far=500
    scene.add(dir)
    scene.add(new THREE.HemisphereLight(0x87ceeb, 0x8b7355, 0.3))

    const groundGeo = new THREE.PlaneGeometry(2000, 2000)
    const ground = new THREE.Mesh(groundGeo, new THREE.MeshStandardMaterial({ color: 0xc8b896, roughness: 1 }))
    ground.rotation.x = -Math.PI/2; ground.position.y = 90; ground.receiveShadow = true
    scene.add(ground)

    const grid = new THREE.GridHelper(800, 80, 0xaaaaaa, 0xdddddd)
    grid.position.y = 90.01; grid.name = 'gridHelper'
    scene.add(grid)

    const modelGroup = new THREE.Group()
    modelGroup.name = 'modelGroup'
    scene.add(modelGroup)
    modelGroupRef.current = modelGroup

    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate)
      if (autoRotateRef.current && modelGroupRef.current) modelGroupRef.current.rotation.y += 0.002
      if (waterMeshRef.current && showWaterRef.current) {
        const t = Date.now()*0.001
        waterMeshRef.current.position.y = waterLevelRef.current - 0.05 + Math.sin(t*1.5)*0.03
      }
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const onResize = () => {
      if (!container) return
      const W = container.clientWidth, H = container.clientHeight
      camera.aspect = W/H; camera.updateProjectionMatrix()
      renderer.setSize(W, H)
    }
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      cancelAnimationFrame(animFrameRef.current)
      renderer.dispose()
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement)
    }
  }, [])

  // 网格/坐标轴切换
  useEffect(() => {
    if (!sceneRef.current) return
    const g = sceneRef.current.getObjectByName('gridHelper') as THREE.GridHelper
    if (g) g.visible = showGrid
  }, [showGrid])

  // 构建/更新三维模型（支持纵坡+建筑物+里程桩）
  useEffect(() => {
    if (!sceneRef.current || !modelGroupRef.current || !designResult) return
    const scene = sceneRef.current
    const group = modelGroupRef.current

    // 清除旧模型
    while (group.children.length > 0) {
      const obj = group.children[0]
      group.remove(obj)
      obj.traverse((o: any) => {
        if (o.geometry) o.geometry.dispose()
        if (o.material) {
          if (Array.isArray(o.material)) o.material.forEach((m:any)=>m.dispose())
          else o.material.dispose()
        }
      })
    }
    if (waterMeshRef.current) {
      scene.remove(waterMeshRef.current)
      waterMeshRef.current.geometry.dispose()
      ;(waterMeshRef.current.material as THREE.Material).dispose()
      waterMeshRef.current = null
    }

    const { outline_points } = designResult.geometry
    const { bed_elevation, crest_elevation, revetment_name, bed_width } = designResult.parameters
    const L = channelLength
    const halfL = L / 2
    const centerX = designResult.geometry.section_width_m / 2

    // 材质
    const matMap: Record<string, THREE.MeshStandardMaterial> = {
      fill: new THREE.MeshStandardMaterial({ color: 0xc49a6c, roughness: 0.95, flatShading: true }),
      concrete: new THREE.MeshStandardMaterial({ color: 0xb0b0b0, roughness: 0.7 }),
      stone: new THREE.MeshStandardMaterial({ color: 0x808080, roughness: 0.8 }),
      eco: new THREE.MeshStandardMaterial({ color: 0x6b8e4e, roughness: 0.9 }),
      grass: new THREE.MeshStandardMaterial({ color: 0x7cb342, roughness: 0.95 }),
      water: new THREE.MeshStandardMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.6, roughness: 0.1, metalness: 0.3, side: THREE.DoubleSide }),
      crest: new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.8 }),
      sluice: new THREE.MeshStandardMaterial({ color: 0x4a6fa5, roughness: 0.4, metalness: 0.3 }),
      culvert: new THREE.MeshStandardMaterial({ color: 0x6d6d6d, roughness: 0.6 }),
      weir: new THREE.MeshStandardMaterial({ color: 0x8b7355, roughness: 0.8 }),
      stake: new THREE.MeshStandardMaterial({ color: 0xdc2626, roughness: 0.5 }),
    }

    const revMat = revetment_name.includes('混凝土') ? matMap.concrete
                : revetment_name.includes('生态') ? matMap.eco
                : revetment_name.includes('草皮') ? matMap.grass
                : matMap.stone

    // 沿Z轴分段构建（支持纵坡），每10m一段
    const segLen = 10
    const nSeg = Math.ceil(L / segLen)

    for (let si = 0; si < nSeg; si++) {
      const z0 = -halfL + si * segLen
      const z1 = Math.min(-halfL + (si+1) * segLen, halfL)
      const segLenActual = z1 - z0
      if (segLenActual <= 0) continue

      // 该段河底高程（考虑纵坡，中间位置z=0为设计高程）
      const bedEl0 = bed_elevation - z0 * bedSlope
      const bedEl1 = bed_elevation - z1 * bedSlope
      const crestEl0 = crest_elevation - z0 * bedSlope
      const crestEl1 = crest_elevation - z1 * bedSlope
      const dElev = bedEl1 - bedEl0  // 该段高程变化

      // 为每段构建断面Shape并拉伸到下一段（线性插值）
      const shape = new THREE.Shape()
      const segPts = outline_points.map(p => ({ x: p.x - centerX, y: p.y }))
      // 调整断面点高程（整体平移）
      const avgBed = (bedEl0 + bedEl1) / 2 - bed_elevation
      const adjPts = segPts.map(p => ({ x: p.x, y: p.y + avgBed }))
      shape.moveTo(adjPts[0].x, adjPts[0].y)
      for (let i = 1; i < adjPts.length; i++) shape.lineTo(adjPts[i].x, adjPts[i].y)

      const extrudeSettings: any = { depth: segLenActual, bevelEnabled: false, curveSegments: 2 }
      const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings)
      const mesh = new THREE.Mesh(geo, matMap.fill)
      mesh.position.z = z0
      mesh.position.y = 0
      // 倾斜该段以表现纵坡
      mesh.rotation.x = Math.atan2(-dElev, segLenActual)
      mesh.castShadow = true; mesh.receiveShadow = true
      group.add(mesh)

      // 护岸层（简化：沿边坡放置薄板）
      for (let pi = 0; pi < adjPts.length - 1; pi++) {
        const p1 = adjPts[pi], p2 = adjPts[pi+1]
        const dx = p2.x - p1.x, dy = p2.y - p1.y
        const segLen2d = Math.sqrt(dx*dx+dy*dy)
        if (segLen2d < 0.1) continue
        // 只在边坡部分（非水平段、非堤顶水平段）加护岸
        const isSide = Math.abs(dy) > 0.3 && Math.abs(dx) > 0.1
        const isCrest = Math.abs(dy) < 0.1 && pi >= 1 && pi <= 2 // 堤顶段
        if (isSide || isCrest) {
          const thick = isCrest ? 0.2 : (designResult.parameters.revetment_thickness || 0.3)
          const slabGeo = new THREE.BoxGeometry(segLen2d, thick, segLenActual)
          const slabMat = isCrest ? matMap.crest : revMat
          const slab = new THREE.Mesh(slabGeo, slabMat)
          slab.position.set((p1.x+p2.x)/2, (p1.y+p2.y)/2, z0 + segLenActual/2)
          slab.rotation.z = Math.atan2(dy, dx) - Math.PI/2
          slab.rotation.x = Math.atan2(-dElev, segLenActual)
          slab.castShadow = true; slab.receiveShadow = true
          group.add(slab)
        }
      }
    }

    // 水面（梯形简化，随纵坡倾斜）
    const wDepth = Math.max(0, waterLevel - bed_elevation)
    if (wDepth > 0 && showWater) {
      const waterSurfaceWidth = bed_width + 2 * (designResult.parameters.m_slope || 2.0) * wDepth
      const waterGeo = new THREE.PlaneGeometry(waterSurfaceWidth, L)
      const waterMesh = new THREE.Mesh(waterGeo, matMap.water)
      waterMesh.rotation.x = -Math.PI/2
      waterMesh.rotation.z = 0
      // 水面倾斜（纵坡）
      waterMesh.rotation.x = -Math.PI/2 + Math.atan(-bedSlope)
      waterMesh.position.set(0, waterLevel - 0.05, 0)
      waterMesh.receiveShadow = true
      scene.add(waterMesh)
      waterMeshRef.current = waterMesh
    }

    // 设计水位线框（沿程）
    const wl = designResult.parameters.design_water_level
    const wlWidth = bed_width + 2*(designResult.parameters.m_slope||2)*(wl - bed_elevation)
    const wlPts = [
      new THREE.Vector3(-wlWidth/2, wl, -halfL), new THREE.Vector3(wlWidth/2, wl, -halfL),
      new THREE.Vector3(wlWidth/2, wl, halfL), new THREE.Vector3(-wlWidth/2, wl, halfL),
      new THREE.Vector3(-wlWidth/2, wl, -halfL),
    ]
    const wlLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(wlPts),
      new THREE.LineBasicMaterial({ color: 0xdc2626, linewidth: 2 })
    )
    group.add(wlLine)

    // 里程桩
    if (showStations) {
      const stakeMat = matMap.stake
      for (let z = -halfL; z <= halfL; z += 50) {
        // 桩柱
        const stakeGeo = new THREE.CylinderGeometry(0.2, 0.2, 5, 8)
        const stake = new THREE.Mesh(stakeGeo, stakeMat)
        const groundY = crest_elevation - z*bedSlope + 2.5
        stake.position.set(centerX + 3, groundY, z)
        group.add(stake)
        // 里程标签（用Sprite简化）
        const canvas = document.createElement('canvas')
        canvas.width = 128; canvas.height = 48
        const ctx = canvas.getContext('2d')!
        ctx.fillStyle = '#ffffff'; ctx.fillRect(0,0,128,48)
        ctx.strokeStyle = '#dc2626'; ctx.lineWidth = 2; ctx.strokeRect(0,0,128,48)
        ctx.fillStyle = '#000000'; ctx.font = 'bold 18px sans-serif'; ctx.textAlign='center'; ctx.textBaseline='middle'
        const station = ((z + halfL) / 1000).toFixed(2)
        ctx.fillText(`K${station}`, 64, 24)
        const tex = new THREE.CanvasTexture(canvas)
        const spriteMat = new THREE.SpriteMaterial({ map: tex })
        const sprite = new THREE.Sprite(spriteMat)
        sprite.scale.set(8, 3, 1)
        sprite.position.set(centerX + 3, groundY + 4, z)
        group.add(sprite)
      }
    }

    // 典型建筑物
    if (structure.type !== 'none') {
      const sz = structure.position_m - halfL
      const bedElZ = bed_elevation - sz * bedSlope
      const crestElZ = crest_elevation - sz * bedSlope
      const structW = structure.width_m

      if (structure.type === 'sluice') {
        // 简化水闸模型：闸墩+闸室+工作桥
        const pierW = 1.2, pierH = crestElZ - bedElZ + 2
        const nPiers = 3
        const spanW = structW / (nPiers-1)
        for (let i = 0; i < nPiers; i++) {
          const px = -structW/2 + i*spanW
          const pier = new THREE.Mesh(
            new THREE.BoxGeometry(pierW, pierH, 6),
            matMap.sluice
          )
          pier.position.set(px, bedElZ + pierH/2, sz)
          pier.castShadow = true
          group.add(pier)
        }
        // 工作桥
        const bridge = new THREE.Mesh(
          new THREE.BoxGeometry(structW + 4, 0.6, 5),
          matMap.concrete
        )
        bridge.position.set(0, crestElZ + 1, sz)
        bridge.castShadow = true
        group.add(bridge)
        // 闸门（简化为薄板）
        for (let i = 0; i < nPiers-1; i++) {
          const gx = -structW/2 + i*spanW + spanW/2
          const gate = new THREE.Mesh(
            new THREE.BoxGeometry(spanW - pierW, wDepth*0.7, 0.3),
            new THREE.MeshStandardMaterial({ color: 0x2c3e50, metalness:0.6, roughness:0.3 })
          )
          gate.position.set(gx, bedElZ + wDepth*0.35, sz)
          group.add(gate)
        }
      } else if (structure.type === 'culvert') {
        // 涵洞：方形箱涵
        const culvert = new THREE.Mesh(
          new THREE.BoxGeometry(structW, 3, 8),
          matMap.culvert
        )
        culvert.position.set(0, bedElZ - 1.5, sz)
        culvert.castShadow = true
        group.add(culvert)
        // 入口
        const hole = new THREE.Mesh(
          new THREE.BoxGeometry(structW*0.7, 2, 8.1),
          new THREE.MeshStandardMaterial({ color: 0x1a1a1a })
        )
        hole.position.set(0, bedElZ - 1.5, sz)
        group.add(hole)
      } else if (structure.type === 'weir') {
        // 溢流堰：梯形断面
        const weirShape = new THREE.Shape()
        weirShape.moveTo(-structW/2 - 4, bedElZ)
        weirShape.lineTo(-structW/2, bedElZ + 3)
        weirShape.lineTo(structW/2, bedElZ + 3)
        weirShape.lineTo(structW/2 + 4, bedElZ)
        weirShape.lineTo(-structW/2 - 4, bedElZ)
        const weirGeo = new THREE.ExtrudeGeometry(weirShape, { depth: 8, bevelEnabled:false })
        const weir = new THREE.Mesh(weirGeo, matMap.weir)
        weir.position.z = sz - 4
        weir.castShadow = true
        group.add(weir)
      }
    }

    // 视角调整
    const centerY = (crest_elevation + bed_elevation)/2
    if (cameraRef.current && controlsRef.current) {
      if (viewMode === 'perspective') {
        controlsRef.current.target.set(0, centerY, 0)
        cameraRef.current.position.set(120, 70, 180)
      }
      controlsRef.current.update()
    }
  }, [designResult, channelLength, bedSlope, showStations, structure, showWater])

  // 水位变化更新水面
  useEffect(() => {
    if (!waterMeshRef.current || !designResult) return
    const { bed_elevation, bed_width, m_slope } = designResult.parameters
    const wD = Math.max(0, waterLevel - bed_elevation)
    if (wD <= 0) { waterMeshRef.current.visible = false; return }
    waterMeshRef.current.visible = showWater
    const ww = bed_width + 2*(m_slope||2)*wD
    waterMeshRef.current.scale.set(ww, 1, 1)
    waterMeshRef.current.position.y = waterLevel - 0.05
  }, [waterLevel, showWater, designResult])

  // 视角切换
  useEffect(() => {
    if (!cameraRef.current || !controlsRef.current || !designResult) return
    const cam = cameraRef.current, ctrl = controlsRef.current
    const cy = (designResult.parameters.crest_elevation + designResult.parameters.bed_elevation)/2
    switch (viewMode) {
      case 'top': cam.position.set(0, cy + 250, 0.01); ctrl.target.set(0, cy, 0); break
      case 'front': cam.position.set(0, cy, L()*0.8); ctrl.target.set(0, cy, 0); break
      case 'side': cam.position.set(200, cy-20, 0); ctrl.target.set(0, cy, 0); break
      default: cam.position.set(120, 70, 180); ctrl.target.set(0, cy, 0)
    }
    ctrl.update()
  }, [viewMode, designResult])
  function L() { return channelLength }

  const applyPreset = (preset: 'dry'|'design'|'flood') => {
    if (!designResult) return
    const { bed_elevation, design_water_level, crest_elevation } = designResult.parameters
    setWaterLevel(preset==='dry'?bed_elevation+0.3:preset==='design'?design_water_level:crest_elevation-0.1)
  }

  const sectionTypeOptions: {id:SectionType,name:string,desc:string}[] = [
    {id:'trapezoidal',name:'梯形断面',desc:'土质堤防最常用'},
    {id:'rectangular',name:'矩形断面',desc:'城镇段重力挡墙'},
    {id:'compound',name:'复式断面',desc:'主槽+滩地'},
  ]

  const updateParam = (key:string, val:any) => setParams(p=>({...p,[key]:val}))

  return (
    <div className="flex flex-col h-full">
      <div className="mb-3 flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 flex items-center gap-2">
            <Cuboid className="w-5 h-5 text-cyan-600"/> 三维可视化
          </h2>
          <p className="text-sm text-neutral-500 mt-0.5">参数化设计三维预览，支持多断面类型、纵坡、典型建筑物</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={handleDesign} disabled={designing} className="btn-primary text-xs px-3 py-1.5">
            {designing?'生成中...':'应用参数生成'}
          </button>
        </div>
      </div>

      <div className="flex-1 flex gap-3 min-h-0">
        {/* 左侧参数面板 */}
        <div className="w-72 flex-shrink-0 bg-white border border-neutral-200 rounded-lg p-3 overflow-y-auto space-y-3.5 text-sm">
          {/* 断面类型选择 */}
          <div>
            <div className="font-medium text-neutral-700 mb-1.5 flex items-center gap-1">
              <Layers className="w-3.5 h-3.5"/> 断面类型
            </div>
            <div className="grid grid-cols-3 gap-1">
              {sectionTypeOptions.map(s => (
                <button key={s.id} onClick={()=>switchSection(s.id)}
                  className={cn("text-xs py-1.5 px-1 rounded border transition-colors",
                    sectionType===s.id?"bg-cyan-50 border-cyan-300 text-cyan-700 font-medium":"bg-white border-neutral-200 text-neutral-600 hover:bg-neutral-50")}>
                  {s.name}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-neutral-400 mt-1">{sectionTypeOptions.find(s=>s.id===sectionType)?.desc}</p>
          </div>

          {/* 断面参数 */}
          <div>
            <div className="font-medium text-neutral-700 mb-1.5 flex items-center gap-1">
              <Ruler className="w-3.5 h-3.5"/> 断面参数
            </div>
            <div className="space-y-1.5">
              {sectionType === 'trapezoidal' && [
                {k:'design_water_level',l:'设计水位(m)',min:90,max:120,step:0.1},
                {k:'bed_elevation',l:'河底高程(m)',min:85,max:115,step:0.1},
                {k:'bed_width',l:'底宽(m)',min:3,max:50,step:0.5},
                {k:'m_slope',l:'边坡系数m',min:1,max:5,step:0.25},
                {k:'freeboard',l:'超高(m)',min:0.3,max:3,step:0.1},
                {k:'crest_width',l:'堤顶宽(m)',min:2,max:15,step:0.5},
              ].map(f=>(
                <div key={f.k} className="flex items-center gap-2">
                  <label className="text-xs text-neutral-500 w-24 flex-shrink-0">{f.l}</label>
                  <input type="number" value={params[f.k]} min={f.min} max={f.max} step={f.step}
                    onChange={e=>updateParam(f.k,parseFloat(e.target.value)||0)} className="flex-1 input text-xs py-1 px-2"/>
                </div>))}
              {sectionType === 'rectangular' && [
                {k:'design_water_level',l:'设计水位(m)',min:90,max:120,step:0.1},
                {k:'bed_elevation',l:'河底高程(m)',min:85,max:115,step:0.1},
                {k:'bed_width',l:'河宽(m)',min:3,max:30,step:0.5},
                {k:'wall_thickness',l:'墙顶宽(m)',min:0.3,max:1.5,step:0.1},
                {k:'wall_bottom_thickness',l:'墙底宽(m)',min:0.8,max:4,step:0.1},
                {k:'freeboard',l:'超高(m)',min:0.3,max:2,step:0.1},
              ].map(f=>(
                <div key={f.k} className="flex items-center gap-2">
                  <label className="text-xs text-neutral-500 w-24 flex-shrink-0">{f.l}</label>
                  <input type="number" value={params[f.k]} min={f.min} max={f.max} step={f.step}
                    onChange={e=>updateParam(f.k,parseFloat(e.target.value)||0)} className="flex-1 input text-xs py-1 px-2"/>
                </div>))}
              {sectionType === 'compound' && [
                {k:'design_water_level',l:'设计水位(m)',min:90,max:120,step:0.1},
                {k:'bed_elevation',l:'河底高程(m)',min:85,max:115,step:0.1},
                {k:'main_channel_width',l:'主槽宽(m)',min:5,max:40,step:1},
                {k:'main_channel_depth',l:'主槽深(m)',min:1,max:8,step:0.5},
                {k:'floodplain_width',l:'滩地宽(m)',min:5,max:50,step:1},
                {k:'freeboard',l:'超高(m)',min:0.3,max:3,step:0.1},
              ].map(f=>(
                <div key={f.k} className="flex items-center gap-2">
                  <label className="text-xs text-neutral-500 w-24 flex-shrink-0">{f.l}</label>
                  <input type="number" value={params[f.k]} min={f.min} max={f.max} step={f.step}
                    onChange={e=>updateParam(f.k,parseFloat(e.target.value)||0)} className="flex-1 input text-xs py-1 px-2"/>
                </div>))}
              <div className="flex items-center gap-2">
                <label className="text-xs text-neutral-500 w-24 flex-shrink-0">护岸类型</label>
                <select value={params.revetment_type} onChange={e=>updateParam('revetment_type',e.target.value)} className="flex-1 input text-xs py-1 px-2">
                  <option value="stone_mortar">浆砌石</option><option value="concrete">混凝土</option>
                  <option value="ecological">生态护岸</option><option value="stone_dry">干砌石</option><option value="grass">草皮护坡</option>
                </select>
              </div>
            </div>
          </div>

          {/* 纵断面与河道参数 */}
          <div className="border-t border-neutral-100 pt-3">
            <div className="font-medium text-neutral-700 mb-1.5 flex items-center gap-1">
              <Milestone className="w-3.5 h-3.5"/> 纵断面
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <label className="text-xs text-neutral-500 w-24 flex-shrink-0">河道长度(m)</label>
                <input type="number" min={50} max={1000} step={10} value={channelLength}
                  onChange={e=>setChannelLength(parseFloat(e.target.value)||200)} className="flex-1 input text-xs py-1 px-2"/>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-neutral-500 w-24 flex-shrink-0">纵坡 i</label>
                <input type="number" min={0} max={0.05} step={0.0005} value={bedSlope}
                  onChange={e=>setBedSlope(parseFloat(e.target.value)||0)} className="flex-1 input text-xs py-1 px-2"/>
              </div>
            </div>
          </div>

          {/* 建筑物 */}
          <div className="border-t border-neutral-100 pt-3">
            <div className="font-medium text-neutral-700 mb-1.5 flex items-center gap-1">
              <Building2 className="w-3.5 h-3.5"/> 渠系建筑物
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <label className="text-xs text-neutral-500 w-24 flex-shrink-0">类型</label>
                <select value={structure.type} onChange={e=>setStructure(s=>({...s,type:e.target.value as StructureType}))} className="flex-1 input text-xs py-1 px-2">
                  <option value="none">无</option><option value="sluice">水闸</option>
                  <option value="culvert">涵洞</option><option value="weir">溢流堰</option>
                </select>
              </div>
              {structure.type!=='none' && <>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-neutral-500 w-24 flex-shrink-0">位置(m)</label>
                  <input type="number" min={0} max={channelLength} step={10} value={structure.position_m}
                    onChange={e=>setStructure(s=>({...s,position_m:parseFloat(e.target.value)||100}))} className="flex-1 input text-xs py-1 px-2"/>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-neutral-500 w-24 flex-shrink-0">宽度(m)</label>
                  <input type="number" min={3} max={30} step={0.5} value={structure.width_m}
                    onChange={e=>setStructure(s=>({...s,width_m:parseFloat(e.target.value)||8}))} className="flex-1 input text-xs py-1 px-2"/>
                </div>
              </>}
            </div>
          </div>

          {/* 水位控制 */}
          <div className="border-t border-neutral-100 pt-3">
            <div className="font-medium text-neutral-700 mb-1.5 flex items-center gap-1 text-blue-600">
              <Droplets className="w-3.5 h-3.5"/> 水位控制
            </div>
            <input type="range" min={designResult?.parameters.bed_elevation||90} max={designResult?.parameters.crest_elevation||105} step={0.1} value={waterLevel}
              onChange={e=>setWaterLevel(parseFloat(e.target.value))} className="w-full accent-blue-500"/>
            <div className="flex justify-between text-[10px] text-neutral-400 mt-0.5">
              <span>河底{designResult?.parameters.bed_elevation.toFixed(1)}m</span>
              <span className="font-medium text-blue-600">{waterLevel.toFixed(1)}m</span>
              <span>堤顶{designResult?.parameters.crest_elevation.toFixed(1)}m</span>
            </div>
            <div className="flex gap-1 mt-2">
              <button onClick={()=>applyPreset('dry')} className="flex-1 text-[10px] py-1 bg-neutral-100 hover:bg-neutral-200 rounded">干涸</button>
              <button onClick={()=>applyPreset('design')} className="flex-1 text-[10px] py-1 bg-blue-100 text-blue-700 hover:bg-blue-200 rounded">设计水位</button>
              <button onClick={()=>applyPreset('flood')} className="flex-1 text-[10px] py-1 bg-red-100 text-red-700 hover:bg-red-200 rounded">漫堤</button>
            </div>
          </div>

          {/* 显示选项 */}
          <div className="border-t border-neutral-100 pt-3">
            <div className="font-medium text-neutral-700 mb-1.5 flex items-center gap-1">
              <Eye className="w-3.5 h-3.5"/> 显示
            </div>
            <div className="space-y-1 text-xs text-neutral-600">
              <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" checked={showWater} onChange={e=>setShowWater(e.target.checked)}/>水面</label>
              <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" checked={showGrid} onChange={e=>setShowGrid(e.target.checked)}/>网格</label>
              <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" checked={showStations} onChange={e=>setShowStations(e.target.checked)}/>里程桩</label>
              <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" checked={autoRotate} onChange={e=>setAutoRotate(e.target.checked)}/>自动旋转</label>
            </div>
          </div>

          {/* 视角 */}
          <div className="border-t border-neutral-100 pt-3">
            <div className="font-medium text-neutral-700 mb-1.5 flex items-center gap-1">
              <RotateCcw className="w-3.5 h-3.5"/> 视角
            </div>
            <div className="grid grid-cols-2 gap-1">
              {([['perspective','透视'],['top','俯视'],['front','正视'],['side','侧视']] as const).map(([k,l])=>(
                <button key={k} onClick={()=>setViewMode(k)}
                  className={cn("text-xs py-1 rounded border",
                    viewMode===k?"bg-cyan-50 border-cyan-300 text-cyan-700":"bg-white border-neutral-200 text-neutral-600 hover:bg-neutral-50")}>{l}</button>
              ))}
            </div>
          </div>

          {/* 结果摘要 */}
          {designResult && (
            <div className="border-t border-neutral-100 pt-3">
              <div className="font-medium text-neutral-700 mb-1.5 flex items-center gap-1">
                <Settings className="w-3.5 h-3.5"/> 结果
              </div>
              <div className="text-xs space-y-0.5 text-neutral-600">
                <div>类型: <span className="font-medium text-neutral-800">{designResult.section_name}</span></div>
                <div>堤顶: <span className="font-medium text-neutral-800">{designResult.parameters.crest_elevation}m</span></div>
                <div>水深: <span className="font-medium text-neutral-800">{designResult.parameters.water_depth}m</span></div>
                <div>断面宽: <span className="font-medium text-neutral-800">{designResult.geometry.section_width_m.toFixed(1)}m</span></div>
                <div>抗滑Kc: <span className={cn("font-medium",designResult.stability.pass?"text-emerald-600":"text-red-600")}>{designResult.stability.anti_slide_Kc.toFixed(2)}</span></div>
                <div>每延米: <span className="font-medium text-neutral-800">{(designResult.costs.total_cost_yuan_per_m/10000).toFixed(2)}万元</span></div>
                <div className="text-neutral-400 mt-1">纵坡 i={bedSlope}, 河道长{channelLength}m</div>
              </div>
            </div>
          )}
        </div>

        {/* 右侧3D视图 */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center justify-between mb-2 px-1">
            <button onClick={()=>setViewMode('perspective')} className="p-1.5 hover:bg-neutral-100 rounded text-neutral-500"><RotateCcw className="w-4 h-4"/></button>
            <span className="text-xs text-neutral-400 ml-1">左键旋转 · 右键平移 · 滚轮缩放</span>
            <div className="flex items-center gap-2 text-[10px] text-neutral-400">
              <span className="inline-flex items-center gap-0.5"><span className="w-2.5 h-2.5 rounded-sm inline-block" style={{background:'#c49a6c'}}/>堤身</span>
              <span className="inline-flex items-center gap-0.5"><span className="w-2.5 h-2.5 rounded-sm inline-block" style={{background:revMatColor(revetment_name(designResult))}}/>护岸</span>
              <span className="inline-flex items-center gap-0.5"><span className="w-2.5 h-2.5 rounded-sm inline-block" style={{background:'#3b82f6',opacity:0.6}}/>水体</span>
              <span className="inline-flex items-center gap-0.5"><span className="w-2.5 h-2.5 rounded-sm inline-block" style={{background:'#4a6fa5'}}/>建筑物</span>
            </div>
          </div>
          <div ref={containerRef} className="flex-1 bg-gradient-to-b from-sky-50 to-slate-100 rounded-lg border border-neutral-200 overflow-hidden min-h-[400px]"/>
        </div>
      </div>
    </div>
  )
}

function revetment_name(r: SectionDesignResult | null): string { return r?.parameters?.revetment_name || '浆砌石' }
function revMatColor(name: string): string {
  if (name.includes('混凝土')) return '#b0b0b0'
  if (name.includes('生态') || name.includes('草皮')) return '#6b8e4e'
  return '#808080'
}
