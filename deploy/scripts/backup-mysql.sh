#!/usr/bin/env bash
# MySQL 每日备份：docker compose 环境下导出 SQL 并保留最近 7 天
# crontab 示例（每日 3:30）：
#   30 3 * * * /opt/yuxm-site/deploy/scripts/backup-mysql.sh >> /var/log/yuxm-backup.log 2>&1
set -euo pipefail

COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${COMPOSE_DIR}/backups"
KEEP_DAYS=7
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="${BACKUP_DIR}/yuxm_${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

# 从 compose 环境找到 mysql 容器
MYSQL_CONTAINER="$(docker compose -f "${COMPOSE_DIR}/docker-compose.yml" ps -q mysql)"
if [ -z "${MYSQL_CONTAINER}" ]; then
  echo "[backup] 未找到 mysql 容器"
  exit 1
fi

echo "[backup] 导出 ${MYSQL_CONTAINER} ..."
docker exec "${MYSQL_CONTAINER}" sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers "$MYSQL_DATABASE"' \
  | gzip > "${FILE}"

echo "[backup] 完成：${FILE} ($(du -h "${FILE}" | cut -f1))"

# 清理过期备份
find "${BACKUP_DIR}" -name "yuxm_*.sql.gz" -mtime +${KEEP_DAYS} -delete
echo "[backup] 已清理 ${KEEP_DAYS} 天前的备份"
