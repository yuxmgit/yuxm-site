#!/usr/bin/env bash
# 一键回滚脚本：把线上 web/api 容器回退到指定的历史构建版本
#
# 用法：
#   bash rollback.sh status            # 查看当前版本、回滚点、可用镜像
#   bash rollback.sh                   # 回滚到上一个成功部署的版本（.rollback_build）
#   bash rollback.sh 42                # 回滚到指定构建版本 yuxm-web:42 / yuxm-api:42
#
# 原理：Jenkins 每次部署成功后会把镜像打成 yuxm-web:<BUILD_NUMBER> 双标签，
# 并把"上一个成功版本"写入 deploy/.rollback_build。本脚本只需把目标版本
# 重新打 latest 标签，再 docker compose up -d --no-build，秒级完成（无重新构建）。
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${ROLLBACK_STATE_DIR:-${DEPLOY_DIR}}"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"

deployed_build()  { cat "${STATE_DIR}/.deployed_build" 2>/dev/null || echo "未记录"; }
rollback_point()  { cat "${STATE_DIR}/.rollback_build" 2>/dev/null || echo "无"; }

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
  [ "$ok" -eq 1 ] || { echo "[rollback] 回滚后健康检查失败！请执行 docker compose logs api web 排查"; exit 1; }
}

retag_and_up() {
  local target="$1"
  echo "[rollback] 将版本 #${target} 重新打 latest 标签并重启容器..."
  docker tag "yuxm-web:${target}" yuxm-web:latest
  docker tag "yuxm-api:${target}" yuxm-api:latest
  docker compose -f "${COMPOSE_FILE}" up -d --no-build web api
  echo "${target}" > "${STATE_DIR}/.deployed_build"
  health_check
  echo "[rollback] 已回滚至版本 #${target}（重复执行为幂等操作）。需要回退到指定版本请用: rollback.sh <构建号>"
}

case "${1:-}" in
  status)
    echo "当前线上版本: #$(deployed_build)"
    echo "回滚点:       #$(rollback_point)"
    echo "本地可用版本:"
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
