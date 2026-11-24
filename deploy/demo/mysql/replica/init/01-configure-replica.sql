-- 从库：首次启动自动配置并启动复制（指向 docker 网络内的 mysql-master）
CHANGE REPLICATION SOURCE TO
  SOURCE_HOST = 'mysql-master',
  SOURCE_PORT = 3306,
  SOURCE_USER = 'repl',
  SOURCE_PASSWORD = 'repl123',
  SOURCE_AUTO_POSITION = 1,
  GET_MASTER_PUBLIC_KEY = 1;
START REPLICA;

-- 只读保护：初始化完成后再开启（cnf 里配置会导致 Docker 首次初始化失败）
-- 注意 SET GLOBAL 不持久化，容器重启后需重跑本脚本或手动执行
SET GLOBAL read_only = 1;
SET GLOBAL super_read_only = 1;
