# Portal P4 Security Alignment Readiness

## 1. Scope

本 readiness 覆盖 Portal P4 前半段双平台安全对齐：

- P4-A 跨平台安全能力对齐审计。
- P4-B1 账号认证策略对齐。
- P4-B2 登录锁定/限流对齐。
- P4-C1 账号通知对齐。
- P4-D IP 审计与日志查询对齐。

本 readiness 不覆盖：

- P4-E 文件下载、`scan_status`、ClamAV 双平台对齐。
- P4-F ClamAV worker 生产扫描策略对齐。
- P4-G 监控、备份恢复、日志保留清理。
- P4-H shared baseline/template。
- 服务器部署。
- `main` merge。

## 2. Branch and Baseline

| Item | Value |
|---|---|
| P4 branch | `codex/p4d-ip-audit-log-alignment` |
| P4 HEAD before readiness commit | `a4b73808b8170f9daa3c2bf1daf74d862e835523` |
| Previous deployed Portal P3 server branch | `codex/portal-p3-clamav-worker` |
| Previous deployed Portal P3 server HEAD | `258e572f25a9fb0bbae20cc4a3bdacd7900deb7a` |
| Planned RC tag | `v1.0-portal-p4-security-alignment-rc1` |

## 3. Stage Summary

| Stage | Commit | Scope | Code/docs | Validation | Result |
|---|---|---|---|---|---|
| P4-A | `ed0622a` | Cross-platform security parity audit | Docs only | Cross-platform code and document audit | Completed locally |
| P4-B1 | `ac557c720eded1e428cfb02055e0c1e70a543330` | Account authentication policy and UX alignment | Backend, frontend, smoke, docs | Password policy smoke and frontend/admin checks | Completed locally |
| P4-B2 | `6ed15cd7b0e39bd16bc1bc2a43d848a4b74cdf72` | Login lockout, rate limiting, notification controls | Backend, admin, frontend, smoke, docs | Login lockout smoke and existing P3 regression smokes | Completed locally |
| P4-C1 | `0c53218` | Account notification provider semantics | Docs and smoke evidence | Account notification smoke with `dev_outbox` / `disabled` | Completed locally |
| P4-D | `a4b73808b8170f9daa3c2bf1daf74d862e835523` | Trusted proxy IP audit and log query alignment | Backend helper, smoke, docs | Audit IP smoke and admin query regression | Completed locally |

## 4. Portal Changes

P4-A through P4-D changed Portal in these areas:

- Weak password and account-information similarity rejection while preserving the Portal 8-20 character and 3-of-4 complexity baseline.
- Durable login lockout for account+IP and IP-global dimensions.
- Lockout notification behavior through the existing provider boundary.
- Trusted proxy audit alignment through `TRUST_PROXY_HEADERS`.
- Protected endpoint unauthorized audit coverage without recording all public GET traffic.
- Administrator audit and login-log filtering for security investigation.

## 5. Cross-platform Alignment Status

Portal has completed the P4-B/C/D local alignment items on the P4 branch. Achievement completed the corresponding adaptations on its own P4 branch. Neither platform has pushed `main`, merged `main`, or deployed P4 to the server in this readiness stage.

## 6. Validation Evidence

The P4-R gate is expected to run the following local validation before the RC tag:

- `./scripts/portal_min_acceptance.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_v1_acceptance.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_password_policy_backend.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_account_notifications_backend.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_login_lockout_backend.sh`
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

P4-R local validation result:

| Check | Result | Notes |
|---|---|---|
| Portal minimal and V1 acceptance | PASS | `run_v1_acceptance.sh` completed and its minimal component checks passed while readiness docs were unstaged. |
| Password policy smoke | PASS | Weak password, account-similarity, and reuse boundaries remain covered. |
| Account notification smoke | PASS | `dev_outbox` and `disabled` provider boundaries passed; no real SMTP UAT was run. |
| Login lockout smoke | PASS | Account+IP, IP-global, notification, and unlock checks passed. |
| Session expiry smoke | PASS | Expired token rejection and login-state recovery smoke passed. |
| Audit IP smoke | PASS | Trusted and untrusted proxy-header checks passed. |
| File download and scan smokes | PASS | Download gate, scan-status gate, and ClamAV worker smoke passed. |
| Web/admin check and build | PASS | Existing npm/Volar/Nuxt/chunk warnings remain non-blocking. |
| Backend compileall | PASS | `apps/api-server/app` compiled successfully. |
| Diff, artifact, and secret scans | PASS | No forbidden artifact or secret-like value was detected. |

## 7. Deployment Preparation Notes

The next P4 deployment stage should not directly merge `main`. It should first prepare:

- PostgreSQL backup.
- Portal file data backup.
- Server-local `.env.production` review, including `TRUST_PROXY_HEADERS`.
- New database field, migration, and compatibility checks for the P4 branch.
- Portal and Achievement smoke plan for the deployed branches.
- Rollback plan to the current P3 deployed Portal version if the deployment fails.

## 8. Security Boundary

- No secrets are committed.
- No access tokens or reset tokens are committed.
- No full email addresses are committed.
- No server `.env` or `.env.production` files are committed.
- No runtime logs, SQLite databases, upload directories, build outputs, certificates, or ClamAV virus database files are committed.
- P4-R does not run real SMTP UAT and does not send real email.

## 9. Next Step

The intended P4-R closure is:

1. Push the P4 branch.
2. Push the RC tag.
3. Run server read-only verification.
4. Stop before deployment.
5. Start P4-Deploy only after the user explicitly authorizes it.
6. Merge `main` only after stable deployment verification.
