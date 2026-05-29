# Portal P3 Account Experience Readiness

## 1. Scope

本 readiness 覆盖 Portal P3 账号体验与通知本地收束：

- P3-A 账号体验与密码策略。
- P3-B 账号邮件通知。
- P3-B2 账号邮件通知真实 SMTP UAT。

本 readiness 不覆盖：

- P3-C 3 小时静默过期的服务器部署与生产验证。
- P3-D IP 审计；该能力已在 `docs/P3_AUDIT_IP_TRACEABILITY.md` 单独记录。
- 文件加密。
- 病毒扫描。
- 监控后端。
- 服务器部署。

## 2. Stage Summary

| Stage | Commit | Scope | Result |
|---|---|---|---|
| P3-A | b7f2f8a | account UX + password policy | PASS |
| P3-B | bd48a47 | account email notifications | PASS |
| P3-B2 | b070f6f | real SMTP UAT docs/scripts | PASS |

## 3. P3-A Evidence

- 密码长度为 8-20 位。
- 密码必须满足大写字母、小写字母、数字、特殊字符 4 类中至少 3 类。
- 邮件密码重置确认不得将新密码设置为当前密码。
- 注册成功后返回门户首页，并显示“注册已提交，等待审核，注意查收邮件”。
- Header 已登录态显示用户名、角色、个人中心和退出。
- `/profile` 是最小只读个人中心，展示用户名、真实姓名、邮箱、手机号、单位、角色和账号状态。
- `smoke_password_policy_backend.sh` 已作为本地密码策略 smoke。

## 4. P3-B Evidence

- 注册提交邮件通知已实现。
- 审核通过邮件通知已实现。
- 审核拒绝邮件通知已实现。
- 管理员创建机构用户邮件已实现，邮件不包含初始密码。
- 密码修改成功通知已实现，邮件不包含 token 或 reset link。
- 审核拒绝 reason 去除首尾空白后必须为 20-1000 字符。
- `smoke_account_notifications_backend.sh` 已作为本地账号通知 smoke。
- P3-B 本地验证使用 `dev_outbox` / `disabled` provider，不发送真实邮件。

## 5. P3-B2 Evidence

- 真实 SMTP UAT 已完成。
- SMTP: `smtpdm.aliyun.com:465` implicit SSL/TLS。
- 真实邮件总数：8 封。
- 收件邮箱仅记录为 `20***@stu.pku.edu.cn`。
- 注册提交、审核通过、审核拒绝、管理员创建机构用户、密码修改成功均已收到。
- 审核拒绝邮件包含 reason。
- 管理员创建用户邮件不含初始密码。
- 密码修改成功邮件不含 token / reset link。
- 无 SMTP password、token、reset link、完整邮箱、密码提交。

## 6. Validation

P3-B3 本地收束运行以下非真实 SMTP 验证：

- `./scripts/portal_min_acceptance.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_v1_acceptance.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_password_policy_backend.sh`
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_account_notifications_backend.sh`
- `pnpm check:web`
- `pnpm build:web`
- `pnpm check:admin`
- `pnpm build:admin`
- `cd apps/api-server && python3 -m compileall app`
- `git diff --check`
- `./scripts/check_forbidden_artifacts.sh`
- `./scripts/check_secrets_basic.sh`

本轮不重发真实 SMTP 邮件。P3-B2 的真实 SMTP UAT 结果作为最终真实投递证据引用。

## 7. Security Boundary

- no push
- no server deploy
- no SMS change
- no SMTP secret committed
- no full email committed
- no token/reset link committed
- no password committed

## 8. Next Recommended Stage

建议下一阶段：

- P3-C：本地会话过期 / 登录态回收已在 `docs/P3_SESSION_EXPIRY.md` 记录；后续仍需用户授权后再做 push/deployment。
- P3-D：本地 IP 可溯源审计已在 `docs/P3_AUDIT_IP_TRACEABILITY.md` 记录；后续仍需用户授权后再做 push/deployment。
- P3-A/B/B2 merge-readiness push/deployment，需用户另行授权。
