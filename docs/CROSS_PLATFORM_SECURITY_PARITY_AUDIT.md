# Cross-platform Security Parity Audit: P4-C1 Account Notification Alignment

## 1. Scope

本文件记录 P4-B1 至 P4-C1 双平台账号认证、登录保护与账号通知语义对齐结果。P4 阶段同时覆盖 Portal-Website 与 Achievement-Transformation，不拆成两个独立平台任务。

本阶段覆盖：

- Portal 密码策略吸收 Achievement 已验证的常见弱密码和账号信息相似拒绝能力。
- Achievement 保留现有强密码策略，并补齐当前密码复用拒绝。
- 两个平台前端均展示清晰密码规则提示，说明长度、复杂度、常见弱密码和账号信息相似限制。
- Achievement 补充登录过期提示和最小只读 profile 体验。

本阶段不覆盖：

- P4-C2 真实 SMTP UAT。
- SMS、SSO、文件安全、ClamAV、监控、服务器部署和 main merge。

## 2. Portal Changes

Portal 保留 P3-A 的基础规则：

- 密码长度 8-20 位。
- 大写字母、小写字母、数字、特殊字符 4 类中至少满足 3 类。
- password reset confirm 拒绝当前密码复用。

P4-B1 新增：

- 小型常见弱密码 denylist。
- 与 username、email local part、mobile 明显相似的密码拒绝。
- 注册、password reset confirm、管理员创建用户都传入账号上下文。
- 注册页、重置密码页、后台创建用户表单显示完整规则提示。
- smoke 覆盖 common password、username/email/mobile similarity 和当前密码复用。

## 3. Achievement Changes

Achievement 保留已有强项：

- 可配置最小长度。
- 必须包含大写字母、小写字母、数字和特殊字符。
- 常见弱密码拒绝。
- 用户名相似密码拒绝。
- 登录失败锁定/限流仍保持现状，本阶段不改。

P4-B1 新增：

- password reset confirm 在更新 hash 前拒绝与当前密码相同的新密码。
- 密码策略扩展到 email local part 和 phone 相似检查，同时不降低原有 username 相似检查。
- 注册页和重置密码页显示完整规则提示。
- 登录页识别 `reason=expired` 并显示“登录已过期，请重新登录。”。
- 新增最小只读 profile 页面，展示当前用户基础信息、角色和账号状态。

## 4. Shared Policy

| Capability | Portal | Achievement | P4-B1 result |
|---|---|---|---|
| Length and complexity | 8-20, 3 of 4 classes | minimum length, all 4 classes | keep platform-specific baseline |
| Common password rejection | added | already present | aligned |
| Account-info similarity rejection | added for username/email/mobile | extended for email/phone, kept username | aligned |
| Current password reuse rejection | already present | added for reset confirm | aligned |
| Expired-session prompt | already present | added | aligned |
| Profile/current-user UX | already present | added minimal profile | aligned |
| Login lockout/rate limiting | added durable account+IP and IP lockouts | adapted to same durable policy | aligned in P4-B2 |
| Email notification | P3-B/P3-B2 complete; P4-C1 regression only | P4-C1 added account event notifications | aligned locally |

## 5. Validation

Portal validation for this stage includes:

- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_password_policy_backend.sh`
- Existing P3 smoke and frontend/admin check/build commands from release readiness.
- Forbidden artifact and secret scans.

Achievement validation for this stage includes:

- `cd backend && uv run pytest`
- `cd frontend && pnpm typecheck`
- `cd frontend && pnpm build`
- `bash scripts/run_release_readiness.sh`
- Forbidden artifact and secret scans.

## 6. Security Boundary

- No shared/utils repository was created.
- No large password-strength dependency was introduced.
- No password history table was introduced.
- No token, reset link, SMTP password, database password, admin password, full email, or plaintext password is committed.
- No deployment, server edit, push, main merge, rebase, amend, or tag deletion was performed.

## 7. P4-B2 Login Lockout Alignment

P4-B2 extends the shared account-authentication baseline:

- Both platforms use account+IP lockout after 10 failed attempts in 24 hours.
- Both platforms use IP-global lockout after 30 failed attempts in 24 hours across account identifiers.
- Both lockout types last 24 hours by default.
- Existing accounts with email receive one account+IP lockout notification through the local provider boundary.
- Missing accounts receive no email.
- IP-global lockout does not send mass notifications.
- Administrator unlock requires a trimmed 20-1000 character reason and writes audit evidence.
- Login responses stay generic and do not reveal account existence.

Portal is implementation-heavy in P4-B2 because it did not previously have a durable login lockout model. Achievement is adaptation-heavy because it already had an account-abuse baseline but needed account+IP/IP-wide parity, notification controls, and unlock reason enforcement.

## 8. Next Recommended Step

P4-C2 should run controlled real SMTP UAT for Achievement account event notifications after the local provider-only P4-C1 result is reviewed.

## 9. P4-C1 Account Notification Alignment

P4-C1 aligns account event notification semantics outside login lockout mail.

Portal remains the regression baseline:

- Registration submitted, approval accepted, rejection with reason, administrator-created user, and password-changed notifications already exist.
- Notification sending uses the same `dev_outbox` / `disabled` / `smtp` provider boundary as password reset and lockout mail.
- Account notification failures are recorded in notification audit details and do not roll back registration, review, administrator creation, or password-change flows.
- `scripts/smoke_account_notifications_backend.sh` now covers `dev_outbox` events and verifies `disabled` provider does not block the account workflow.
- P4-C1 does not rerun the P3-B2 real SMTP UAT.

Achievement closes the local semantic gap:

- It adds plaintext account notifications for registration submitted, approval accepted, rejection, administrator-created user, and password changed.
- It reuses the existing email provider primitives instead of adding a second SMTP sender.
- Rejection reason is enforced as trimmed 20-1000 characters and included in the rejection email.
- Administrator-created user email does not include the initial password and instructs the user to use password reset.
- Password-changed notification does not include a token or reset URL.

Both platforms validate P4-C1 with `dev_outbox` / `disabled` only. Real SMTP delivery remains P4-C2.

## 10. P4-D IP Audit And Log Query Alignment

P4-D aligns application-level IP and User-Agent audit semantics for Portal and Achievement without turning either product into a traffic analytics system.

Portal remains mostly regression-oriented:

- It keeps the P3-D `LoginLog` / `AuditLog` metadata model for `ip_address`, `user_agent`, `path`, `method`, result, and failure reason.
- It adds `TRUST_PROXY_HEADERS` so trusted Nginx reverse-proxy deployments can use `X-Forwarded-For` / `X-Real-IP`, while untrusted or direct deployments fall back to `request.client.host`.
- Its audit smoke covers trusted and untrusted proxy-header behavior.
- It keeps existing administrator Audit/Login tabs for IP, account, action/module, and success/failure filtering.

Achievement closes the local query and unauthorized-audit gap:

- It keeps its existing request-security helper and extends proxy handling to include `X-Real-IP` fallback only when trusted proxy headers are enabled.
- `AuditLog` gains request path, method, result, and failure reason so protected-route unauthorized attempts can be queried consistently.
- Administrator audit filtering now supports IP, username/account, action, module/resource type, result, and creation-time range.
- The admin audit UI displays IP, shortened User-Agent, request method/path, result, and failure reason without adding a monitoring dashboard.

Shared boundaries:

- Full IP is recorded only in administrator-visible logs.
- Public GET traffic is not written to the application audit table.
- GeoIP, WAF, IP blacklist, anomaly detection, PV/UV analytics, and automatic retention cleanup remain out of scope.
- The recommended audit retention stays 180 days; cleanup automation belongs to P4-G.
