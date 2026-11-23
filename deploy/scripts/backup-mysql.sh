#!/usr/bin/env bash
# =============================================================================
# MySQL 每日备份：导出全库 SQL 并 gzip 压缩，保留最近 7 天，过期自动清理
# =============================================================================
#
# crontab 示例（每日 3:30 执行，日志追加到 /var/log/yuxm-backup.log）：
#   30 3 * * * /opt/yuxm-site/deploy/scripts/backup-mysql.sh >> /var/log/yuxm-backup.log 2>&1
#   （crontab -e 添加；确保已 chmod +x 本脚本）
#
# 备份文件位置：deploy/backups/yuxm_<时间戳>.sql.gz
# 恢复方法（详见 docs/server-setup.md §7）：
#   gunzip < yuxm_20260101_033000.sql.gz | \
#     docker exec -i yuxm-site-mysql-1 mysql -uroot -p"$MYSQL_ROOT_PASSWORD" yuxm_site
#
# 设计要点：
#   - 密码不写死在命令行/脚本里，而是引用容器环境变量 $MYSQL_ROOT_PASSWORD
#     （compose 启动 mysql 时注入），避免密码出现在 ps/日志/脚本仓库中
#   - --single-transaction：InnoDB 一致性快照导出，不锁表（业务无感）
#   - docker compose ps -q mysql 按项目名找容器 ID，不写死容器名
# =============================================================================
set -euo pipefail
# -e/-u/-o pipefail：任一步失败即中止，绝不留下一个"看起来成功"的空备份

# 备份输出目录：deploy/backups/（与 compose 同级，方便一起挪动/挂载）
COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${COMPOSE_DIR}/backups"
KEEP_DAYS=7                 # 备份保留天数，过期文件在备份成功后清理
STAMP="$(date +%Y%m%d_%H%M%S)"              # 时间戳后缀，文件名精确到秒
FILE="${BACKUP_DIR}/yuxm_${STAMP}.sql.gz"   # 本次备份的最终文件路径

mkdir -p "${BACKUP_DIR}"

# 通过 compose 定位 mysql 容器 ID（-q 只输出 ID）。
# 按项目名+服务名查找，即使容器被重建过也能找到当前实例；
# 找不到说明 mysql 没起来——备份失败是正确行为，cron 日志里会看到报错
MYSQL_CONTAINER="$(docker compose -f "${COMPOSE_DIR}/docker-compose.yml" ps -q mysql)"
if [ -z "${MYSQL_CONTAINER}" ]; then
  echo "[backup] 未找到 mysql 容器"
  exit 1
fi

# 导出全库：
#   -uroot -p"$MYSQL_ROOT_PASSWORD"  root 账号，密码取容器环境变量（见上）
#   --single-transaction             一致性快照，不锁表（见上）
#   --routines --triggers            连存储过程/触发器一起导出（结构完整）
#   "$MYSQL_DATABASE"                库名取容器环境变量（默认 yuxm_site）
# docker exec 的 sh -c 包一层：让 $MYSQL_* 在容器内展开（宿主机没有这些变量）
# 管道 gzip 压缩落盘；pipefail 保证 mysqldump 失败不会产出损坏的空包
echo "[backup] 导出 ${MYSQL_CONTAINER} ..."
docker exec "${MYSQL_CONTAINER}" sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers "$MYSQL_DATABASE"' \
  | gzip > "${FILE}"

echo "[backup] 完成：${FILE} ($(du -h "${FILE}" | cut -f1))"

# 清理过期备份：find 找出修改时间超过 KEEP_DAYS 天的同名模式文件并删除
# -mtime +7 = 严格大于 7 天；只匹配 yuxm_*.sql.gz，不会误删目录里其他文件
find "${BACKUP_DIR}" -name "yuxm_*.sql.gz" -mtime +${KEEP_DAYS} -delete
echo "[backup] 已清理 ${KEEP_DAYS} 天前的备份"
