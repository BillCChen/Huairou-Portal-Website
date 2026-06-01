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

## 4. Docker 官方镜像拉取问题与镜像源切换

在阿里云 ECS 上，`docker.io/library` 官方镜像可能因 mirror 或 registry 解析问题出现 `not found`，例如：

- `postgres:16`
- `python:3.13-slim`
- `node:22-alpine`
- `nginx:1.27-alpine`

生产模板支持通过服务器本地 `.env.production` 设置：

- `PORTAL_POSTGRES_IMAGE`
- `PORTAL_PYTHON_BASE_IMAGE`
- `PORTAL_NODE_BASE_IMAGE`
- `PORTAL_NGINX_BASE_IMAGE`

当前 ECS 验证可达的 Docker Official Images ECR Public 路径：

    PORTAL_POSTGRES_IMAGE=public.ecr.aws/docker/library/postgres:16
    PORTAL_PYTHON_BASE_IMAGE=public.ecr.aws/docker/library/python:3.13-slim
    PORTAL_NODE_BASE_IMAGE=public.ecr.aws/docker/library/node:22-alpine
    PORTAL_NGINX_BASE_IMAGE=public.ecr.aws/docker/library/nginx:1.27-alpine

不要在服务器上长期使用 `docker tag` 手工伪装镜像名。不要手工修改 `docker-compose.prod.yml`。镜像源兼容应通过 `.env.production` 覆盖变量完成。

## 5. 启动 Portal

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

## 6. Nginx 配置

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

Portal 前台首页可启用 Nginx exact-root microcache：

- 只缓存 `https://huairou.tech/` 和 `https://www.huairou.tech/` 的无 query、无 cookie、无 Authorization 的 `GET/HEAD /`。
- TTL 为 60 秒，缓存目录为 `/var/cache/nginx/huairou_portal_home`，zone 为 `huairou_portal_home_cache`。
- 开启 `proxy_cache_lock` 和 `proxy_cache_use_stale updating`，避免 TTL 到期时 50 VU 同时回源压垮 Portal web/SSR。
- exact-root 响应开启 gzip，减少缓存命中后首页 HTML 的传输体积；该设置不应用于 API、后台或 Achievement。
- `/?registered=pending` 等带 query 的注册提示页面不缓存。
- `/api/`、`portal-admin.huairou.tech`、`cg.huairou.tech` 不进入该 cache zone。
- 响应头 `X-Cache-Status` 用于只读验证 `MISS/HIT/BYPASS`。

如需临时回退首页 microcache：

    sudo cp /etc/nginx/sites-available/portal-prod.conf.q2b2.bak /etc/nginx/sites-available/portal-prod.conf
    sudo rm -f /etc/nginx/conf.d/huairou_portal_home_cache.conf
    sudo nginx -t
    sudo systemctl reload nginx

Portal admin 容器内部只提供 HTTP 静态站点：

- admin 容器监听 `80`，由 Compose 绑定到宿主机 `127.0.0.1:15174`。
- HTTPS 终止由宿主机 Nginx 的 `portal-admin.huairou.tech` server block 处理。
- 不要在 admin 容器内配置 `/etc/ssl/certs/portal.crt` 或 `/etc/ssl/private/portal.key`。
- 如果 admin 容器日志出现 `portal.crt` missing，说明服务器仍在使用旧的容器内 SSL 配置，应更新到包含 HTTP-only admin Nginx 模板的版本后重建 admin 服务。

## 7. 验证

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

## 8. 密码重置正式域名验证

- `PUBLIC_FRONTEND_BASE_URL` 必须为 `https://huairou.tech`。
- 邮件链接路径必须保持 `/password-reset/confirm?token=...`。
- 不要把 reset token、完整 reset link、完整收件邮箱、SMTP password 写入文档、聊天或 Git。
- 真实 SMTP 只通过服务器本地 `.env.production` 启用。
- 默认 `EMAIL_PROVIDER=dev_outbox`，确认要真实发送邮件时再改为 `EMAIL_PROVIDER=smtp`。

## 9. 回滚

服务器本地执行：

    cd /opt/huairou/portal/repo/deploy/docker
    docker compose --env-file .env.production -f docker-compose.prod.yml down

如需回滚到旧占位页，禁用 `/etc/nginx/sites-enabled/portal-prod.conf`，恢复原 Nginx 站点配置后执行：

    sudo nginx -t
    sudo systemctl reload nginx

## 10. 注意事项

- 不要把容器端口绑定到 `0.0.0.0`，除非有明确网络安全设计。
- PostgreSQL 只在 Docker 网络内部使用，不对公网暴露。
- `.env.production`、SMTP password、数据库密码、JWT secret、证书私钥均保留在服务器本地。
- 默认 Docker Hub 官方镜像仍可用于网络正常环境；当前阿里云 ECS 可通过 `.env.production` 切换到 ECR Public 官方镜像路径。
- P2-B 只提供 Portal 生产域名部署模板，不部署 Achievement。
- P2-B 不包含 V2 业务系统、性能压测、安全扫描、备份监控和 Kubernetes hardening。
