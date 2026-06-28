FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖（PyMuPDF需要libgl1/libglib2.0，faiss需要libgomp1/libopenblas）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p /app/uploads /app/vector_db /app/db_data /app/resources/iso_templates

EXPOSE 8000

# 生产环境使用 Gunicorn + Uvicorn workers
# workers=1 防止SQLite多进程写锁定，同时降低内存占用（2核4G配置适用）
# timeout=300 适配大文件上传和AI生成耗时操作
CMD ["gunicorn", "app.main:app", \
     "--workers", "1", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "300", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
