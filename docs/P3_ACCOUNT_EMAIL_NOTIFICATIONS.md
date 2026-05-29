# Portal P3-B Account Email Notifications

## 1. 范围

P3-B 只实现 Portal 本地账号邮件通知链路。通知使用已有邮箱 provider 边界，并在本地验证中使用 `dev_outbox`。本阶段不发送真实邮件、不启用 SMTP、不部署服务器、不修改 SMS/SSO，也不进入 V2 业务模块。

## 2. 通知事件

| 事件 | 触发点 | 结果 |
|---|---|---|
| 注册申请已提交 | 个人注册成功并进入 `pending` | 写入注册已提交通知 |
| 账号审核已通过 | 管理员将 pending 用户审核为 `active` | 写入账号可登录通知 |
| 注册申请审核未通过 | 管理员将 pending 用户审核为 `rejected` | 写入包含审核说明的通知 |
| 管理员创建账号 | 管理员创建 active 机构用户 | 写入账号已创建通知 |
| 密码已修改 | 邮件密码重置确认成功 | 写入安全提醒通知 |

## 3. 纯文本模板

邮件模板均为纯文本，便于本地审计、快速验证和多端阅读。本阶段不实现 HTML 邮件模板。

邮件正文只包含账号事件所需信息，不包含 access token、reset token、完整 reset link、SMTP secret、数据库密码或管理员初始密码。

## 4. 管理员创建用户通知

管理员创建机构用户后，系统发送“账号已创建”通知。邮件包含用户名、登录地址和“通过忘记密码设置或重置登录密码”的说明。

邮件不包含管理员填写的初始密码，也不包含 `password_hash`。

## 5. 审核拒绝原因

审核拒绝时，管理员必须填写原因。后端要求去除首尾空白后不少于 20 个字符，最多 1000 个字符。后台管理端在提交前也做同样的最小长度提示。

审核拒绝邮件包含格式化字段：

- 审核结果：未通过
- 审核说明：管理员填写的 reason
- 后续建议：如需补充材料，请联系平台管理员

## 6. 密码修改成功通知

邮件密码重置确认成功后，系统发送“密码已修改”安全通知。通知只提示密码已修改以及非本人操作时联系管理员，不包含 reset token 或 reset link。

P3-B 不修改 password reset token/hash/expiry/consumed 语义。

## 7. Provider 边界

| Provider | P3-B 行为 |
|---|---|
| `dev_outbox` | 写入本地 ignored outbox，用于 smoke 验证 |
| `disabled` | 不发送邮件，主业务流程继续 |
| `smtp` | 保留 provider 能力，但本阶段不启用、不发送真实邮件 |

真实 SMTP 域名 UAT 应在后续独立阶段执行。

## 8. 本地验证

新增 smoke：

```bash
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_account_notifications_backend.sh
```

该 smoke 使用隔离 SQLite runtime 和 `dev_outbox`，覆盖注册提交、审核通过、审核拒绝 reason 校验、管理员创建账号、密码修改成功通知，并验证管理员创建账号邮件不包含初始密码。

## 9. 未做事项

- 未发送真实邮件。
- 未启用 SMTP。
- 未修改 SMS verification login 或真实 SMS provider。
- 未修改 SSO。
- 未修改部署配置。
- 未部署服务器。
- 未实现 HTML 邮件模板。
