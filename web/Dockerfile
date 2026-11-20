# 构建 Nuxt 前端镜像：构建期注入 API 地址（容器间通信），运行 node server
# ----- 构建阶段 -----
FROM node:22-alpine AS builder

WORKDIR /app

ARG API_BASE=http://api:8000
ENV NUXT_PUBLIC_API_BASE=$API_BASE

# better-sqlite3（@nuxt/content 依赖）是原生模块，alpine/musl 无预编译产物，需要编译工具链
RUN apk add --no-cache python3 make g++ libc6-compat

COPY package.json ./
RUN npm install --registry=https://registry.npmmirror.com

COPY . .
RUN npm run build

# ----- 运行阶段 -----
FROM node:22-alpine

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.output ./.output

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
