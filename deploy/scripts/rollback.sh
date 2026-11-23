#!/usr/bin/env bash
# =============================================================================
# 一键回滚脚本：把线上 web/api 容器回退到任意历史构建版本（秒级，无需重新构建）
# =============================================================================
#
# 前提（由 Jenkins 流水线自动维护）：
#   - 每次部署成功的镜像都有双标签：yuxm-web:<构建号>（版本标签，不移动）
#     和 yuxm-web:latest（运行引用）
#   - 健康检查通过后，流水线在部署目录写入两个状态文件：
#       .deployed_build  —— 当前线上版本号
#       .rollback_build  —— 上一条线上版本号
#
# 用法（在宿主机执行，目录任意）：
#   bash rollback.sh status            # 查看当前版本、回滚点、可用镜像列表
#   bash rollback.sh                   # 回滚到上一个成功部署的版本（.rollback_build）
#   bash rollback.sh 42                # 回滚到指定构建版本 yuxm-web:42 / yuxm-api:42
#
# 原理：回滚 = 把目标历史版本的镜像重新打上 latest 标签，
#       再 docker compose up -d --no-build 让容器按新 latest 重建。
#       镜像早已存在于本机，因此不拉代码、不构建、不装依赖，秒级完成。
#
# 幂等性：重复执行同一命令无副作用（tag 幂等、up -d 配置无变化则不动容器）。
# =============================================================================
set -euo pipefail
# -e : 任何命令失败立即退出（避免回滚到一半继续执行更危险的操作）
# -u : 引用未定义变量报错（防止手误变量名静默变成空串）
# -o pipefail : 管道中任一环节失败视为整体失败（mysqldump 失败但 gzip 成功也算失败）

# 自动定位项目根（scripts/ 的上一级），保证从任意 CWD 执行都正确
DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# 状态文件目录：默认为本部署目录；在 Jenkins 容器内执行时可被
# ROLLBACK_STATE_DIR=/host-deploy 环境变量覆盖（同一批文件的容器内路径）
STATE_DIR="${ROLLBACK_STATE_DIR:-${DEPLOY_DIR}}"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"

# 读取两个状态文件；文件不存在（从未成功部署过）时输出占位文案
deployed_build()  { cat "${STATE_DIR}/.deployed_build"  2>/dev/null || echo "未记录"; }
rollback_point()  { cat "${STATE_DIR}/.rollback_build"  2>/dev/null || echo "无"; }

# 回滚后的健康检查：与流水线同一判据（后端 /api/health + 前台首页）
# 本脚本在宿主机执行，127.0.0.1:80 就是宿主机 nginx，直接 curl 即可
# 5 次探测 × 5 秒间隔，给容器重启和应用初始化留缓冲
health_check() {
  echo "[rollback] 健康检查..."
  local ok=0
  for i in 1 2 3 4 5; do
    sleep 5
    if curl -fsS http://127.0.0.1/api/health > /dev/null 2>&1 \
       && curl -fsS http://127.0.0.1/ > /dev/null 2>&1; then
      echo "[rollback] 健康检查通过（第 ${i} 次探测）"
      ok=1
      break
    fi
    echo "[rollback] 第 ${i} 次探测未就绪，等待中..."
  done
  # 全部失败：退出码非 0，提示排查方向（此时旧版本容器可能也停了，需人工介入）
  [ "$ok" -eq 1 ] || { echo "[rollback] 回滚后健康检查失败！请执行 docker compose logs api web 排查"; exit 1; }
}

# 核心动作：retag + 重建容器 + 更新状态文件 + 健康检查
# 参数 target：目标构建号
retag_and_up() {
  local target="$1"
  echo "[rollback] 将版本 #${target} 重新打 latest 标签并重启容器..."
  # 1) 把历史版本镜像重新打为 latest —— compose 的 image 字段引用的就是 latest
  docker tag "yuxm-web:${target}" yuxm-web:latest
  docker tag "yuxm-api:${target}" yuxm-api:latest
  # 2) --no-build 重建 web/api 容器：容器按新 latest 重新创建，
  #    mysql/redis/nginx 不受影响；compose 发现 latest 指向变了会自动替换容器
  docker compose -f "${COMPOSE_FILE}" up -d --no-build web api
  # 3) 更新当前版本记录（注意：.rollback_build 不动——再执行一次无参回滚
  #    会回到同一个目标，如需"回滚回滚"请显式指定构建号）
  echo "${target}" > "${STATE_DIR}/.deployed_build"
  # 4) 验证回滚后的服务确实可用
  health_check
  echo "[rollback] 已回滚至版本 #${target}（重复执行为幂等操作）。需要回退到指定版本请用: rollback.sh <构建号>"
}

# 入口分发：
#   status       —— 只读查看，不做任何变更
#   无参/rollback —— 自动回滚到 .rollback_build 指向的上一版本
#   数字开头     —— 显式指定目标构建号（如 rollback.sh 42）
case "${1:-}" in
  status)
    echo "当前线上版本: #$(deployed_build)"
    echo "回滚点:       #$(rollback_point)"
    # 列出本机保留的所有历史版本镜像（排除 latest 移动标签），按创建时间展示
    docker images yuxm-web --format "  {{.Tag}}\t{{.CreatedSince}}" | grep -v '^  latest' || echo "  （无）"
    ;;
  ""|rollback)
    target="$(rollback_point)"
    if [ "${target}" = "无" ]; then
      echo "[rollback] 尚无回滚点（首次部署成功后自动生成）。可手动指定: rollback.sh <构建号>"
      exit 1
    fi
    retag_and_up "${target}"
    ;;
  [0-9]*)
    retag_and_up "$1"
    ;;
  *)
    echo "用法: rollback.sh [status | <构建号>]"; exit 1
    ;;
esac
