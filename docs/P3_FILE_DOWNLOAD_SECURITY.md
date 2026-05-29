# Portal P3-E1 File Download Security

## 1. Scope

P3-E1 只覆盖 Portal 文件下载门禁和审计：

- public 下载资源允许匿名下载，但必须通过后端下载 endpoint。
- protected 下载资源要求 active 登录用户。
- 下载成功、拒绝、未找到和路径异常都进入应用级审计。
- 审计复用 P3-D 的 IP / User-Agent / path / method 记录能力。

P3-E1 不覆盖：

- 病毒扫描。
- `scan_status` 状态机，已由 P3-E2 独立处理。
- ClamAV 或其他扫描服务。
- 文件内容加密。
- 对象存储 S3 / OSS。
- 断点上传或分片上传。
- 文件预览。
- 全站 PV/UV 统计。
- Achievement 同步。
- 服务器部署。

## 2. File Visibility

public:

- 匿名用户可以下载。
- 下载入口为后端接口。
- 每次成功、拒绝、未找到和路径异常都记录 IP / User-Agent。

protected:

- active 登录用户可以下载。
- 未登录、无效 token、过期 token 或非 active 用户会被拒绝。
- 成功下载记录用户账号、IP、User-Agent、路径、方法和结果。

P3-E1 不做细粒度角色权限。protected 文件只要求当前用户是 active 登录用户。

P3-E2 在此基础上增加 fail-closed 扫描状态门禁：public 和 protected 文件都必须 `scan_status=clean` 才允许下载。

P3-E3 延续同一下载规则：ClamAV 扫描为 `clean` 或 `super_admin` 手动放行后的 `manual_override` 才能下载；`pending`、`infected`、`failed`、`skipped` 仍拒绝下载并审计。

## 3. Download Endpoints

实际下载入口：

- `GET /api/v1/public/downloads/{resource_id}/download`
- `GET /api/v1/downloads/{resource_id}/download`

公开列表：

- `GET /api/v1/public/downloads`

公开列表和后台文件列表不会返回 `storage_path`。浏览器只拿到后端 download URL，不拿服务器文件系统路径。

`uploads` 目录不作为静态目录暴露。下载接口不会接受用户传入文件系统路径，也不会用 query 参数拼接磁盘路径。

## 4. Audit Events

下载审计复用 `AuditLog`，事件包括：

- `file_download_success`
- `file_download_denied`
- `file_download_not_found`
- `file_download_path_invalid`

审计记录包含：

- `user_id`，匿名下载为空。
- `detail_json.actor_type`，值为 `anonymous` 或 `user`。
- `detail_json.resource_id`
- `detail_json.file_id`
- `detail_json.origin_name`
- `detail_json.is_public`
- `detail_json.username`
- `detail_json.result`
- `detail_json.reason`
- `ip_address`
- `user_agent`
- `path`
- `method`
- `result`
- `failure_reason`

日志不得写入文件内容、password、password hash、access token、raw reset token、完整 reset link、SMTP secret 或服务器真实存储根路径。

## 5. Transport and Storage Boundary

浏览器到宿主机 Nginx 的传输加密由 HTTPS 负责。容器内部 HTTP 只在 localhost / Docker network 边界内使用。

P3-E1 不做文件内容加密，不做数据库透明加密，也不改变现有上传存储结构。下载路径由数据库中的 `FileRecord.storage_path` 派生，并在服务端解析后校验必须位于 `settings.storage_root` 内。

P3-E2 只新增扫描状态门禁和 mock scanner，不改变存储结构，不接真实扫描引擎。

P3-E3 新增本地 ClamAV worker 试验，不改变上传存储结构，不暴露 `uploads` 静态目录，也不向公开接口返回 `storage_path`。

## 6. Retention

文件下载审计建议与 P3-D 一致，保留 180 天。

本阶段不实现自动清理任务。后续运维阶段可补充归档、清理或导出脚本。

## 7. Smoke

新增本地 smoke：

```bash
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_file_download_security_backend.sh
```

该 smoke 使用隔离 SQLite runtime，并通过请求头传入：

- test IP: `203.0.113.20`
- test User-Agent: `Portal-P3E1-File-Smoke/1.0`

覆盖内容：

- public 匿名下载成功。
- public 下载响应内容与测试文件一致。
- protected 资源匿名下载被拒绝。
- protected 资源 active 用户下载成功。
- 不存在资源返回 404 并记录审计。
- 路径越界资源被拒绝并记录审计。
- public downloads API 不返回 `storage_path`。
- 审计记录包含 IP / User-Agent。
- smoke 输出不打印 token、password 或 secret。

## 8. Remaining Work

P3-E2 已继续处理：

- `scan_status` 状态机。
- public / protected 下载必须 `clean`。
- mock scanner 状态流转验证。
- 非 `clean` 下载拒绝审计。

P3-E3 已继续处理：

- 本地 ClamAV `clamd` TCP 扫描 provider。
- 一次性 scanner worker。
- EICAR smoke。
- admin rescan。
- `super_admin` manual override。

P3-E3 仍未处理：

- 服务器生产 ClamAV 部署。
- 常驻 worker / queue。
- virus database update monitoring。
- 生产环境 scanner fail-closed 运维策略。

后续独立阶段可处理：

- object storage。
- encrypted-at-rest strategy。
- file lifecycle cleanup。
- formal database migrations。
