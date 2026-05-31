# Q0 Dual-platform Performance Test Plan

## 1. Scope

Q0 为 Portal 与 Achievement 准备 100 并发虚拟用户性能测试工具包，但不执行正式 100 并发测试。

本阶段覆盖：

- k6 双平台只读脚本。
- 服务器只读资源采集脚本。
- Nginx 日志摘要脚本。
- Docker stats 快照脚本。
- 性能测试报告模板。
- 小流量 preflight 运行说明。

本阶段不覆盖：

- 正式 100 并发测试。
- 长时间压测。
- 注册、审核、创建用户、密码修改。
- 真实邮件。
- 连续错误登录或 lockout 阈值触发。
- 上传、EICAR、ClamAV worker。
- 业务代码修改。
- 服务器部署或配置修改。

## 2. Definition of 100 Concurrent Users

100 并发表示 100 个 concurrent virtual users 持续执行代表性低扰动业务流程。

它不是：

- 100 QPS。
- 100 个真实浏览器。
- 批量写入、注册或上传。

k6 的虚拟用户会在多个只读页面和 API 之间循环，并加入 1-3 秒 think time，以接近普通浏览访问而不是请求洪峰。

## 3. Load Generator and Targets

压测机：

- Local Mac。

被测目标：

- Portal public: `https://huairou.tech`
- Portal admin shell: `https://portal-admin.huairou.tech`
- Achievement public: `https://cg.huairou.tech`

Q0 本地 curl 受本机代理或 TLS 栈影响时，允许用 Python/OpenSSL 或服务器侧只读 smoke 辅助判断域名可达性；正式 k6 运行仍以 k6 summary 为准。

## 4. Low-disruption Scenario Set

Portal:

- `GET /`
- `GET /api/v1/public/home`
- `GET /api/v1/public/news?page=1&page_size=5`
- `GET /api/v1/public/cases?page=1&page_size=5`
- `GET /api/v1/public/settings`
- `GET https://portal-admin.huairou.tech/`

Achievement:

- `GET /`
- `GET /api/v1/health`
- `GET /api/v1/public/achievements?page=1&page_size=10`
- `GET /api/v1/public/talents?page=1&page_size=10`
- `GET /api/v1/public/facilities?page=1&page_size=10`

Excluded endpoints:

- `POST /api/v1/auth/register`
- password reset request/confirm
- login failure loops
- admin review/create/update APIs
- upload/download stress
- file scan worker
- any endpoint that sends real email or mutates production data

## 5. Authenticated Scenarios

Q0 does not require authenticated load.

If Q1 needs authenticated read-only coverage, credentials or tokens must be provided at runtime through environment variables or a temporary low-privilege test account. Tokens and passwords must never be committed, written into reports, or printed in logs.

## 6. Test Data Guidance

Q0 仅使用当前线上公开只读数据，不创建测试用户、不注册账号、不触发审核、不上传文件。

Q1 如需扩展到认证只读场景，应先准备：

- 明确标记的低权限测试账号。
- 不会触发邮件、短信、审核、锁定阈值或文件扫描的访问路径。
- 与生产真实用户隔离的测试记录清单。
- 测试后可核对的只读审计范围。

Q1 不应使用管理员账号承载 100 VU 负载。

## 7. k6 Scripts

Smoke preflight:

```bash
PORTAL_BASE_URL=https://huairou.tech \
PORTAL_ADMIN_BASE_URL=https://portal-admin.huairou.tech \
ACHIEVEMENT_BASE_URL=https://cg.huairou.tech \
k6 run performance/k6/dual-platform-smoke.js
```

Safe profile for the 100 VU script:

```bash
PROFILE=smoke \
PORTAL_BASE_URL=https://huairou.tech \
PORTAL_ADMIN_BASE_URL=https://portal-admin.huairou.tech \
ACHIEVEMENT_BASE_URL=https://cg.huairou.tech \
k6 run performance/k6/dual-platform-100vu.js
```

Q1 formal 100 VU command, not allowed in Q0:

```bash
PROFILE=baseline100 \
RUN_FULL_LOAD=true \
PORTAL_BASE_URL=https://huairou.tech \
PORTAL_ADMIN_BASE_URL=https://portal-admin.huairou.tech \
ACHIEVEMENT_BASE_URL=https://cg.huairou.tech \
k6 run performance/k6/dual-platform-100vu.js
```

The baseline profile is guarded. `PROFILE=baseline100` fails unless `RUN_FULL_LOAD=true` is explicitly set.

## 8. Server Read-only Snapshot

Run before and after Q1 formal load:

```bash
SERVER_HOST=47.94.240.154 \
SSH_KEY=/path/to/ssh-key \
bash performance/scripts/server-readonly-snapshot.sh
```

Runtime output is written to:

```text
performance/reports/runtime/
```

The runtime directory is ignored by Git.

## 9. Log Summary

Nginx summary over SSH:

```bash
SERVER_HOST=47.94.240.154 \
SSH_KEY=/path/to/ssh-key \
bash performance/scripts/nginx-log-summary.sh
```

Docker stats snapshot:

```bash
SERVER_HOST=47.94.240.154 \
SSH_KEY=/path/to/ssh-key \
bash performance/scripts/docker-stats-snapshot.sh
```

These scripts are read-only and redact token/password-like query parameters.

## 10. Acceptance Thresholds

Q1 recommended thresholds:

- 5xx = 0.
- total error rate < 0.5%.
- core API p95 < 800ms.
- page/html p95 < 1000ms.
- p99 < 1500ms.
- CPU peak < 70%.
- memory no sustained growth.
- no DB connection exhaustion.

Q0 smoke threshold is intentionally stricter for correctness checks:

- `http_req_failed < 1%`
- `http_req_duration p95 < 1000ms`
- `checks rate > 99%`

## 11. Q0 Preflight Status

Current local k6 availability:

- `k6` was not found on the local Mac during Q0 preparation.
- Q0 does not automatically install k6.

Install command for the next run:

```bash
brew install k6
```

After installation, run the smoke command in section 7. Do not run the baseline100 profile until Q1 is explicitly authorized.

Current endpoint audit:

- Portal public home, public APIs, and admin shell returned HTTP 200 in the Q0 endpoint audit.
- Achievement public home and health/public APIs returned HTTP 200 in the Q0 endpoint audit.
- Server read-only snapshot completed with both platform containers healthy/up and Nginx configuration valid.
- The k6 smoke run is pending until k6 is installed locally.

## 12. Report Template

Use:

```text
performance/reports/templates/Q_PERFORMANCE_REPORT_TEMPLATE.md
```

The report must include environment, scenario mix, k6 summary, server resource snapshots, Nginx/API log summary, exclusions, and known limitations.
