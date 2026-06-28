import os
import mimetypes
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal

# 确保常见图片/矢量MIME类型被正确识别（部分系统mimetypes数据库缺少这些）
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('application/zip', '.zip')

# 导入所有模型确保表被创建
import app.models  # noqa

from app.api.routes import documents, qa, review, projects, flood, admin, upload, iso, usage, payment, cad, agent, workspace, tools, phase3, phase4, compliance

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
)

# CORS - 修复7：添加常见生产环境本地地址
default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://0.0.0.0:5173",
]
cors_env = os.getenv("CORS_ORIGINS", "")
if cors_env:
    cors_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
else:
    cors_origins = default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加中间件禁止缓存，确保总是加载最新版本
@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    # 对HTML和API响应禁止缓存
    if request.url.path.startswith("/api") or request.url.path == "/" or request.url.path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 注册API路由
app.include_router(documents.router, prefix="/api/documents", tags=["文档管理"])
app.include_router(qa.router, prefix="/api/qa", tags=["智能问答"])
app.include_router(review.router, prefix="/api/review", tags=["合规审查"])
app.include_router(projects.router)  # prefix/tags已在router中定义: /api/projects [项目管理]
app.include_router(flood.router)     # prefix/tags已在router中定义: /api/flood [防汛辅助]
app.include_router(admin.router)     # prefix/tags已在router中定义: /api/admin [管理后台]
app.include_router(upload.router, prefix="/api/upload", tags=["文件上传"])
app.include_router(iso.router, prefix="/api/iso", tags=["ISO体系文档"])
app.include_router(usage.router, prefix="/api/usage", tags=["用户与额度"])
app.include_router(payment.router, prefix="/api/payment", tags=["支付"])
app.include_router(cad.router)       # prefix/tags已在router中定义: /api/cad [智能CAD设计]
app.include_router(agent.router, prefix="/api/agent", tags=["AI Agent"])
app.include_router(workspace.router) # prefix/tags已在router中定义: /api/workspace [项目工作台]
app.include_router(tools.router)     # prefix/tags已在router中定义: /api/tools [第二阶段工具]
app.include_router(phase3.router)    # prefix/tags已在router中定义: /api/phase3 [第三阶段工具]
app.include_router(phase4.router)    # prefix/tags已在router中定义: /api/phase4 [第四阶段工具]
app.include_router(compliance.router) # prefix/tags已在router中定义: /api/compliance [合规初审]


@app.get("/health", tags=["系统"])
def health_check():
    return {"status": "healthy"}


# 挂载前端静态文件（生产模式）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")
FRONTEND_PUBLIC = os.path.join(PROJECT_ROOT, "frontend", "public")

if os.path.exists(FRONTEND_DIST):
    # 挂载assets目录（JS/CSS等带hash的资源）
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    def _find_static_file(rel_path: str):
        """在dist和public目录中查找静态文件"""
        # 先在dist中查找
        dist_path = os.path.join(FRONTEND_DIST, rel_path)
        if os.path.isfile(dist_path):
            return dist_path
        # 再在public中查找（qrcodes等）
        public_path = os.path.join(FRONTEND_PUBLIC, rel_path)
        if os.path.isfile(public_path):
            return public_path
        return None

    # SPA fallback + 静态文件服务
    @app.get("/{full_path:path}", tags=["前端"])
    async def serve_frontend(full_path: str):
        # API路由和docs不走前端
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json", "health"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)

        # 如果请求路径对应的静态文件存在，直接返回
        if full_path:
            static_file = _find_static_file(full_path)
            if static_file:
                media_type = mimetypes.guess_type(static_file)[0]
                return FileResponse(static_file, media_type=media_type)

        # 否则返回index.html（SPA路由）
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "前端未构建，请先运行 npm run build", "docs": "/docs"}
else:
    @app.get("/", tags=["系统"])
    def root():
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "running",
            "docs": "/docs",
            "message": "前端未构建，开发模式请运行 npm run dev",
        }


# 初始化Mock数据和水利规范知识库
@app.on_event("startup")
def init_seed_data():
    db = SessionLocal()
    try:
        from app.seed_data import init_mock_data
        init_mock_data(db)
    except Exception as e:
        print(f"初始化基础数据失败: {e}")
    
    try:
        from app.seed_form_templates import seed_form_templates
        seed_form_templates(db)
    except Exception as e:
        print(f"初始化表单模板失败（可忽略）: {e}")
    
    try:
        from app.seed_section_templates import seed_section_templates
        seed_section_templates(db)
    except Exception as e:
        print(f"初始化章节模板失败（可忽略）: {e}")
    
    # 修复7：初始化合规模板
    try:
        from app.compliance_seed import init_compliance_templates
        init_compliance_templates(db)
    except Exception as e:
        print(f"初始化合规模板失败（可忽略）: {e}")
    
    db.close()

    # 导入水利核心规范知识库
    try:
        from app.water_standards_seed import seed_standards_to_vector_store
        seed_standards_to_vector_store()
    except Exception as e:
        print(f"导入水利规范知识库失败（可忽略，不影响系统运行）: {e}")
