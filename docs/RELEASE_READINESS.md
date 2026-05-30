# Portal Website Release Readiness

## 1. 当前状态

当前尚未达到生产交付标准。本文件记录后续 release readiness 需要补齐的检查项。

## 2. 必须通过的基础检查

| 检查项 | 当前状态 | 目标 |
|---|---|---|
| Git 工作区干净 | 否，存在未跟踪 runtime/output | P0 收敛 |
| 前台 typecheck | 未验证 | 必须通过 |
| 前台 build | 未验证 | 必须通过 |
| 后台 typecheck | 未验证 | 必须通过 |
| 后台 build | 未验证 | 必须通过 |
| 后端测试 | 缺失 | 新增并通过 |
| API smoke | 缺失 | 新增并通过 |
| Docker compose | 未完整验收 | 可启动并通过 healthcheck |
| Secret scan | 缺失 | 新增并通过 |
| Forbidden artifact scan | 缺失 | 新增并通过 |
| 安全扫描 | 缺失 | 新增报告 |
| 性能压测 | 缺失 | 证明核心业务 100 并发 |
| HTTPS | 未验收 | 提供域名/证书方案 |
| K8s | 缺失 | 若合同坚持，补 manifests 或说明边界 |

## 3. Forbidden Artifacts

不得提交：

- `.runtime-logs/`
- `outputs/`
- `.env`
- 真实密钥
- 本地数据库
- 上传文件运行目录
- 构建产物
- 测试报告原始大文件，除非位于约定 reports 目录并确认可提交

## 4. 当前已知风险

- HEAD 快照提交使用本机自动 committer 身份，需要合并前决定是否修正。
- `apps/api-server/app/main.py` 存在临时 SQLite schema compatibility 逻辑，后续应以正式迁移替代。
- `SiteHeader.vue` 中的成果、人才、设施入口已指向正式成果转化平台域名 `https://cg.huairou.tech`，不再使用访问者本机 `127.0.0.1` 地址。
- P1-A 已确认手机号验证码登录排除在 Portal V1 acceptance 外；现有 SMS UI/API 只能视为 current-code/test-path。
- P1-B 已实现邮箱密码重置后端基础：email/username request、hash-only token、expiry、consumed/reuse rejection、dev outbox/disabled provider boundary 和后端 smoke。
- P1-C 已实现邮箱密码重置前端基础：`/forgot-password`、`/password-reset/confirm?token=...`、登录页找回密码入口和前端 API client。真实 SMTP UAT 和 full-link UAT 仍未执行。
- P1-D 已实现用户生命周期闭环基础：审核通过/驳回、禁用/启用、机构用户创建、角色分配、后台 UI 和 user lifecycle smoke。
- P1-E 已实现 V1 内容 CMS 验收闭环：首页聚合、新闻、案例、关于我们、领导团队、Banner、分类/标签、站点设置和 V1 content smoke。
- P1-F 已新增 V1 总验收入口、auth/permission smoke、V1 验收清单和验收报告。
- P1-G 已完成合并就绪审计：V1 总验收、route map 稳定性、forbidden artifact scan、basic secret scan、merge-tree 冲突检查和 18200 端口残留检查均通过；本阶段不 merge、不 push。
- P2-A 已完成真实 SMTP password reset full-link UAT：临时 HTTPS tunnel、真实邮件送达、reset 页面打开、改密成功、旧密码拒绝、新密码登录成功和 token 复用拒绝均已脱敏记录。生产域名、正式 SMTP 运维手册、性能压测、安全扫描和 K8s 仍是后续事项。
- P2-B 已新增生产域名部署配置模板：`deploy/docker/docker-compose.prod.yml`、`deploy/docker/.env.production.example`、`deploy/nginx/portal-prod.conf.example` 和 `docs/DEPLOYMENT_PORTAL_ECS.md`。本阶段只固化 Portal 部署模板，不执行服务器部署、不修改业务逻辑、不处理 Achievement 部署。
- P2-B2 已新增部署镜像源兼容：生产 Dockerfile 基础镜像可通过 build args 配置，`docker-compose.prod.yml` 可从服务器本地 `.env.production` 传入 ECR Public Docker Official Images 路径。本阶段不修改业务逻辑，服务器仍需 pull 后重新运行 compose。
- P2-B3 已修正 admin 容器 runtime Nginx SSL 边界：admin 容器内部只提供 HTTP 静态站点，HTTPS 终止继续由宿主机 Nginx 负责。本阶段不修改业务逻辑。
- P3-A 已新增账号体验与密码策略本地开发：注册、邮件密码重置确认、管理员创建用户统一使用 8–20 位且 4 类中至少 3 类的密码策略；密码重置确认拒绝当前相同密码；前台注册成功后返回首页并显示“注册已提交，等待审核，注意查收邮件”；Header 展示登录态；`/profile` 提供最小只读个人中心。P3-A 不发送真实邮件、不修改 SMS、不修改服务器部署、不进入 V2。
- P3-B2 已完成账号邮件通知本地真实 SMTP UAT：注册提交、审核通过、审核拒绝、管理员创建机构用户和密码修改成功五类通知均已发送并由用户确认收到；审核拒绝 reason 已确认送达；未提交 SMTP password、完整邮箱、token、reset link 或密码。本阶段不 push、不部署服务器、不修改 SMS/SSO/部署配置。
- P3-B3 记录 P3-A/P3-B/P3-B2 本地 readiness 收束：新增 `docs/P3_ACCOUNT_EXPERIENCE_READINESS.md`，本轮只做文档与本地非真实 SMTP 验证，不重发真实邮件、不 push、不部署服务器。下一步建议进入 P3-C 3 小时静默过期，或在用户另行授权后做 P3 merge-readiness / push / deployment。
- P3-C 已新增会话过期与登录态回收本地开发：`ACCESS_TOKEN_EXPIRE_MINUTES` 默认 180 分钟，后端 JWT `exp` 过期返回 401；Portal 前台和 Admin Console 遇到认证 401 会清理本地登录态并跳转登录页；新增 1 分钟过期 smoke。本阶段不引入 refresh token、token blacklist 或多端互踢，不修改 SMS/SSO，不发送邮件，不部署服务器。
- P3-D 已新增 IP 访问日志与账号可溯源审计本地开发：关键账号、安全和后台管理事件记录 IP、User-Agent、path、method 和结果；后台审计页提供最小 IP/账号/action 筛选；新增 `scripts/smoke_audit_ip_backend.sh` 使用 `203.0.113.10` 验证可溯源链路。本阶段不做 PV/UV、GeoIP、IP 封禁、监控 dashboard，不修改 SMS/SSO，不发送邮件，不部署服务器。
- P3-E1 已新增文件下载门禁与审计本地开发：public 文件允许匿名通过后端下载 endpoint 下载并审计；protected 文件要求 active 登录用户；下载成功、拒绝、未找到和路径异常均记录 IP/User-Agent；新增 `scripts/smoke_file_download_security_backend.sh` 使用 `203.0.113.20` 验证门禁和审计。本阶段不做病毒扫描、`scan_status`、对象存储、文件内容加密、服务器部署或 push。
- P3-E2 已新增文件扫描状态机与 fail-closed 下载策略本地开发：`FileRecord` 记录 `scan_status`，新上传和历史空状态默认 `pending`；public/protected 下载都要求 `clean`；`pending`、`infected`、`failed`、`skipped` 均拒绝并审计；新增 mock scanner 和 `scripts/smoke_file_scan_status_backend.sh` 使用 `203.0.113.30` 验证状态门禁。本阶段不接真实 ClamAV，不做扫描 worker、对象存储、文件内容加密、服务器部署或 push。
- P3-E3 已新增本地 ClamAV `clamd` worker 试验：`file_scanning.py` 增加 TCP `clamd` provider；`scripts/run_file_scan_worker.py` 提供一次性 pending 文件扫描；admin 文件库支持重新扫描和 `super_admin` 手动放行；`scripts/smoke_file_clamav_worker_backend.sh` 使用 EICAR 验证 clean / infected / failed / manual_override。本阶段不部署服务器、不 push、不做常驻 worker 或队列。
- P3 security hardening readiness 已准备受控 ECS 部署：新增 `docs/P3_SECURITY_HARDENING_READINESS.md`，并补齐 production compose 的 P3-C/P3-E3 运行时配置透传和 API 镜像内 one-shot worker 入口。本阶段仍不 merge main、不 push main、不声称服务器已部署。
- 当前无 Alembic 迁移体系。
- 当前无真实性能、安全、功能测试报告。

## 5. P0-2 Minimal Acceptance Scripts

P0-2 新增以下最小验收脚本：

| 脚本 | 用途 |
|---|---|
| `scripts/check_forbidden_artifacts.sh` | 检查已跟踪文件中是否误提交 runtime logs、outputs、真实 env、本地数据库、构建产物等禁止产物 |
| `scripts/check_secrets_basic.sh` | 对已跟踪文本做基础 secret-like pattern 扫描；不能替代 gitleaks/trufflehog |
| `scripts/extract_api_routes.py` | 从 FastAPI 路由源码提取 API route map，并生成 `docs/API_ROUTE_MAP.generated.md` |
| `scripts/portal_min_acceptance.sh` | 最小验收入口，串联 git clean 检查、forbidden artifact、basic secret scan 和 API route map extraction |
| `scripts/run_v1_acceptance.sh` | V1 总验收入口，编排前台/后台静态检查、后端 compileall、公共 API smoke、密码重置 smoke、用户生命周期 smoke、权限 smoke、内容 smoke 和仓库卫生检查 |
| `scripts/smoke_auth_permission_backend.sh` | 本地隔离运行的认证/权限边界 smoke，验证 anonymous、ordinary user、admin、super-admin 的 admin API 访问边界 |

运行方式：

```bash
./scripts/check_forbidden_artifacts.sh
./scripts/check_secrets_basic.sh
python3 scripts/extract_api_routes.py
./scripts/portal_min_acceptance.sh
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_v1_acceptance.sh
```

当前边界：

- P0-2 不验证业务正确性。
- P0-2 不替代后端 pytest、前端 build、E2E、安全扫描、性能压测。
- P0-2 只建立最低限度的仓库卫生和 API 路由可见性检查。

P1-F 的 `scripts/run_v1_acceptance.sh` 是 V1 合同验收汇总入口，但仍不替代真实性能压测、外部安全扫描、真实 SMTP full-link UAT、Kubernetes 验收或 V2 业务验收。

## 5a. P1-G Merge Readiness Result

P1-G final readiness status:

| Check | Status | Notes |
|---|---|---|
| P1 branch scope audit | PASS | P1 branch contains P1-A through P1-F commits and remains scoped to V1 contract closure. |
| V1 acceptance runner | PASS | `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_v1_acceptance.sh`. |
| Route map stability | PASS | Generated API route map remained stable at 68 routes. |
| Forbidden artifact scan | PASS | No tracked runtime artifacts or build outputs were detected. |
| Basic secret scan | PASS | No tracked secret-like value was reported. |
| Merge-tree check | PASS | `main` is an ancestor of the P1 branch and no conflict marker was reported. |
| Port cleanup | PASS | No listener remained on port `18200`. |

P1-G readiness does not mean production release readiness. Real SMTP full-link UAT, production performance testing, external security scanning, Kubernetes validation, public file delivery hardening, formal migrations, and V2 business systems remain separate later tracks.

## 5b. P2-A Password Reset Full-Link UAT Result

P2-A validates the real email password reset path in a controlled temporary environment. It does not change SMS scope, password reset token semantics, user lifecycle behavior, V1 content CMS behavior, or V2 business scope.

| Check | Status | Notes |
|---|---|---|
| SMTP provider boundary | PASS | `EMAIL_PROVIDER=smtp` supports runtime-injected SMTP credentials; default remains `dev_outbox`. |
| SMTP config smoke | PASS | `scripts/smoke_password_reset_smtp_config.sh` verifies disabled/dev-safe behavior and fail-closed SMTP misconfiguration. |
| Full-link UAT | PASS | One real reset email was delivered to the controlled masked recipient. |
| Reset frontend route | PASS | `/password-reset/confirm?token=...` opened through the temporary HTTPS tunnel. |
| Password rotation | PASS | Old password rejected and new password accepted by the login API. |
| Token reuse | PASS | Same-link reuse was rejected. |
| Secret handling | PASS | No SMTP password, reset token, full reset link, full recipient email, login token, or password was committed. |

P2-A still does not mean production release readiness. Production domain HTTPS, formal SMTP operations, performance testing, external security scanning, Kubernetes validation, public file delivery hardening, formal migrations, and V2 business systems remain separate later tracks.

## 5c. P2-B Production-Domain Deployment Template Result

P2-B adds versioned deployment templates for the ECS / Nginx / Docker environment. It does not deploy to the server, does not change auth, password reset, user lifecycle, V1 content CMS, SMS, or V2 business behavior.

| Check | Status | Notes |
|---|---|---|
| Production Docker Compose template | ADDED | `deploy/docker/docker-compose.prod.yml` binds API, web, and admin only to `127.0.0.1` host ports. |
| Production env example | ADDED | `deploy/docker/.env.production.example` contains placeholders only; real `.env.production` remains server-local. |
| Nginx reverse proxy example | ADDED | `deploy/nginx/portal-prod.conf.example` routes `huairou.tech`, `www.huairou.tech`, `/api/`, and `portal-admin.huairou.tech`. |
| Deployment runbook | ADDED | `docs/DEPLOYMENT_PORTAL_ECS.md` documents GitHub pull, local secrets, compose startup, Nginx enablement, verification, and rollback. |
| Browser API base | TEMPLATE FIXED | Production web/admin API base points to `https://huairou.tech/api/v1`, not visitor-side `localhost`. |

P2-B still does not mean production release readiness. The actual ECS deployment, production-domain smoke, backup policy, monitoring, performance testing, external security scanning, formal migrations, Kubernetes validation, Achievement deployment, and V2 systems remain separate later tracks.

## 5d. P2-B2 Deployment Image Source Compatibility

P2-B2 records deployment-only compatibility for ECS environments where Docker Hub official image resolution is unavailable through the configured registry mirror. It does not change auth, password reset, user lifecycle, V1 content CMS, SMS, or V2 business behavior.

| Check | Status | Notes |
|---|---|---|
| Dockerfile base image args | ADDED | API, web, and admin Dockerfiles keep Docker Hub defaults and allow base image override through build args. |
| Production compose build args | ADDED | `docker-compose.prod.yml` passes Python, Node, and Nginx base image variables from `.env.production`. |
| Production env example | UPDATED | `deploy/docker/.env.production.example` uses ECR Public Docker Official Images paths that were reachable on the current Aliyun ECS test server. |
| Deployment runbook | UPDATED | `docs/DEPLOYMENT_PORTAL_ECS.md` documents the Docker Hub mirror failure mode and the ECR Public override path. |

P2-B2 still does not mean production release readiness. The server must pull the updated branch and rerun compose with server-local secrets before HTTPS deployment can be marked complete.

## 5e. P2-B3 Admin Container HTTP Runtime Boundary

P2-B3 records a deployment-only correction for the admin container runtime. It does not change auth, password reset, user lifecycle, V1 content CMS, SMS, or V2 business behavior.

| Check | Status | Notes |
|---|---|---|
| Admin container Nginx | UPDATED | `deploy/docker/nginx.admin.conf` serves HTTP on container port `80` and no longer references container-local TLS certificate files. |
| Production compose boundary | PRESERVED | `docker-compose.prod.yml` keeps admin bound to `127.0.0.1:15174:80`. |
| Host Nginx boundary | PRESERVED | `deploy/nginx/portal-prod.conf.example` keeps TLS termination on the ECS host and proxies `portal-admin.huairou.tech` to `127.0.0.1:15174`. |

P2-B3 still does not mean production release readiness. The server must pull the updated branch, rebuild the admin service, and verify the local admin upstream before switching public Nginx routing.

## 5f. P3-A Account UX and Password Policy

P3-A is a local-only account experience and password policy stage. It does not deploy to ECS, does not push, does not send real email, does not change SMS, and does not modify deployment templates.

| Check | Status | Notes |
|---|---|---|
| Password policy helper | ADDED | `apps/api-server/app/services/password_policy.py` defines the shared 8–20 / 3-of-4 rule. |
| Registration policy | UPDATED | `POST /api/v1/auth/register` rejects weak passwords. |
| Password reset confirm policy | UPDATED | `POST /api/v1/auth/password-reset/confirm` rejects weak passwords and current-password reuse. |
| Admin user creation policy | UPDATED | `POST /api/v1/admin/users` rejects weak initial passwords. |
| Account profile payload | UPDATED | `/auth/me` includes role code/name for Header and `/profile`. |
| Frontend account UX | UPDATED | Registration redirects home with the pending-review notice; Header shows login state; `/profile` is read-only. |
| Admin password hint | UPDATED | Admin user creation displays the same password rule hint. |
| Backend smoke | ADDED | `scripts/smoke_password_policy_backend.sh` covers weak/strong password and current-password reuse paths. |

P3-A still does not mean production release readiness. Broader account settings, password history, session-expiry UX, performance testing, external security scanning, formal migrations, Kubernetes validation, and V2 business systems remain separate later tracks.

## 5g. P3-B Account Email Notifications

P3-B is a local-only account email notification stage. It does not deploy to ECS, does not push, does not enable SMTP, does not send real email, does not change SMS/SSO, and does not modify deployment templates.

| Check | Status | Notes |
|---|---|---|
| Shared plaintext sender | ADDED | `apps/api-server/app/services/email_notifications.py` centralizes `dev_outbox`, `disabled`, and SMTP provider boundaries. |
| Account notification service | ADDED | `apps/api-server/app/services/account_notifications.py` defines plaintext templates for registration, approval, rejection, admin-created users, and password changes. |
| Registration submitted email | ADDED | `POST /api/v1/auth/register` writes a local `dev_outbox` notification after a pending registration is created. |
| Approval/rejection email | ADDED | Admin approve/reject flows write local notifications; rejection includes the admin reason. |
| Reject reason policy | UPDATED | `POST /api/v1/admin/users/{user_id}/reject` requires a trimmed reason of 20–1000 characters. |
| Admin-created user email | ADDED | The account-created email instructs users to use forgot password and does not include the initial password. |
| Password changed email | ADDED | Successful email password reset confirmation writes a safety notification without token or reset link. |
| Backend smoke | ADDED | `scripts/smoke_account_notifications_backend.sh` validates local `dev_outbox` events and secret boundaries. |

P3-B still does not mean production release readiness. Real SMTP production-domain UAT, HTML email templates, account settings, password history, session-expiry UX, performance testing, external security scanning, formal migrations, Kubernetes validation, and V2 business systems remain separate later tracks.

## 5h. P3-B2 Account Email Notification SMTP UAT

P3-B2 is a local-only real SMTP UAT stage for account email notifications. It does not deploy to ECS, does not push, does not change SMS/SSO, and does not modify deployment templates.

| Check | Status | Notes |
|---|---|---|
| SMTP UAT script | ADDED | `scripts/smoke_account_notifications_smtp_uat.sh` uses runtime SMTP credentials and a controlled recipient outside the repository. |
| Registration submitted email | PASS | Real SMTP delivery confirmed by user mailbox check. |
| Approval email | PASS | Real SMTP delivery confirmed by user mailbox check. |
| Rejection email | PASS | Real SMTP delivery confirmed; formatted reason was received. |
| Admin-created user email | PASS | Real SMTP delivery confirmed; no initial password anomaly reported. |
| Password changed email | PASS | Real SMTP delivery confirmed; no token/reset-link anomaly reported. |
| Secret handling | PASS | No SMTP password, full recipient email, token, full reset link, or password is committed. |

P3-B2 still does not mean production release readiness. Server deployment of P3-B notifications, HTML templates, account settings, password history, session-expiry UX, performance testing, external security scanning, formal migrations, Kubernetes validation, and V2 business systems remain separate later tracks.

## 5i. P3-B3 Account Experience Readiness

P3-B3 is a local-only readiness closure for P3-A, P3-B, and P3-B2. It does not change business code, does not rerun real SMTP UAT, does not deploy to ECS, does not push, does not change SMS/SSO, and does not modify deployment templates.

| Check | Status | Notes |
|---|---|---|
| P3-A evidence | RECORDED | Password policy, registration UX, Header login state, and `/profile` are summarized in `docs/P3_ACCOUNT_EXPERIENCE_READINESS.md`. |
| P3-B evidence | RECORDED | Account notification events, reject reason policy, and `dev_outbox` smoke are summarized. |
| P3-B2 evidence | RECORDED | Real SMTP UAT evidence is referenced without resending email. |
| Security boundary | RECORDED | No SMTP password, full recipient email, token, reset link, or password is committed. |

P3-B3 still does not mean production release readiness. P3-C session-expiry UX, server deployment of account notifications, HTML templates, account settings, password history, IP audit, file security, monitoring, performance testing, external security scanning, formal migrations, Kubernetes validation, and V2 business systems remain separate later tracks.

## 5j. P3-C Session Expiry and Login State Recovery

P3-C is a local-only session expiry stage. It does not deploy to ECS, does not push, does not change SMS/SSO, does not send email, and does not add refresh tokens, token blacklist, or multi-device logout.

| Check | Status | Notes |
|---|---|---|
| Access token lifetime | UPDATED | `ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 180 minutes. |
| Backend JWT expiry | VERIFIED | Expired JWT access tokens are rejected by protected endpoints with 401. |
| Portal frontend recovery | UPDATED | Authenticated API 401 clears Portal token/user state and redirects to `/login?reason=expired`. |
| Admin recovery | UPDATED | Admin API 401 clears admin token/user state and redirects to `/login?reason=expired`. |
| Backend smoke | ADDED | `scripts/smoke_session_expiry_backend.sh` uses a 1-minute token lifetime and verifies 401 after waiting 70 seconds. |

P3-C still does not mean production release readiness. Server deployment, account notification deployment, HTML templates, account settings, password history, IP audit, file security, monitoring, performance testing, external security scanning, formal migrations, Kubernetes validation, and V2 business systems remain separate later tracks.

## 5k. P3-D IP Traceability Audit

P3-D is a local-only IP traceability and account/security audit stage. It does not deploy to ECS, does not push, does not change SMS/SSO, does not send email, and does not add PV/UV analytics, GeoIP, IP blocking, anomaly detection, or a monitoring dashboard.

| Check | Status | Notes |
|---|---|---|
| Request metadata helper | ADDED | `request_context.py` extracts `X-Forwarded-For`, `X-Real-IP`, fallback client host, User-Agent, path, and method. |
| Login traceability | UPDATED | Password login success/failure writes `LoginLog` and auth audit rows with IP, User-Agent, path, method, result, and failure reason. |
| Account/security audit | UPDATED | Registration, password reset request/confirm, protected-route unauthorized, user lifecycle, role assignment, and existing CMS audits carry request metadata. |
| Admin logs UI | UPDATED | The audit logs page adds IP/account/action filters and a login-log tab with IP/User-Agent display. |
| Backend smoke | ADDED | `scripts/smoke_audit_ip_backend.sh` uses test IP `203.0.113.10` and verifies login, registration, password reset, approval/rejection, admin-created user, role change, and filtering. |
| Retention | DOCUMENTED | `docs/P3_AUDIT_IP_TRACEABILITY.md` recommends 180-day retention; automatic cleanup is deferred. |

P3-D still does not mean production release readiness. Formal migrations, server deployment, real operational retention jobs, monitoring, external security scanning, performance testing, Kubernetes validation, and V2 business systems remain separate later tracks.

## 5l. P3-E1 File Download Security

P3-E1 is a local-only file download access-control and audit stage. It does not deploy to ECS, does not push, does not change SMS/SSO, does not send email, and does not add virus scanning, `scan_status`, object storage, file content encryption, public uploads static serving, or PV/UV analytics.

| Check | Status | Notes |
|---|---|---|
| Backend download endpoints | ADDED | `GET /api/v1/public/downloads/{resource_id}/download` serves public resources anonymously; `GET /api/v1/downloads/{resource_id}/download` requires an active logged-in user. |
| Path safety | ADDED | Download paths are derived only from `FileRecord.storage_path`, resolved under `settings.storage_root`, and rejected when they escape the storage root. |
| Metadata boundary | UPDATED | Public downloads and admin file responses do not return `storage_path`; `uploads` remains non-static. |
| Download audit | ADDED | `AuditLog` records `file_download_success`, `file_download_denied`, `file_download_not_found`, and `file_download_path_invalid` with actor type, resource/file IDs, IP, User-Agent, path, method, result, and failure reason. |
| Admin UI | UPDATED | The file library hides storage paths and shows download resource visibility plus a backend-endpoint download action. |
| Backend smoke | ADDED | `scripts/smoke_file_download_security_backend.sh` uses test IP `203.0.113.20` and verifies public/protected download behavior, not-found/path-invalid auditing, and metadata redaction. |
| Retention | DOCUMENTED | `docs/P3_FILE_DOWNLOAD_SECURITY.md` aligns file download audit retention with the P3-D 180-day recommendation; automatic cleanup is deferred. |

P3-E1 still does not mean production release readiness. Virus scanning engine integration, object storage, encrypted-at-rest strategy, formal migrations, server deployment, monitoring, external security scanning, performance testing, Kubernetes validation, and V2 business systems remain separate later tracks.

## 5m. P3-E2 File Scan Status

P3-E2 is a local-only scan-status state machine and fail-closed download gate. It does not deploy to ECS, does not push, does not change SMS/SSO, does not send email, and does not integrate ClamAV or any real scanner.

| Check | Status | Notes |
|---|---|---|
| File metadata | ADDED | `FileRecord` carries `scan_status`, `scan_engine`, `scan_message`, and `scanned_at`; new uploads default to `pending`. |
| Historical default | ADDED | Empty or unknown scan status is normalized to `pending`, so historical files are not implicitly trusted. |
| Download gate | ADDED | Public and protected download endpoints require `scan_status=clean`; `pending`, `infected`, `failed`, and `skipped` are rejected. |
| Download audit | UPDATED | Scan-state download denials use `file_download_denied` with `reason=scan_status_not_clean` and include `scan_status`, IP, User-Agent, path, and method. |
| Mock scanner | ADDED | `file_scanning.py` provides local-only mock scanning for clean, infected, and failed status transitions. |
| Admin UI | UPDATED | The file library displays scan status and allows a single-file mock scan action. |
| Backend smoke | ADDED | `scripts/smoke_file_scan_status_backend.sh` uses test IP `203.0.113.30` and verifies pending, clean, infected, failed, and empty-state gates. |

P3-E2 still does not mean production release readiness. Real antivirus engine design, scanner worker/queue, virus database updates, formal migrations, server deployment, monitoring, external security scanning, performance testing, Kubernetes validation, and V2 business systems remain separate later tracks.

## 5n. P3-E3 ClamAV Worker

P3-E3 is a local-only ClamAV worker experiment. It does not deploy to ECS, does not push, does not start a production scanner service, and does not change SMS/SSO/email/password reset behavior.

| Check | Status | Notes |
|---|---|---|
| clamd provider | ADDED | `file_scanning.py` uses TCP `INSTREAM`; `OK` maps to `clean`, `FOUND` maps to `infected`, unavailable or protocol failure maps to `failed`. |
| One-shot worker | ADDED | `scripts/run_file_scan_worker.py` scans selected `scan_status=pending` files once, supports `limit`, `retries`, and `retry-delay`, and writes `AuditLog`. |
| Default worker scope | ADDED | Worker default is pending-only. `failed` files are not automatically rescanned. |
| clamd unavailable | ADDED | Unavailable clamd produces `scan_status=failed`; downloads remain denied. |
| Admin rescan | ADDED | Admin can trigger a single-file scan using the configured provider or explicit provider. |
| Manual override | ADDED | `super_admin` can mark a file clean with `scan_engine=manual_override` only after a 20–1000 character reason; audit records the override. |
| Download gate | PRESERVED | Public and protected downloads still require `scan_status=clean`; manual override is visibly distinguished by `scan_engine=manual_override`. |
| Local ClamAV compose | ADDED | `deploy/docker/compose.clamav.local.yml` exposes clamd at `127.0.0.1:3310`, starts `clamd` directly with the image-bundled virus database, and keeps `CLAMAV_IMAGE` configurable. |
| EICAR smoke | ADDED | `scripts/smoke_file_clamav_worker_backend.sh` verifies normal clean, EICAR infected, clamd unavailable failed, admin rescan, and manual override. |

P3-E3 still does not mean production release readiness. Server ClamAV deployment, freshclam monitoring, persistent worker or queue, resource limits, formal migrations, performance testing, Kubernetes validation, and V2 business systems remain separate later tracks.

## 5o. P3 Security Hardening Deployment Readiness

P3 security hardening readiness prepares a controlled ECS deployment for the P3 branch. It does not merge `main`, does not push `main`, and does not claim that the server deployment has completed.

| Check | Status | Notes |
|---|---|---|
| Readiness document | ADDED | `docs/P3_SECURITY_HARDENING_READINESS.md` summarizes P3-A through P3-E3 evidence, deployment plan, risks, and secret boundaries. |
| Production runtime config | UPDATED | `docker-compose.prod.yml` passes `ACCESS_TOKEN_EXPIRE_MINUTES`, `FILE_SCAN_PROVIDER`, `CLAMAV_*`, and file scan worker parameters into the API container. |
| Production env example | UPDATED | `.env.production.example` documents non-secret P3 runtime keys and the configurable `CLAMAV_IMAGE`. |
| API worker entry | UPDATED | The API image includes `scripts/run_file_scan_worker.py`, and the worker can locate the API package in both local repo and container layouts. |
| Deployment strategy | DOCUMENTED | Deploy the P3 branch first, back up PostgreSQL and file data, enable server-local SMTP and ClamAV, run the one-shot worker, then verify Portal and Achievement. The ClamAV deployment candidate uses direct `clamd` startup; freshclam operations remain a later hardening gate. |

This readiness still does not mean production release readiness. ECS deployment, backup verification, SMTP server-local secret injection, ClamAV service health, one-shot worker execution, public HTTPS smoke, performance testing, external security scanning, formal migrations, and later `main` merge remain separate gates.

## 6. P0-3 First Validation Run

See `docs/P0_VALIDATION_REPORT.md` for the first real validation run.

Current P0-3 status summary:

| Check | Current Status |
|---|---|
| Minimal acceptance | P0-3 已首次运行，PASS |
| Web typecheck | P0-3 已首次运行，FAIL |
| Web build | P0-3 已首次运行，PASS |
| Admin typecheck | P0-3 已首次运行，PASS |
| Admin build | P0-3 已首次运行，PASS |
| Backend compileall | P0-3 已首次运行，PASS |
| Docker compose config | P0-3 已首次运行，FAIL |
| Backend pytest | 缺失 |
| E2E | 缺失 |
| Security scan | 缺失 |
| Performance test | 缺失 |

## 7. P0-3b Validation Entrypoint Fix

P0-3b corrected validation-entry behavior without changing business source code.

| Check | P0-3b Status | Notes |
|---|---|---|
| `pnpm check:web` | FAIL | Root command form is fixed. Current failure is `Cannot find matching tsconfig.json` for `apps/web-portal`, which requires a later validation/config decision. |
| Docker compose config | PASS | `scripts/check_docker_compose_config.sh` uses `deploy/docker/.env.example` for config validation. Compose `.env` references are optional, so config validation no longer requires a real `.env` file. |
| Minimal acceptance | Pending rerun after commit | `scripts/portal_min_acceptance.sh` now includes Docker Compose config validation and still requires a clean working tree. |

## 8. P0-3c Web Typecheck Configuration Result

P0-3c added `apps/web-portal/tsconfig.json` with the minimal Nuxt extension:

```json
{
  "extends": "./.nuxt/tsconfig.json"
}
```

Current status:

| Check | Status | Notes |
|---|---|---|
| `apps/web-portal/tsconfig.json` | Added | Minimal config only; no path aliases or suppressive compiler options were added. |
| `pnpm check:web` | FAIL | The command now enters real TypeScript checking. Remaining failures are `process` type availability and page error object typing. |
| `pnpm build:web` | PASS | Production build remains valid. |
| `portal_min_acceptance.sh` | PASS after clean commit | The script requires a clean tree and should be run after committing intended config/doc changes. |

Next recommended follow-up: `P0-3d Web Typecheck Error Triage`. Do not mark `pnpm check:web` as a passing gate until those TypeScript findings are resolved or explicitly scoped.

## 9. P0-3d Web Typecheck Triage

P0-3d completed triage for the current `pnpm check:web` failures. See `docs/WEB_TYPECHECK_TRIAGE.md`.

Current status:

| Check | Status | Notes |
|---|---|---|
| `pnpm check:web` | FAIL | Typecheck entrypoint is valid, but 9 TS errors remain. Main categories are missing Nuxt config Node typing and unsafe `error.data.message/detail` access in pages. |
| Web typecheck triage | DONE | Errors were classified without changing business source code. |
| Recommended next step | P0-3e | Repair type errors only after explicit authorization. Recommended strategy is centralized API error typing plus a minimal Nuxt config typing fix. |

## 10. P0-3e Web Typecheck Fix

P0-3e resolved the blocking web typecheck errors without changing backend, admin, database model, API route, or page layout/style behavior.

Current status:

| Check | Status | Notes |
|---|---|---|
| `pnpm check:web` | P0-3e PASS | Previous `process` and `message/detail` TypeScript errors are resolved. A Vue language plugin warning remains non-blocking. |
| `pnpm build:web` | P0-3e PASS | Production build remains valid. |
| `pnpm check:admin` | P0-3e PASS | Admin typecheck remains valid. |
| `pnpm build:admin` | P0-3e PASS | Admin build remains valid. |
| Backend compileall | P0-3e PASS | Backend static compile check remains valid. |

Implementation summary:

- `nuxt.config.ts` uses a local typed `globalThis.process?.env` reader instead of importing `node:process`.
- Web API error display uses a centralized typed helper.
- No backend, admin, database model, or API behavior changed.

## 11. P0-4 API Smoke Skeleton

P0-4 added `scripts/smoke_api_public.sh` and `docs/API_SMOKE_RUNBOOK.md`.

Current state:

| Item | Status | Notes |
|---|---|---|
| Public API smoke script | P0-4 added | Covers `/healthz` and selected non-destructive public GET endpoints. |
| Script syntax check | P0-4 PASS | `bash -n scripts/smoke_api_public.sh`. |
| Placeholder execution | P0-4 BLOCKED-compatible | `PORTAL_SMOKE_ALLOW_UNAVAILABLE=1 ./scripts/smoke_api_public.sh` exited successfully while reporting a blocked smoke result; current local `/healthz` returned `404`. |
| Real API smoke | Not run | Requires an already running API service; P0-4 does not start services. |

The allow-unavailable result must not be recorded as a real API smoke PASS. Real smoke validation remains required before release readiness can be marked complete.

## 12. P0-5 Real Public API Smoke

Public API smoke status: P0-5 PASS.

Evidence:

| Check | Status | Notes |
|---|---|---|
| Compatible runtime | PASS | Python 3.11.15 from `/Users/billchen/.local/bin/python3.11` |
| Isolated backend venv | PASS | `.runtime-logs/p0-5/backend-venv-py311/`, ignored and not committed |
| Dependency installation | PASS | Installed only `apps/api-server/requirements.txt` |
| Local API startup | PASS | API started on `127.0.0.1:18200` with runtime SQLite and uploads under `.runtime-logs/p0-5/` |
| Real public API smoke | PASS | `PORTAL_API_BASE=http://127.0.0.1:18200 ./scripts/smoke_api_public.sh` |
| Post-smoke validation | PASS | Minimal acceptance, web check/build, admin check/build, and backend compileall all passed |

Remaining release gaps are unchanged: auth smoke, admin RBAC smoke, file upload/download security smoke, performance testing, security scanning, and production deployment validation are still required later.

## 13. P0-6 Reusable Local Public API Smoke Runner

Reusable local public API smoke status: P0-6 PASS.

Evidence:

| Check | Status | Notes |
|---|---|---|
| Local smoke runner | PASS | `scripts/run_local_public_api_smoke.sh` added. |
| Runner syntax | PASS | `bash -n scripts/run_local_public_api_smoke.sh`. |
| Real public API smoke | PASS | `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_local_public_api_smoke.sh`. |
| Runtime isolation | PASS | Uses ignored `.runtime-logs/local-public-api-smoke/` for venv, SQLite, uploads, logs, and PID file. |
| Post-run cleanup | PASS | The runner stops the API process it starts and leaves port `18200` free. |
| Post-smoke validation | PASS | Web check/build, admin check/build, backend compileall, and post-commit minimal acceptance passed. |

Remaining release gaps are unchanged: auth smoke, admin RBAC smoke, file upload/download security smoke, performance testing, security scanning, and production deployment validation are still required later.

## 14. P1-A Auth Scope Revision

P1-A records the V1 auth scope correction and password reset reuse audit.

| Item | Status | Notes |
|---|---|---|
| SMS verification login | Excluded from V1 acceptance | Existing SMS login/reset code remains current-code/test-path only. Do not add real SMS provider or SMS V1 smoke. |
| Email password reset | Required for V1 | Current Portal implementation is missing the Achievement-style email reset token flow. |
| Achievement reuse audit | Completed | `docs/P1_PASSWORD_RESET_REUSE_MAP.md` maps reusable routes, models, provider boundaries, tests, and UAT evidence. |
| P1 execution plan | Added | `docs/P1_CONTRACT_CLOSURE_PLAN.md` defines P1-B through P1-G. |

P1-A does not claim password reset completion, SMS acceptance, or Portal SMTP acceptance. Those require later implementation and UAT stages.

## 15. P1-B Email Password Reset Backend

P1-B implements the backend foundation for email-based password reset.

| Item | Status | Notes |
|---|---|---|
| Token persistence | Implemented | `password_reset_tokens` stores `token_hash`, `expires_at`, `consumed_at`, request IP, and user-agent metadata. |
| Request endpoint | Implemented | `POST /api/v1/auth/password-reset/request` returns a generic safe response for existing and missing accounts. |
| Confirm endpoint | Implemented | `POST /api/v1/auth/password-reset/confirm` consumes a valid token and updates `User.password_hash`. |
| Provider boundary | Implemented | `EMAIL_PROVIDER=dev_outbox` writes ignored local runtime mail; `disabled` does not send. Real SMTP is not implemented in Portal P1-B. |
| Backend smoke | Implemented | `scripts/smoke_password_reset_backend.sh` verifies hash-only storage, password rotation, replay rejection, expiry rejection, and audit redaction. |
| Migration framework | Not implemented | Portal still uses `Base.metadata.create_all`; formal migrations remain a later hardening item. |
| Frontend reset pages | Implemented | P1-C owns and completed forgot/reset-confirm UI and login-page entry. |

P1-B does not change SMS verification login scope and does not claim Portal SMTP or full-link UAT completion.

## 16. P1-C Email Password Reset Frontend

P1-C implements the frontend flow for the P1-B backend email password reset contract.

| Item | Status | Notes |
|---|---|---|
| Forgot-password page | Implemented | `/forgot-password` accepts email or username and shows a generic safe response. |
| Reset-confirm page | Implemented | `/password-reset/confirm?token=...` accepts a new password and confirms through the backend. |
| Login-page entry | Implemented | Password login path links to `/forgot-password`. |
| API client methods | Implemented | `requestPasswordReset` and `confirmPasswordReset` call the P1-B endpoints. |
| Token handling | Implemented | The token is read from the route query and submitted to the backend only; it is not displayed, logged, or persisted. |
| SMS scope | Unchanged | SMS verification login remains excluded from V1 acceptance. |
| Real email | Not run | No real SMTP send or provider UAT in P1-C. |

Remaining release gaps include full-link dev outbox/UAT smoke, optional real SMTP UAT, user-management closure, auth/admin smoke coverage, security scanning, and performance testing.

## 17. P1-D User Lifecycle Closure

P1-D closes the Portal V1 account-management lifecycle without changing password-reset behavior or SMS scope.

| Item | Status | Notes |
|---|---|---|
| User states | Implemented | `pending`, `active`, `rejected`, and `disabled` are enforced by password login; authenticated dependency resolution also rejects non-active users. |
| Approval/rejection | Implemented | Pending registrations can be approved or rejected through admin APIs and admin-console actions. |
| Disable/enable | Implemented | Active users can be disabled and disabled users can be enabled; self-disable and last active super-admin modification are protected. |
| Institution user creation | Implemented | Admins can create active users with `registered_user` or `institute_editor` roles. Initial passwords are hashed and not returned. |
| Role assignment | Implemented | `super_admin` can assign roles; self-demotion and last active super-admin demotion are blocked. |
| Audit | Implemented | create, approve, reject, disable, enable, and assign_role user events are recorded without raw passwords or tokens. |
| Admin UI | Implemented | `UsersView.vue` supports lifecycle operations and refreshes after each action. |
| Smoke | Implemented | `scripts/smoke_user_lifecycle_backend.sh` validates the user lifecycle against isolated runtime SQLite. |

Remaining release gaps include broader permission-matrix tests, content CMS acceptance closure, full-link password-reset UAT, security scanning, and performance testing.

## 18. P1-E V1 Content CMS Closure

P1-E closes the V1 content CMS acceptance surface without changing auth, password reset, user lifecycle, SMS, or real email behavior.

| Item | Status | Notes |
|---|---|---|
| Homepage content | Implemented | `/api/v1/public/home` and the public homepage cover banners, institution profile, stats, news, and cases. |
| News | Implemented | Public list/detail support published-only results, category metadata, keyword search, and admin maintenance fields. |
| Cases | Implemented | Public list/detail cover project intro, partner, stage, benefits, result blocks, and admin maintenance fields. |
| About us | Implemented | About content uses page blocks and site settings for mission, vision, strategy, governance, contact, and email. |
| Leaders | Implemented | Public visible leaders and admin maintenance are covered. |
| Categories/tags | Implemented | Public categories/tags and admin category/tag maintenance are covered. |
| Smoke | Implemented | `scripts/smoke_v1_content_backend.sh` validates public content endpoints, draft hiding, and admin endpoint reachability on isolated SQLite. |
| File URL boundary | Deferred | Public file/image delivery remains a later file-service hardening item; P1-E uses safe frontend fallbacks. |

Remaining release gaps include P1-F acceptance report consolidation, broader permission-matrix tests, full-link password-reset UAT, security scanning, performance testing, and production deployment validation.
