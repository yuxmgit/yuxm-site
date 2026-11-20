# 服务器初始化与安全加固清单（腾讯云）

> 适用：CentOS 7+/Ubuntu 22.04，2C4G 起步。执行顺序自上而下。

## 1. 基础初始化

```bash
# 系统更新
sudo yum update -y          # CentOS
# sudo apt update && sudo apt upgrade -y   # Ubuntu

# 时区
sudo timedatectl set-timezone Asia/Shanghai

# 安装 Docker（腾讯云镜像源加速）
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
sudo mkdir -p /etc/docker
cat <<'EOF' | sudo tee /etc/docker/daemon.json
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
EOF
sudo systemctl restart docker

# 安装 docker compose 插件（新版 docker 自带；无则装）
sudo yum install -y docker-compose-plugin   # 或 apt install docker-compose-plugin
```

## 2. SSH 加固（最优先）

```bash
# 1) 本地生成密钥并上传（Windows: ssh-keygen → ssh-copy-id 或手动追加 authorized_keys）
# 2) 确认密钥能登录后，禁用密码登录与 root 直登
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
# 可选：改端口 sudo sed -i 's/^#\?Port 22/Port 2222/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

## 3. 防火墙（腾讯云安全组 + 系统防火墙双保险）

腾讯云控制台安全组只放行：
| 端口 | 用途 | 来源限制 |
|---|---|---|
| 2222（或 22） | SSH | 你的常用 IP /0.0.0.0 |
| 80/443 | HTTP/HTTPS | 0.0.0.0/0 |
| 8080 | Jenkins 控制台 | 你的 IP/32，绝不对公网开放 |
| 备案期间 | 临时调试端口 | 你的 IP，备案后删除 |

其余端口一律不放行；3306/6379/8000/3000 只在容器网络内通信，不对公网暴露（Jenkins 的 50000 agent 端口单机部署也无需放行）。

```bash
# 系统防火墙（Ubuntu ufw）
sudo ufw allow 2222/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw enable
```

## 4. fail2ban 防 SSH 爆破

```bash
sudo yum install -y fail2ban   # Ubuntu: apt install fail2ban
sudo tee /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 600
bantime = 3600
EOF
sudo systemctl enable --now fail2ban
```

## 5. 应用层部署

```bash
# 目录规划
sudo mkdir -p /opt/yuxm-site && cd /opt/yuxm-site
# 拉取代码（git clone 或 Jenkins 自动部署后忽略此步）

# 环境变量（复制模板并填写强随机值；注意放在 deploy/ 目录下）
cp .env.example deploy/.env
vim deploy/.env   # 必改：JWT_SECRET、MYSQL_PASSWORD、MYSQL_ROOT_PASSWORD、REDIS_PASSWORD

# 启动
cd deploy && docker compose up -d
docker compose exec api python -m app.seed   # 创建管理员

# 定时备份
chmod +x scripts/backup-mysql.sh
crontab -e   # 加入：30 3 * * * /opt/yuxm-site/deploy/scripts/backup-mysql.sh >> /var/log/yuxm-backup.log 2>&1
```

## 6. HTTPS（备案通过后）

1. 腾讯云控制台 → SSL 证书 → 申请免费证书（DV，域名 yuxm.site）
2. 下载 Nginx 版证书，上传 `deploy/nginx/certs/`（yuxm.site_bundle.pem / yuxm.site.key）
3. 按 `deploy/nginx/nginx.conf` 内注释启用 443 段
4. `docker compose restart nginx`，浏览器验证 https://yuxm.site

## 7. 上线前安全复查清单

- [ ] `.env` 中所有 `change-me` 已替换为强随机值（JWT_SECRET ≥ 32 字节随机）
- [ ] 已登录后台修改管理员默认密码（yuxiangming → 强密码）
- [ ] SSH 已禁密码登录、fail2ban 运行中
- [ ] 安全组未放行 3306/6379/8000/3000
- [ ] 备份脚本 cron 运行且已验证恢复流程（restore: gunzip → docker exec -i mysql mysql）
- [ ] `/api/docs` 在生产环境已关闭（APP_ENV=prod 时自动关闭）
