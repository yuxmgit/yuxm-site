-- 从库：首次启动自动配置并启动复制（指向 docker 网络内的 mysql-master）
CHANGE REPLICATION SOURCE TO
  SOURCE_HOST = 'mysql-master',
  SOURCE_PORT = 3306,
  SOURCE_USER = 'repl',
  SOURCE_PASSWORD = 'repl123',
  SOURCE_AUTO_POSITION = 1,
  GET_MASTER_PUBLIC_KEY = 1;
START REPLICA;
