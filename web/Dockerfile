# 构建 Nuxt 前端镜像：构建期注入 API 地址（容器间通信），运行 node server
# 说明：用 node:22-slim（Debian glibc）而非 alpine——better-sqlite3（@nuxt/content 依赖）
# 是原生模块，glibc 平台有官方预编译二进制，配合 npmmirror 二进制镜像直接下载，
# 免去 apk 安装 gcc/make + 源码编译（2C 机器上可省 30+ 分钟构建时间）
# ----- 构建阶段 -----
FROM node:22-slim AS builder

WORKDIR /app

ARG API_BASE=http://api:8000
ENV NUXT_PUBLIC_API_BASE=$API_BASE
# better-sqlite3 预编译产物走 npmmirror（GitHub 在境内不可达）
ENV npm_config_better_sqlite3_binary_host=https://registry.npmmirror.com/-/binary/better-sqlite3

COPY package.json ./
RUN npm install --registry=https://registry.npmmirror.com

COPY . .
RUN npm run build

# ----- 运行阶段 -----
FROM node:22-slim

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.output ./.output

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
