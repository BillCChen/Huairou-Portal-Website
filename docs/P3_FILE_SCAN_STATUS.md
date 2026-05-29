# Portal P3-E2 File Scan Status

## 1. Scope

P3-E2 只覆盖 Portal 文件扫描状态机和 fail-closed 下载策略。

本阶段覆盖：

- `FileRecord` 扫描状态元数据。
- public / protected 下载前的 `clean` 状态检查。
- 非 `clean` 文件下载拒绝审计。
- 本地 mock scanner，用于状态机和 smoke 验证。
- 后台文件库扫描状态展示和单文件模拟扫描操作。

本阶段不覆盖：

- 真实病毒扫描引擎。
- ClamAV 或其他扫描服务。
- 病毒库更新。
- 常驻 worker、异步队列或批量扫描。
- 对象存储。
- 文件内容加密。
- 数据库透明加密。
- 分片上传、断点上传或文件预览。
- Achievement 同步。
- 服务器部署。

真实扫描引擎、worker、队列和病毒库运维设计留到 P3-E3。

P3-E3 已在本地试验中补充 `clamd` TCP provider、一次性 worker、管理员重扫和 `super_admin` 手动放行。该补充仍不代表服务器生产部署。

## 2. scan_status

`scan_status` 取值：

- `pending`：待扫描。
- `clean`：已通过扫描，可下载。
- `infected`：mock scanner 检出测试风险签名。
- `failed`：扫描失败或文件不可读。
- `skipped`：扫描被跳过，仍不可下载。

新上传文件默认 `pending`。

历史文件、空值、未知值按 `pending` 处理。这样可以避免旧文件在没有安全状态证据时被默认放行。

## 3. Download Policy

下载规则：

- public 文件允许匿名访问下载 endpoint，但必须 `scan_status=clean`。
- protected 文件要求 active 登录用户，并且必须 `scan_status=clean`。
- `pending` / `infected` / `failed` / `skipped` 全部 fail-closed，返回拒绝响应。
- 只有下载成功才增加 `download_count`。

下载接口不返回 `storage_path`，也不接受用户传入文件系统路径。文件路径仍由数据库记录派生，并校验位于 `settings.storage_root` 内。

## 4. Mock Scanner

P3-E2 的 mock scanner 只用于本地验证和管理员手工触发，不代表真实病毒防护。

mock 规则：

- 文件名或内容包含 `EICAR` / `infected`：标记为 `infected`。
- 文件名或内容包含 `scan-fail`：标记为 `failed`。
- 文件不存在或不可读：标记为 `failed`。
- 其他普通文件：标记为 `clean`。

mock scanner 不调用外部进程，不接 ClamAV，不读取超过 1 MB 的文件样本，不输出文件内容。

P3-E3 在此基础上新增 `clamd` provider。`clamd` 扫描使用 TCP `INSTREAM`，普通文件映射为 `clean`，EICAR 命中映射为 `infected`，连接不可用、超时或协议异常映射为 `failed`。

## 5. Admin UI

后台文件库展示：

- 扫描状态。
- 扫描引擎。
- 扫描时间。
- 扫描说明。
- 单文件“模拟扫描”操作。
- P3-E3 起支持单文件重新扫描。
- P3-E3 起支持 `super_admin` 手动放行，并以“手动放行（未扫描）”区别于普通扫描通过。

后台不会展示 `storage_path`，不会暴露上传目录结构，也不提供复杂扫描队列 UI。

## 6. Audit

下载拒绝复用 P3-D / P3-E1 的 `AuditLog`，并增加扫描状态信息：

- `detail_json.resource_id`
- `detail_json.file_id`
- `detail_json.actor_type`
- `detail_json.username`
- `detail_json.scan_status`
- `detail_json.result`
- `detail_json.reason`
- `ip_address`
- `user_agent`
- `path`
- `method`

非 `clean` 拒绝使用：

- `action=file_download_denied`
- `reason=scan_status_not_clean`

管理员触发 mock scan 使用：

- `module=files`
- `action=file_mock_scan`

P3-E3 新增：

- `action=file_scan`
- `action=file_scan_worker`
- `action=file_scan_manual_override`
- `detail_json.scan_engine`

`manual_override` 必须保留审计原因，并明确该 `clean` 状态未经过 ClamAV 扫描。

审计不记录文件内容、password、password hash、access token、raw reset token、完整 reset link、SMTP secret 或服务器真实存储根路径。

## 7. Smoke

新增本地 smoke：

```bash
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_file_scan_status_backend.sh
```

该 smoke 使用隔离 SQLite runtime，并通过请求头传入：

- test IP: `203.0.113.30`
- test User-Agent: `Portal-P3E2-Scan-Smoke/1.0`

覆盖内容：

- public 文件默认 `pending`，匿名下载被拒绝。
- mock scan 普通 public 文件后变为 `clean`，匿名下载成功。
- protected 文件默认 `pending`，active 用户下载被拒绝。
- infected 文件经 mock scan 标记为 `infected`，下载被拒绝。
- clean protected 文件 active 用户下载成功。
- failed / skipped / 空扫描状态下载被拒绝。
- public / admin metadata 不返回 `storage_path`。
- 下载拒绝审计包含 IP / User-Agent / `scan_status` / `scan_status_not_clean`。
- smoke 输出不打印 token、password 或 secret。

## 8. Remaining Work

P3-E3 已继续处理：

- 本地 ClamAV `clamd` TCP provider。
- 一次性 scanner worker。
- worker retry。
- clamd unavailable -> `failed`。
- admin rescan。
- `super_admin` manual override。

P3-E3 仍未处理：

- 服务器部署。
- 常驻 worker 或队列。
- 病毒库运维监控。
- 资源占用和生产 fail-closed 运维策略。

后续独立阶段：

- object storage。
- encrypted-at-rest strategy。
- file lifecycle cleanup。
- formal database migrations。
