from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.services.llm_service import llm_service

router = APIRouter()


class CADGenerateRequest(BaseModel):
    description: str
    template: Optional[str] = None
    parameters: Optional[dict] = None


class CADTemplate(BaseModel):
    id: str
    name: str
    category: str
    description: str
    default_prompt: str
    icon: str


# 水利工程常用 CAD 构件模板
WATER_TEMPLATES: List[dict] = [
    {
        "id": "arch_dam",
        "name": "拱坝",
        "category": "挡水建筑物",
        "description": "混凝土拱坝三维模型，含坝体、溢流堰、坝顶结构",
        "default_prompt": "A concrete arch dam with spillway, realistic dimensions, parametric model with adjustable height, crest length, and arch radius",
        "icon": "🏔️",
    },
    {
        "id": "gravity_dam",
        "name": "重力坝",
        "category": "挡水建筑物",
        "description": "混凝土重力坝典型断面，含坝顶、上下游坝坡、廊道",
        "default_prompt": "A concrete gravity dam cross-section with upstream and downstream faces, drainage gallery, spillway, parametric dimensions",
        "icon": "🧱",
    },
    {
        "id": "embankment_dam",
        "name": "土石坝",
        "category": "挡水建筑物",
        "description": "碾压式土石坝，含心墙/斜墙、反滤层、护坡",
        "default_prompt": "An embankment dam with clay core, filter layers, riprap slope protection, parametric model with height, crest width, slope ratios",
        "icon": "⛰️",
    },
    {
        "id": "spillway",
        "name": "溢洪道",
        "category": "泄水建筑物",
        "description": "开敞式溢洪道，含控制段、泄槽、消力池",
        "default_prompt": "An open channel spillway with control weir, chute, and stilling basin energy dissipator, parametric design",
        "icon": "🌊",
    },
    {
        "id": "sluice",
        "name": "水闸",
        "category": "泄水建筑物",
        "description": "开敞式水闸，含闸室、闸门、桥墩、消力池",
        "default_prompt": "A sluice gate structure with piers, gate openings, bridge deck, stilling basin, parametric model with adjustable span and gate height",
        "icon": "🚪",
    },
    {
        "id": "culvert",
        "name": "涵洞/隧洞",
        "category": "输水建筑物",
        "description": "圆形/城门洞形输水隧洞，含进口、洞身、出口",
        "default_prompt": "A culvert or tunnel with circular cross-section, inlet and outlet structures, parametric model with diameter and length",
        "icon": "🕳️",
    },
    {
        "id": "aqueduct",
        "name": "渡槽",
        "category": "输水建筑物",
        "description": "梁式渡槽，含槽身、排架、基础",
        "default_prompt": "An aqueduct bridge with U-shaped or rectangular channel, supporting piers and foundations, parametric design",
        "icon": "🌉",
    },
    {
        "id": "retaining_wall",
        "name": "挡土墙",
        "category": "边坡防护",
        "description": "重力式/悬臂式挡土墙，含排水孔、墙后回填",
        "default_prompt": "A gravity retaining wall with drainage holes, backfill, parametric model with height, base width, and wall thickness",
        "icon": "🧱",
    },
    {
        "id": "levee",
        "name": "堤防",
        "category": "防洪工程",
        "description": "河道堤防标准断面，含堤顶、堤坡、防渗体",
        "default_prompt": "A levee or embankment cross-section with crest, slopes, seepage cutoff, parametric model with height and crest width",
        "icon": "🏞️",
    },
    {
        "id": "pipe_penstock",
        "name": "压力管道",
        "category": "水电站",
        "description": "压力钢管/预制混凝土管，含镇墩、支墩、伸缩节",
        "default_prompt": "A penstock pipe with anchor blocks, support piers, expansion joints, parametric model with diameter, length, and bend angle",
        "icon": "🔧",
    },
    {
        "id": "turbine",
        "name": "水轮机",
        "category": "水电站",
        "description": "混流式/轴流式水轮机转轮，含蜗壳、导叶",
        "default_prompt": "A Francis turbine runner with spiral case, wicket gates, parametric model with adjustable diameter and blade count",
        "icon": "⚙️",
    },
    {
        "id": "flume",
        "name": "量水堰/水槽",
        "category": "水文测验",
        "description": "巴歇尔量水槽/薄壁堰，用于流量测量",
        "default_prompt": "A Parshall flume or sharp-crested weir for flow measurement, parametric model with throat width",
        "icon": "📏",
    },
    {
        "id": "check_dam",
        "name": "谷坊/拦沙坝",
        "category": "水土保持",
        "description": "小型拦沙坝/谷坊，含溢洪口、消能设施",
        "default_prompt": "A check dam for sediment control with spillway notch, energy dissipator, parametric model with height and width",
        "icon": "🏔️",
    },
    {
        "id": "pump_station",
        "name": "泵站",
        "category": "排灌工程",
        "description": "排涝/灌溉泵站，含泵房、进出水池、机组",
        "default_prompt": "A pump station building with intake basin, pump room, discharge outlet, parametric model",
        "icon": "💧",
    },
    {
        "id": "channel_section",
        "name": "渠道断面",
        "category": "灌溉排水",
        "description": "梯形/矩形渠道标准断面，含衬砌、堤顶道路",
        "default_prompt": "A trapezoidal channel cross-section with concrete lining, bank roads, parametric model with depth, bottom width, side slope",
        "icon": "〰️",
    },
    {
        "id": "bridge",
        "name": "桥梁",
        "category": "交叉建筑物",
        "description": "简支梁桥/拱桥，含桥墩、桥台、桥面",
        "default_prompt": "A simple beam bridge with piers, abutments, deck, parametric model with span length, width, and pier height",
        "icon": "🌉",
    },
]


CAD_SYSTEM_PROMPT = """You are a CAD engineering assistant specializing in hydraulic and water conservancy engineering.
Your task is to convert the user's natural language description (which may be in Chinese) into a precise, well-structured
English prompt for generating OpenSCAD 3D models.

Guidelines for your output:
1. Output ONLY the English prompt text, nothing else (no explanations, no markdown, no code blocks)
2. Start with the main object name (e.g., "A parametric concrete arch dam...")
3. Specify it should be a parametric OpenSCAD model
4. Include key geometric features with realistic engineering proportions
5. Mention adjustable parameters (height, width, diameter, thickness, etc.)
6. Add engineering details appropriate for the structure
7. Use precise engineering terminology
8. Keep the prompt clear, specific, and between 30-80 words
9. Do NOT include measurements in the prompt - the AI will determine appropriate scale
10. End with "high quality, manifold geometry suitable for 3D printing"

Example output:
A parametric concrete gravity dam with triangular cross-section, upstream vertical face, downstream sloped face at 0.75:1 ratio,
drainage gallery at 1/3 height from base, spillway crest with radial gates, stilling basin at toe, parametric dimensions
for dam height, crest width, base width, high quality, manifold geometry suitable for 3D printing
"""


@router.get("/templates")
async def list_templates(category: Optional[str] = None):
    """获取水利 CAD 构件模板列表"""
    templates = WATER_TEMPLATES
    if category:
        templates = [t for t in templates if t["category"] == category]
    
    categories = list(set(t["category"] for t in WATER_TEMPLATES))
    return {
        "templates": templates,
        "categories": sorted(categories),
    }


@router.post("/generate-prompt")
async def generate_cad_prompt(request: CADGenerateRequest):
    """根据中文描述生成英文 OpenSCAD 提示词"""
    description = request.description
    
    # 如果选择了模板，将模板信息加入描述
    if request.template:
        template = next((t for t in WATER_TEMPLATES if t["id"] == request.template), None)
        if template:
            description = f"{description}. 参考构件类型：{template['name']}（{template['description']}）"
    
    # 调用 LLM 生成专业英文提示词
    prompt = f"Convert this hydraulic engineering description into an OpenSCAD prompt: {description}"
    generated_prompt = await llm_service.generate(prompt, system_prompt=CAD_SYSTEM_PROMPT)
    
    # 如果是 mock 模式或生成失败，提供一个基础 prompt
    if not generated_prompt or len(generated_prompt) < 20:
        # 查找匹配的模板
        if request.template:
            template = next((t for t in WATER_TEMPLATES if t["id"] == request.template), None)
            if template:
                generated_prompt = template["default_prompt"]
            else:
                generated_prompt = f"A parametric 3D model of {description}, with adjustable dimensions, high quality, manifold geometry suitable for 3D printing"
        else:
            generated_prompt = f"A parametric 3D model of {description}, with adjustable dimensions, engineering details, high quality, manifold geometry suitable for 3D printing"
    
    return {
        "prompt": generated_prompt.strip(),
        "original_description": request.description,
        "template_used": request.template,
    }


@router.get("/info")
async def cad_info():
    """获取 CAD 功能信息"""
    return {
        "name": "智能CAD设计",
        "description": "基于AI的水利工程三维CAD模型生成，支持自然语言描述和参数化模板",
        "cadam_url": "https://adam.new/cadam",
        "supported_formats": ["STL", "SCAD", "DXF"],
        "template_count": len(WATER_TEMPLATES),
        "categories": sorted(list(set(t["category"] for t in WATER_TEMPLATES))),
        "usage_tips": [
            "使用自然语言描述您想要的水利工程构件",
            "可选择预置模板快速生成常见构件",
            "生成的提示词将自动发送到CADAM编辑器",
            "在CADAM中可通过滑块调整参数尺寸",
            "支持导出STL用于3D打印或BIM建模",
        ],
    }
