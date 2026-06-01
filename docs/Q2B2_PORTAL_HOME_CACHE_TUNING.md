# Q2-B2 Portal Home HTML Cache Tuning

## 1. Scope

本轮只处理 Portal 前台首页 HTML 高尾延迟，不改业务代码、不改 API、不改 Achievement、不部署应用容器。

目标是用可回退的 Nginx exact-root microcache 降低 `https://huairou.tech/` 在 50 VU 诊断压测中的高尾延迟。正式 100 VU 压测不在本轮执行。

## 2. Q2-B1 Evidence

Q2-B1 的 Nginx timing 诊断显示：

| Target | Evidence | Conclusion |
|---|---|---|
| Portal home HTML `GET /` | k6 50 VU `portal_home_html` p95 为秒级，高尾最明显 | 瓶颈在首页 HTML |
| Portal API `/api/v1/public/home` | Nginx request/upstream p95 为毫秒级 | API 不是主要瓶颈 |
| Achievement `/` 和 `/api/v1/health` | p95 低且稳定 | Achievement 不受该瓶颈影响 |
| Docker stats | 未显示 CPU/内存饱和 | 优先处理 SSR upstream 高尾，而非扩容 |

因此，本轮不触碰 API、数据库、ClamAV、邮件、登录锁定或 Achievement。

## 3. Selected Route

选择 Nginx exact-root microcache：

- `location = /` 只匹配 Portal public host 的根路径。
- `proxy_cache_valid 200 60s`，只缓存 200 响应 60 秒。
- `proxy_cache_lock` 和 `proxy_cache_use_stale updating` 用于避免 TTL 到期时多个 50 VU 请求同时回源。
- exact-root 响应启用 gzip，用于降低缓存命中后的首页 HTML 传输体积。
- 只允许 `GET/HEAD`。
- 带 query、cookie、Authorization 的请求 bypass/no-cache。
- 上游返回 `Set-Cookie` 时不写入缓存。
- 通过 `X-Cache-Status` 观测 `MISS/HIT/BYPASS`。

未选择的路线：

| Route | Reason |
|---|---|
| Nuxt/Nitro 应用级缓存 | 需要应用重建，影响面大于 Nginx exact-root 缓存 |
| 缓存 `location /` 前缀 | 可能误伤 query、注册提示、API 或其他前端路径 |
| 扩容/重建容器 | Q2-B1 未证明资源饱和，本轮不做应用容器变更 |

## 4. Cache Boundary

允许缓存：

- `https://huairou.tech/`
- `https://www.huairou.tech/`
- 无 query、无 cookie、无 Authorization 的 `GET/HEAD /`

明确不缓存：

- `/?registered=pending`
- `/api/`
- `portal-admin.huairou.tech`
- `cg.huairou.tech`
- 任意带 cookie 或 Authorization 的请求
- 任意非 200 响应
- 任意上游带 `Set-Cookie` 的响应

## 5. Server Change Plan

服务器只改 Nginx 配置，不改 Git tracked 文件，不改 `.env.production`，不重启或重建应用容器。

计划变更：

- 新增 `/etc/nginx/conf.d/huairou_portal_home_cache.conf`。
- 在 `/etc/nginx/sites-available/portal-prod.conf` 的 Portal public HTTPS server block 中新增 `location = /`。
- 创建 `/var/cache/nginx/huairou_portal_home`。
- `nginx -t` 通过后 reload Nginx。

回退方式：

```bash
sudo cp /etc/nginx/sites-available/portal-prod.conf.q2b2.bak /etc/nginx/sites-available/portal-prod.conf
sudo rm -f /etc/nginx/conf.d/huairou_portal_home_cache.conf
sudo nginx -t
sudo systemctl reload nginx
```

## 6. Validation Plan

本轮验证顺序：

1. `k6 inspect` 检查脚本语法。
2. Nginx 配置备份。
3. 写入 server-local Nginx microcache 配置。
4. `nginx -t` 和 reload。
5. `portal-home-cache-check.sh` 验证 `/` 有 `HIT`，query/API/admin/Achievement 不被缓存。
6. 运行 `PROFILE=warmup10` 低扰动 warmup。
7. 运行 `PROFILE=diagnose50`，不运行 100 VU。
8. 采集只读服务器快照、Nginx timing 摘要和 Docker stats。

通过标准：

- `portal_home_html` p95 小于 1000ms。
- Portal public/API/admin 都为 200。
- Achievement public/API 仍正常。
- 无持续 5xx 或 502。
- 未触发真实邮件、登录锁定、上传、EICAR 或 ClamAV worker。

## 7. If Target Still Fails

如果 exact-root microcache 后 `portal_home_html` p95 仍超过 1000ms：

- 保留 Nginx microcache 结果和 timing evidence。
- 不扩大缓存范围。
- 下一轮优先排查 Portal web SSR 渲染链路、Nuxt payload、Node worker 并发、upstream keepalive 和首页数据序列化。

## 8. Security Boundary

- 不读取或输出 `.env.production` 全文。
- 不输出 secret、token、password 或完整邮箱。
- 不运行真实 SMTP UAT。
- 不触发登录锁定阈值。
- 不上传文件或 EICAR。
- runtime logs 只保存在 `performance/reports/runtime/`，不提交。
