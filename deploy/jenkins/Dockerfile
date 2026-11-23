# 自定义 Jenkins 镜像：在官方 lts 基础上补装 docker CLI 与 compose 插件
# 官方 jenkins/jenkins:lts 不带 docker CLI，流水线的语法检查（docker run）与
# 部署（docker compose）都无法执行；构建进镜像里，容器重建不丢失
FROM jenkins/jenkins:lts

USER root

# apt 换腾讯云内网镜像（trixie 使用 debian.sources 布局）
RUN sed -i "s|deb.debian.org|mirrors.cloud.tencent.com|g; s|security.debian.org|mirrors.cloud.tencent.com|g" \
      /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list 2>/dev/null || true

# docker CLI + compose 插件走阿里云镜像源（docker-ce 官方源的国内镜像）
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
      > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER jenkins
