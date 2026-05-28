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
