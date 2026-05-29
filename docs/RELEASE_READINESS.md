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
- `apps/api-server/app/main.py` 存在临时 `ensure_banner_tag_column()` 兼容逻辑，后续应以正式迁移替代。
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

P3-A still does not mean production release readiness. Real registration email, broader account settings, password history, session-expiry UX, performance testing, external security scanning, formal migrations, Kubernetes validation, and V2 business systems remain separate later tracks.

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
