-- 主库：创建复制专用账号（仅限演示环境，密码为弱密码 root123）
CREATE USER 'repl'@'%' IDENTIFIED BY 'repl123';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;
