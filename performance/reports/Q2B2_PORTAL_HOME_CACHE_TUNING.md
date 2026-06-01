# Q2-B2 Portal Home Cache Tuning Report

## 1. Scope

本轮只处理 Portal 前台首页 HTML 高尾延迟，目标是在不改业务代码、不重建应用容器、不运行 100 VU 的前提下，用 Nginx exact-root microcache 降低 `https://huairou.tech/` 在 50 VU 诊断压测中的尾延迟。

本轮未触发真实邮件、登录锁定、文件上传、EICAR、ClamAV worker 或任何业务写操作。

## 2. Starting Evidence

Q2-B1 证据显示，50 VU 诊断下 Portal 首页 HTML 是主要高尾点：

| Target | Evidence | Conclusion |
|---|---|---|
| Portal `GET /` | k6 `portal_home_html` p95 为秒级 | 首页 HTML 是主要瓶颈 |
| Portal public API | Nginx request/upstream p95 为毫秒级 | API 不是主要瓶颈 |
| Achievement public/API | p95 低且稳定 | Achievement 不受该瓶颈影响 |
| Docker stats | CPU/内存未饱和 | 不优先做容器扩容 |

## 3. Route Comparison

| Route | Result | Reason |
|---|---|---|
| Nginx exact-root microcache | Selected | 只匹配 `location = /`，不改应用代码，回退简单，影响面最小 |
| Nuxt/Nitro 应用级缓存 | Rejected | 需要应用构建/重启，影响面大于本轮边界 |
| 缓存 `location /` 前缀 | Rejected | 容易误伤 query、注册提示、前端路由和未来动态页面 |
| 容器扩容或重建 | Rejected | Q2-B1 未证明资源饱和，本轮不部署应用容器 |

## 4. Server-side Change

服务器仅修改 Nginx 配置：

- 新增 `/etc/nginx/conf.d/huairou_portal_home_cache.conf`。
- 在 `/etc/nginx/sites-available/portal-prod.conf` 的 Portal public HTTPS server block 中新增 exact-root `location = /`。
- 创建 `/var/cache/nginx/huairou_portal_home`。
- 执行 `nginx -t` 并 reload Nginx。

Nginx 备份：

- `/opt/huairou/backups/nginx/q2b2/nginx_conf_20260601_111646.tar.gz`
- `/etc/nginx/sites-available/portal-prod.conf.q2b2.bak`

未修改 `.env.production`，未重建 Portal 或 Achievement 应用容器。

## 5. Cache Boundary

允许缓存：

- `GET/HEAD https://huairou.tech/`
- `GET/HEAD https://www.huairou.tech/`
- 无 query、无 cookie、无 Authorization、上游不带 `Set-Cookie` 的 200 响应

明确不缓存：

- `/?registered=pending`
- `/api/`
- `portal-admin.huairou.tech`
- `cg.huairou.tech`
- 带 cookie 或 Authorization 的请求
- 非 200 响应
- 上游带 `Set-Cookie` 的响应

只读 cache check 验证结果：

| Check | Result |
|---|---|
| Portal root repeated request | `X-Cache-Status` 出现 `HIT` |
| Portal root query request | `BYPASS` |
| Portal API | 无 cache header |
| Portal admin | 无 cache header |
| Achievement public | 无 cache header |

## 6. Tuning Iterations

| Iteration | Change | 50 VU Result |
|---|---|---|
| Initial exact-root cache | 30s microcache | Portal HTML p95 仍为秒级 |
| Cache lock and stale update | TTL 调整为 60s，启用 `proxy_cache_lock` 和 `proxy_cache_use_stale updating` | Portal HTML p95 仍为秒级 |
| Exact-root gzip | exact-root 响应启用 gzip，降低 HTML 传输体积 | Portal HTML p95 仍未达标 |

本轮没有扩大缓存范围，也没有改应用容器。

## 7. Final 50 VU Diagnostic

命令边界：

- `PROFILE=diagnose50`
- 未运行 `PROFILE=baseline100`
- 未设置 `RUN_FULL_LOAD=true`

最终 50 VU 结果：

| Metric | Result |
|---|---:|
| checks | 100.00% |
| http_req_failed | 0.00% |
| Portal home HTML p95 | 1.99s |
| Portal home HTML p99 | 3.73s |
| Portal HTML max | 28.24s |
| Overall HTML p95 | 1.38s |
| Overall HTTP p99 | 1.57s |
| Portal public API group p95 | 310.69ms |
| Achievement HTML p95 | 22.42ms |
| Achievement API group p95 | 73.82ms |

结论：本轮没有达到 `portal_home_html p95 < 1000ms` 的目标。

## 8. Nginx Timing Evidence

同一窗口的 Nginx performance log 显示服务器侧 `GET /` 已非常快：

| Target | Count | Status | request p95 | request p99 | request max | upstream p95 |
|---|---:|---|---:|---:|---:|---:|
| `huairou.tech GET /` | 4954 | 200 | 0.0ms | 0.0ms | 1.555s | 104.0ms |
| `huairou.tech GET /api/v1/public/home` | 4970 | 200 | 24.0ms | 37.0ms | 145.0ms | 24.0ms |
| `portal-admin.huairou.tech GET /` | 1219 | 200 | 1.0ms | 1.0ms | 2.0ms | 4.0ms |
| `cg.huairou.tech GET /` | 4850 | 200 | 1.0ms | 1.0ms | 3.0ms | 4.0ms |
| `cg.huairou.tech GET /api/v1/health` | 4850 | 200 | 2.0ms | 3.0ms | 23.0ms | 4.0ms |

这说明 exact-root cache 已经把服务端 request/upstream 高尾压低；k6 仍看到秒级 HTML tail，下一轮需要优先排查客户端链路、TLS/连接复用、响应体传输、k6 timing 采样、公网出口带宽或首页 HTML/payload 体积，而不是继续扩大 Nginx 缓存边界。

## 9. Runtime and Health

只读服务器快照显示：

- Portal API/Web/Admin 容器保持 Up。
- Achievement Backend/Frontend 容器保持 healthy。
- Portal ClamAV 容器保持 healthy。
- Nginx `nginx -t` 通过。
- Portal public/API/admin 仍为 200。
- Achievement public/API 仍为 200。
- Nginx access summary 没有 5xx 样本。

## 10. Known Warnings

- 本地 `curl` 在部分 HTTPS 请求上出现 LibreSSL `SSL_ERROR_SYSCALL`，cache check 脚本已使用 Python urllib fallback 完成验证。
- k6 50 VU 的 Portal HTML threshold 仍失败；这不是业务可用性失败，检查和 HTTP 错误率均为 0。
- Nginx `X-Cache-Status: STALE` 在后置只读快照中出现，符合 `proxy_cache_use_stale updating` 的设计，但也提示后续若继续保留该配置，应观察真实用户首页更新延迟。

## 11. Security Boundary

- 未读取或输出 `.env.production`。
- 未输出 secret、token、password 或完整邮箱。
- 未运行真实 SMTP UAT。
- 未触发登录锁定阈值。
- 未上传文件或 EICAR。
- 未运行 ClamAV worker。
- runtime 日志保存在 `performance/reports/runtime/`，不提交。

## 12. Next Recommended Work

Q2-B2 的 low-risk Nginx exact-root cache 路线已经验证到边界：服务器侧已经足够快，但 k6 端 Portal HTML tail 仍不达标。

下一轮建议不要扩大缓存范围，优先做 Q2-B3：

- 在 k6 中拆分 `blocked/connecting/tls_waiting/sending/waiting/receiving`。
- 验证 k6 请求是否实际带 `Accept-Encoding: gzip`，以及收到的 body/transfer size。
- 对比同机、不同网络出口和服务器本机 curl/hey 的 `GET /` latency。
- 评估首页 HTML 和 Nuxt payload 体积是否需要应用层瘦身。
- 如果确认公网传输是主因，再讨论静态化、CDN 或更细的 HTML/payload 策略。
