# Portal P3-D IP Traceability Audit

## 1. Scope

P3-D 只覆盖 Portal 应用级账号、安全和后台管理审计：

- 关键账号事件记录客户端 IP、User-Agent、请求路径、请求方法和结果。
- 后台管理已有 audit 覆盖项补充请求来源信息。
- 后台审计日志页提供最小 IP、账号和事件类型筛选。
- 本地 smoke 使用保留测试 IP 验证可溯源能力。

P3-D 不覆盖：

- 全站 PV/UV 统计。
- Prometheus / Grafana / 监控 dashboard。
- Nginx access log 采集。
- GeoIP。
- IP 封禁。
- 异常登录风控。
- 文件病毒扫描或文件加密。
- Achievement 同步。
- 服务器部署。

## 2. Logged Events

P3-D 记录或增强以下事件：

- password login success / failure
- unauthorized protected-route access where the token reaches backend validation
- registration submitted
- password reset request
- password reset confirm success/failure
- pending user approve / reject
- user disable / enable
- admin-created user
- role assignment
- existing CMS audit events where `write_audit_log` is already used, including articles, cases, pages, banners, categories, tags, leaders, institutes, files, settings, and downloads

P3-D 不记录所有 public GET 页面访问，也不记录公开内容浏览日志。

## 3. Request Metadata

`LoginLog` 和 `AuditLog` 的应用级记录可包含：

- `ip_address`
- `user_agent`
- `path`
- `method`
- `result`
- `failure_reason`

日志不得写入 password、password hash、raw reset token、完整 reset link、SMTP secret 或 access token。

## 4. IP Extraction

请求来源提取顺序：

1. `X-Forwarded-For` 的第一个非空 IP。
2. `X-Real-IP`。
3. `request.client.host`。
4. 无法识别时使用 `unknown`。

`X-Forwarded-For` 和 `X-Real-IP` 只应在可信 Nginx 反向代理部署边界内使用。若未来出现多层代理或公网直连容器，需要重新确认可信代理链。

User-Agent 最长保留 512 字符，超长内容会截断，避免异常请求头撑大日志存储。

## 5. Retention

建议账号和安全审计日志保留 180 天。

P3-D 不实现自动清理任务。后续运维阶段可补充归档或清理脚本，并在执行前确认备份与合规要求。

## 6. Admin Visibility

- IP 和 User-Agent 仅后台管理员可见。
- 公开门户页面不展示 IP。
- 本地测试使用保留测试 IP `203.0.113.10`。
- 文档不记录真实用户公网 IP 或完整个人邮箱。

后台审计日志页提供：

- 审计事件 tab：按 IP、账号、action/module 查询。
- 登录记录 tab：按 IP、账号、登录方式和成功/失败查询。
- User-Agent 只做简略展示，完整值通过 tooltip 查看。

## 7. Smoke

新增本地 smoke：

```bash
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_audit_ip_backend.sh
```

该 smoke 使用隔离 SQLite runtime，并通过请求头传入：

- test IP: `203.0.113.10`
- test User-Agent: `Portal-P3D-Audit-Smoke/1.0`

覆盖内容：

- login success trace
- login failure trace
- registration trace
- password reset request trace
- password reset confirm trace
- approve / reject trace
- admin-created user trace
- role change trace
- IP / account / action filtering
- audit API 不暴露 password、token、reset link 或 Authorization header

## 8. Security Boundary

- no push
- no server deployment
- no real SMTP UAT
- no SMS provider change
- no SSO change
- no PV/UV analytics
- no GeoIP
- no IP blocking
- no heavy monitoring system
- no secret, token, password, full reset link, or full email committed
