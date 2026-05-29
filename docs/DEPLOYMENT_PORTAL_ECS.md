# Portal ECS 部署指南

## 1. 当前服务器前置条件

- ECS Ubuntu 22.04。
- Docker / Docker Compose 已安装。
- Nginx 已安装。
- 已为 `huairou.tech`、`www.huairou.tech`、`cg.huairou.tech`、`portal-admin.huairou.tech` 配置 DNS 和 HTTPS 证书。
- Portal 仓库位于 `/opt/huairou/portal/repo`。
- 服务器使用 deploy 用户执行应用部署。
- GitHub Deploy Key 已允许服务器拉取 Portal 仓库。

## 2. 推荐部署分支

| 目标 | 分支 | 说明 |
|---|---|---|
| V1 合同闭环 | `main` | 不包含 P2-A SMTP provider 分支提交。 |
| 邮箱密码重置 SMTP UAT 支持 | `codex/portal-p2-email-reset-full-link-uat` | 包含 `EMAIL_PROVIDER=smtp` 支持和 P2-A UAT 记录。 |

生产部署前应先明确本次部署分支。不要在生产环境部署未 review 的临时分支。

## 3. 创建服务器本地 `.env.production`

服务器本地执行：

    cd /opt/huairou/portal/repo/deploy/docker
    cp .env.production.example .env.production
    chmod 600 .env.production
    vim .env.production

必须在服务器本地替换：

- `POSTGRES_PASSWORD`
- `PORTAL_SECRET_KEY`
- `PORTAL_ADMIN_PASSWORD`
- `SMTP_PASSWORD`，仅当 `EMAIL_PROVIDER=smtp` 时需要

`deploy/docker/.env.production` 不进入 Git。也可以把真实 secret 放在 `/opt/huairou/secrets`，再由部署脚本注入到 `.env.production`。

## 4. 启动 Portal

服务器本地执行：

    cd /opt/huairou/portal/repo
    git fetch origin
    git switch codex/portal-p2-email-reset-full-link-uat
    git pull --ff-only
    cd deploy/docker
    docker compose --env-file .env.production -f docker-compose.prod.yml config
    docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
    docker compose --env-file .env.production -f docker-compose.prod.yml ps

生产模板只把容器端口绑定到宿主机 `127.0.0.1`：

| 服务 | 容器端口 | 宿主机绑定 |
|---|---:|---|
| API | `8000` | `127.0.0.1:18100` |
| Web | `3000` | `127.0.0.1:13100` |
| Admin | `80` | `127.0.0.1:15174` |
| PostgreSQL | `5432` | 仅 Docker 网络内部 |

`PORTAL_WEB_PUBLIC_API_BASE` 和 `PORTAL_ADMIN_API_BASE` 必须指向 `https://huairou.tech/api/v1`，不能指向 `localhost`。浏览器中的 `localhost` 是访问者自己的电脑，不是 ECS 服务器。

## 5. Nginx 配置

服务器本地执行：

    sudo cp /opt/huairou/portal/repo/deploy/nginx/portal-prod.conf.example /etc/nginx/sites-available/portal-prod.conf
    sudo ln -sfn /etc/nginx/sites-available/portal-prod.conf /etc/nginx/sites-enabled/portal-prod.conf
    sudo nginx -t
    sudo systemctl reload nginx

如服务器已有占位页配置，确认不会抢占以下域名：

- `huairou.tech`
- `www.huairou.tech`
- `portal-admin.huairou.tech`

路由关系：

| 外部 URL | Nginx 上游 | 用途 |
|---|---|---|
| `https://huairou.tech/` | `127.0.0.1:13100` | Portal 前台 |
| `https://www.huairou.tech/` | `127.0.0.1:13100` | Portal 前台 |
| `https://huairou.tech/api/v1` | `127.0.0.1:18100` | Portal API |
| `https://portal-admin.huairou.tech/` | `127.0.0.1:15174` | Portal 后台 |
| `https://portal-admin.huairou.tech/api/v1` | `127.0.0.1:18100` | Portal API |

## 6. 验证

服务器本地执行：

    curl -I https://huairou.tech
    curl -I https://www.huairou.tech
    curl -I https://portal-admin.huairou.tech
    curl -sS https://huairou.tech/api/v1/public/home | head
    curl -sS https://huairou.tech/api/v1/public/settings | head

浏览器验证：

- `https://huairou.tech`
- `https://portal-admin.huairou.tech`
- 浏览器 Network 面板中 API 请求应指向 `https://huairou.tech/api/v1`，不能指向 `http://localhost:8100/api/v1`。

## 7. 密码重置正式域名验证

- `PUBLIC_FRONTEND_BASE_URL` 必须为 `https://huairou.tech`。
- 邮件链接路径必须保持 `/password-reset/confirm?token=...`。
- 不要把 reset token、完整 reset link、完整收件邮箱、SMTP password 写入文档、聊天或 Git。
- 真实 SMTP 只通过服务器本地 `.env.production` 启用。
- 默认 `EMAIL_PROVIDER=dev_outbox`，确认要真实发送邮件时再改为 `EMAIL_PROVIDER=smtp`。

## 8. 回滚

服务器本地执行：

    cd /opt/huairou/portal/repo/deploy/docker
    docker compose --env-file .env.production -f docker-compose.prod.yml down

如需回滚到旧占位页，禁用 `/etc/nginx/sites-enabled/portal-prod.conf`，恢复原 Nginx 站点配置后执行：

    sudo nginx -t
    sudo systemctl reload nginx

## 9. 注意事项

- 不要把容器端口绑定到 `0.0.0.0`，除非有明确网络安全设计。
- PostgreSQL 只在 Docker 网络内部使用，不对公网暴露。
- `.env.production`、SMTP password、数据库密码、JWT secret、证书私钥均保留在服务器本地。
- `postgres:16` 用于生产模板，规避服务器上 `postgres:16-alpine` 镜像拉取不稳定的问题；如后续镜像源稳定，可在服务器本地调整 `PORTAL_POSTGRES_IMAGE`。
- P2-B 只提供 Portal 生产域名部署模板，不部署 Achievement。
- P2-B 不包含 V2 业务系统、性能压测、安全扫描、备份监控和 Kubernetes hardening。
