# 蜀水智库 AI

面向水利电力勘测设计院的本地知识库与 AI 智能问答系统，集成了文档管理、智能问答、合规审查、历史工程参考、防汛预案生成、ISO管理体系文档自动填写等功能。

## 项目架构

```
shushui-ai/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/     # API路由
│   │   │       ├── documents.py    # 文档管理
│   │   │       ├── qa.py           # 智能问答
│   │   │       ├── review.py       # 合规审查
│   │   │       ├── projects.py     # 历史工程
│   │   │       ├── flood.py        # 防汛预案
│   │   │       ├── admin.py        # 管理后台
│   │   │       ├── upload.py       # 文件上传
│   │   │       └── iso.py          # ISO体系文档（已集成）
│   │   ├── core/           # 核心配置
│   │   │   ├── config.py   # 配置项
│   │   │   └── database.py # 数据库连接
│   │   ├── models/         # SQLAlchemy数据模型
│   │   ├── schemas/        # Pydantic数据模式
│   │   ├── services/       # 业务服务层
│   │   │   ├── document_parser.py # 文档解析
│   │   │   ├── embedding.py       # 向量化
│   │   │   ├── llm_service.py     # LLM调用
│   │   │   ├── vector_store.py    # 向量存储
│   │   │   └── iso_service.py     # ISO文档生成（已集成）
│   │   ├── main.py         # 应用入口
│   │   └── seed_data.py    # 初始化数据
│   ├── resources/
│   │   └── iso_templates/  # ISO模板目录
│   ├── uploads/            # 文件上传目录
│   ├── vector_db/          # 向量数据库存储
│   ├── requirements.txt    # Python依赖
│   └── Dockerfile
├── frontend/               # React + TypeScript 前端
│   ├── src/
│   │   ├── api/            # API客户端
│   │   ├── components/     # 组件
│   │   │   └── Layout.tsx  # 主布局（含导航）
│   │   ├── pages/          # 页面
│   │   │   ├── Dashboard.tsx   # 首页仪表盘
│   │   │   ├── QA.tsx          # 智能问答
│   │   │   ├── Upload.tsx      # 文档上传
│   │   │   ├── Projects.tsx    # 历史工程
│   │   │   ├── Flood.tsx       # 防汛预案
│   │   │   ├── Review.tsx      # 合规审查
│   │   │   ├── ISO.tsx         # ISO文档生成（已集成）
│   │   │   └── Admin.tsx       # 管理后台
│   │   ├── App.tsx         # 路由配置
│   │   ├── main.tsx        # 入口文件
│   │   └── index.css       # 全局样式
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml      # Docker编排
└── .gitignore
```

## 核心功能模块

| 模块 | 路径 | 功能说明 |
|------|------|----------|
| 首页仪表盘 | `/` | 系统概览、快捷入口、统计数据 |
| 智能问答 | `/qa` | 基于RAG的知识库问答，支持引用溯源 |
| 文档上传 | `/upload` | 上传文档（PDF/DOCX/TXT），自动解析建库 |
| 历史工程 | `/projects` | 参考历史类似工程案例 |
| 防汛预案 | `/flood` | 防汛预案智能生成 |
| 合规审查 | `/review` | 设计文档合规性自动审查 |
| **ISO体系文档** | `/iso` | **上传设计报告，自动填写ISO管理体系附表（已集成）** |
| 管理后台 | `/admin` | 用户管理、系统配置 |

## 技术栈

### 后端
- **框架**: FastAPI 0.104
- **ORM**: SQLAlchemy 2.0
- **数据库**: SQLite（可扩展PostgreSQL）
- **文档解析**: python-docx, PyPDF2, pdfplumber
- **向量化**: sentence-transformers (text2vec-base-chinese)
- **向量存储**: FAISS
- **LLM**: 支持OpenAI/火山引擎/Mock模式

### 前端
- **框架**: React 18 + TypeScript
- **构建**: Vite 5
- **样式**: Tailwind CSS 3
- **路由**: React Router 6
- **图标**: Lucide React
- **HTTP**: Axios

## 快速启动

### 方式一：本地开发

#### 后端启动
```bash
cd backend
pip install -r requirements.txt --break-system-packages
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端API文档：http://localhost:8000/docs

#### 前端启动
```bash
cd frontend
npm install
npm run dev
```

前端访问：http://localhost:5173

### 方式二：Docker Compose
```bash
docker-compose up -d
```

## ISO文档生成使用说明

1. 将ISO模板文件 `管理体系附表-设计部分.docx` 放入 `backend/resources/iso_templates/` 目录
2. 在前端导航栏点击「ISO体系」
3. 上传项目设计报告（支持.docx/.pdf/.txt格式）
4. 系统自动解析文档并提取项目信息（项目名称、业主单位、设计阶段、日期等）
5. 人工确认/补充信息后，生成填写完成的ISO文档
6. 下载生成的Word文档

## 配置说明

后端配置可通过环境变量或 `.env` 文件设置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| MOCK_MODE | true | Mock模式（无需真实LLM即可运行） |
| LLM_PROVIDER | mock | LLM提供商：mock/openai/volcano |
| EMBEDDING_PROVIDER | local | Embedding提供商 |
| DATABASE_URL | sqlite:///./shushui_ai.db | 数据库连接 |
| UPLOAD_DIR | ./uploads | 文件上传目录 |
| VECTOR_DB_PATH | ./vector_db | 向量库存储路径 |
