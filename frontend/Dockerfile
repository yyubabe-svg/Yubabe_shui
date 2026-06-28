# ==============================
# 前端生产构建 - 多阶段构建
# ==============================
FROM node:18-alpine AS builder

WORKDIR /app

# 先复制package文件利用Docker缓存
COPY package*.json ./
RUN npm ci --registry=https://registry.npmmirror.com

# 复制源码并构建
COPY . .
RUN npm run build

# ==============================
# 生产环境 - Nginx托管静态资源
# ==============================
FROM nginx:alpine

# 复制Nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物（包含qrcodes目录）
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
