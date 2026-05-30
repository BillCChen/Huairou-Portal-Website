# Portal P3-E3 ClamAV Worker

## 1. Scope

P3-E3 是本地 ClamAV clamd 异步扫描 worker 试验，覆盖：

- `clamd` TCP provider。
- 一次性 scanner worker。
- 小次数 retry。
- `clamd` 不可用时标记 `failed`。
- 管理员单文件重新扫描。
- `super_admin` 手动放行。
- 本地 ClamAV compose 和 EICAR smoke。

本阶段不覆盖：

- 服务器部署。
- 常驻 worker。
- Celery / RQ / Redis 队列。
- 多引擎扫描。
- CDR 文件消毒。
- 沙箱执行。
- 对象存储。
- 文件内容加密。
- Achievement 同步。

## 2. Architecture

Portal API 继续负责上传、下载门禁和审计。文件上传后仍默认 `scan_status=pending`。

Scanner worker 是一次性命令，默认只读取 `pending` 文件，调用 `clamd` TCP 扫描，然后写回 `scan_status`、`scan_engine`、`scan_message` 和 `scanned_at`。

ClamAV daemon 由本地 `clamd` TCP 服务提供。P3-E3 不把 `clamd` 做成 Portal 常驻 worker，也不把生产部署配置切到 ClamAV。

`freshclam` 病毒库更新属于部署和运维阶段。本地 compose 只用于 smoke。

## 3. Worker Command

本地 worker 命令：

```bash
python scripts/run_file_scan_worker.py --provider clamd --limit 20 --retries 2 --retry-delay 5
```

参数：

- `--provider`：`clamd` 或 `mock`。
- `--limit`：单次最多扫描文件数。
- `--retries`：扫描失败后的重试次数。
- `--retry-delay`：重试等待秒数。
- `--status`：默认 `pending`。
- `--dry-run`：只列出候选文件，不写状态。

worker 完成扫描流程后退出。即使存在 `infected` 或 `failed` 文件，扫描过程本身完成也返回 0；只有配置错误或数据库不可用才返回非 0。

## 4. clamd Config

运行时配置：

- `FILE_SCAN_PROVIDER=clamd`
- `CLAMAV_HOST=127.0.0.1`
- `CLAMAV_PORT=3310`
- `CLAMAV_TIMEOUT_SECONDS=30`
- `FILE_SCAN_WORKER_LIMIT=20`
- `FILE_SCAN_WORKER_RETRIES=2`
- `FILE_SCAN_WORKER_RETRY_DELAY_SECONDS=5`

`file_scanning.py` 使用 clamd `INSTREAM` 协议，文件内容按块发送给 TCP 服务。这样 `clamd` 容器不需要直接访问 Portal 的上传目录。

## 5. Status Behavior

扫描状态：

- `clean`：允许下载。
- `infected`：拒绝下载。
- `failed`：拒绝下载。
- `pending`：拒绝下载。
- `skipped`：拒绝下载。

`clamd` 不可用、连接超时、协议错误或文件不可读时，最终状态为 `failed`。`failed` 不会被 worker 默认自动重扫，管理员需要手动触发重扫或由 `super_admin` 手动放行。

下载门禁仍只判断 `scan_status=clean`。P3-E3 不改变 P3-E2 的 fail-closed 行为。

## 6. Manual Override

手动放行规则：

- 仅 `super_admin` 可执行。
- reason 必填。
- reason trim 后必须为 20–1000 字符。
- 文件标记为 `scan_status=clean`。
- `scan_engine=manual_override`。
- `scan_message` 记录手动放行原因，并明确没有经过 ClamAV 扫描。
- 写入 `AuditLog`：`action=file_scan_manual_override`。

后台必须把 `manual_override` 显示为“手动放行（未扫描）”，不能显示成普通“已通过”。

## 7. Local ClamAV Compose

本地 ClamAV compose：

```bash
docker compose -f deploy/docker/compose.clamav.local.yml up -d
```

默认端口：

- `127.0.0.1:3310`

镜像可通过 `CLAMAV_IMAGE` 覆盖。当前本地 compose 默认使用 `quay.io/ukhomeofficedigital/clamav:latest`，因为本机 Docker Hub 拉取 `clamav/clamav` 系列镜像时遇到 registry referrers 响应解析错误。

可选官方镜像：

```bash
CLAMAV_IMAGE=clamav/clamav:stable-debian13-slim docker compose -f deploy/docker/compose.clamav.local.yml up -d
```

本地 compose 直接启动 `clamd`，使用镜像内置病毒库。该方式避免本地或 ECS 网络访问 `database.clamav.net` 失败时阻塞 `clamd` 启动；病毒库更新、freshclam 调度和更新失败告警仍属于后续生产运维阶段。病毒库目录、缓存和 runtime 文件不进入 Git。

## 8. EICAR Smoke

EICAR 是标准杀毒测试字符串，用于验证扫描链路，不代表真实恶意样本。

本地 smoke：

```bash
PORTAL_BACKEND_PYTHON=python3.11 \
CLAMAV_HOST=127.0.0.1 \
CLAMAV_PORT=3310 \
PORTAL_CLAMAV_SMOKE_CONFIRM=true \
./scripts/smoke_file_clamav_worker_backend.sh
```

如需脚本自动启动本地 ClamAV compose：

```bash
PORTAL_CLAMAV_SMOKE_START_COMPOSE=true \
PORTAL_CLAMAV_SMOKE_CONFIRM=true \
./scripts/smoke_file_clamav_worker_backend.sh
```

覆盖：

- 普通文件经 clamd 扫描为 `clean` 并可下载。
- EICAR 文件经 clamd 扫描为 `infected` 并拒绝下载。
- clamd 不可用时标记 `failed` 并拒绝下载。
- failed 文件手动重扫后恢复 `clean`。
- failed 文件经 `super_admin` 手动放行后可下载，并保留 `manual_override` 审计。
- 非 `super_admin` 手动放行被拒绝。
- reason 少于 20 字被拒绝。

smoke 不输出 token、password、secret、完整 reset link、SMTP secret 或上传目录路径。

## 9. Production Notes

生产化前仍需单独设计：

- freshclam 更新策略。
- freshclam 更新失败时的镜像内置库降级策略。
- clamd 资源限制。
- 文件大小和超时策略。
- 常驻 worker 或队列。
- failed scan 监控和告警。
- formal database migration。
- ECS 部署和回滚 runbook。

P3-E3 本地试验不等于生产 ClamAV 已部署。
