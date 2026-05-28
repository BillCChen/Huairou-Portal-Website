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
