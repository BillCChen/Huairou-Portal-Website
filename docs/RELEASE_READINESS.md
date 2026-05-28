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
- `SiteHeader.vue` 中的本地 Achievement 地址只能作为演示入口，不能作为生产第三方系统对接。
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

运行方式：

```bash
./scripts/check_forbidden_artifacts.sh
./scripts/check_secrets_basic.sh
python3 scripts/extract_api_routes.py
./scripts/portal_min_acceptance.sh
```

当前边界：

- P0-2 不验证业务正确性。
- P0-2 不替代后端 pytest、前端 build、E2E、安全扫描、性能压测。
- P0-2 只建立最低限度的仓库卫生和 API 路由可见性检查。

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
