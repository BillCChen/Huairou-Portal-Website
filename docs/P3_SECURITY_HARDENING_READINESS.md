# Portal P3 Security Hardening Readiness

## 1. Scope

本 readiness 覆盖 Portal P3-A 到 P3-E3 的本地安全增强闭环：

- P3-A：密码策略与账号体验。
- P3-B：账号邮件通知。
- P3-B2：账号邮件通知真实 SMTP UAT。
- P3-C：会话过期与登录态回收。
- P3-D：IP 可溯源审计。
- P3-E1：文件下载门禁与审计。
- P3-E2：`scan_status` 状态机与 clean-only 下载。
- P3-E3：ClamAV `clamd` 本地 worker 集成。

本 readiness 不覆盖：

- Achievement 同步。
- 服务器生产 ClamAV 长期运维成熟化。
- 性能压测。
- 第三方安全扫描报告。
- K8s。
- 数据库透明加密。
- 文件内容加密。
- 对象存储。

## 2. Stage Summary

| Stage | Commit | Scope | Validation Result |
|---|---|---|---|
| P3-A | `b7f2f8a` | 账号体验与密码策略 | PASS |
| P3-B | `bd48a47` | 账号邮件通知 | PASS |
| P3-B2 | `b070f6f` | 账号邮件通知真实 SMTP UAT | PASS |
| P3-C | `8605314` | 会话过期与登录态回收 | PASS |
| P3-D | `c8bd078` | IP / User-Agent 可溯源审计 | PASS |
| P3-E1 | `0548b9c` | 文件下载门禁与下载审计 | PASS |
| P3-E2 | `18bfb738e6043e6b44d0411d1110eb28d56cc135` | 扫描状态机与 clean-only 下载 | PASS |
| P3-E3 | `c2b13f1cdbc354cceaab6735d01b2026988233e1` | ClamAV clamd worker 本地试验 | PASS |

## 3. Server Deployment Plan

受控 ECS 部署按以下边界执行：

- 先部署 `codex/portal-p3-clamav-worker` 分支，不 merge `main`。
- 部署前备份 Portal PostgreSQL。
- 部署前备份 Portal file data volume。
- 在服务器本地 `.env.production` 中启用真实 SMTP。
- SMTP password 只来自服务器本地 secret 文件，不进入 Git，不写入文档。
- 启用 ClamAV `clamd` 服务；当前部署候选使用镜像内置病毒库直接启动 `clamd`，freshclam 长期更新策略留到后续运维成熟化。
- API 容器通过 production compose 接收 `ACCESS_TOKEN_EXPIRE_MINUTES`、`FILE_SCAN_PROVIDER`、`CLAMAV_*` 和 worker 参数。
- API 镜像包含一次性 worker 脚本，可在容器内运行 `scripts/run_file_scan_worker.py`。
- 运行 one-shot scan worker 扫描 pending 文件。
- 验证 Portal web / API / admin。
- 只读验证 Achievement `https://cg.huairou.tech` 不受影响。

## 4. Risk Notes

- P3-D / P3-E2 增加数据库字段，部署前必须完成 PostgreSQL 备份。
- 当前项目仍无 Alembic 迁移体系，服务器启动兼容逻辑需要在部署 smoke 中验证。
- P3-E2 后历史文件空 `scan_status` 会视为 `pending`，未扫描前不能下载。
- ClamAV 不可用时文件会标记为 `failed`，仍不可下载。
- `manual_override` 不是 ClamAV 扫描通过，后台必须显示为手动放行且未扫描。
- 真实 SMTP 启用后，注册、审核、创建用户和改密会真实发送账号通知。
- P3-E3 的 local ClamAV compose 可用于 ECS 受控启用，但长期 freshclam、资源限制、病毒库更新失败告警和监控仍属于后续运维成熟化。

## 5. Validation

P3 本地安全增强闭环已通过以下验证：

- `./scripts/portal_min_acceptance.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_v1_acceptance.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_password_policy_backend.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_account_notifications_backend.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_session_expiry_backend.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_audit_ip_backend.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_file_download_security_backend.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_file_scan_status_backend.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 CLAMAV_HOST=127.0.0.1 CLAMAV_PORT=3310 PORTAL_CLAMAV_SMOKE_CONFIRM=true ./scripts/smoke_file_clamav_worker_backend.sh`
- `pnpm check:web`
- `pnpm build:web`
- `pnpm check:admin`
- `pnpm build:admin`
- `cd apps/api-server && python3 -m compileall app`
- `git diff --check`
- `./scripts/check_forbidden_artifacts.sh`
- `./scripts/check_secrets_basic.sh`

本 readiness 后的受控 ECS 部署还必须验证：

- PostgreSQL 备份完成。
- Portal file data volume 备份完成。
- `EMAIL_PROVIDER=smtp` 已启用但不输出 SMTP password。
- ClamAV `clamd` TCP 可用。
- one-shot scan worker 可在 API 容器中运行。
- Portal public / API / admin HTTPS smoke 通过。
- Achievement 仍可访问。

## 6. Security Boundary

- no secrets committed
- no full email committed
- no token/reset link committed
- no server `.env.production` committed
- no SMTP password committed
- ClamAV virus DB not committed
- runtime artifacts ignored
- no `main` merge in this deployment stage
- no `main` push in this deployment stage
