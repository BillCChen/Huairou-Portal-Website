# Portal P3-A Account UX and Password Policy

## 1. 范围

P3-A 只处理 Portal 本地账号体验与密码策略一致性，不修改服务器部署、不发送真实邮件、不接入真实 SMS，也不同步 Achievement。

## 2. 密码策略

统一密码策略：

- 长度为 8–20 位。
- 至少包含大写字母、小写字母、数字、特殊字符中的 3 类。
- 拒绝常见弱密码，例如常见默认密码、简单数字序列和平台相关弱口令。
- 拒绝与用户名、邮箱本地部分或手机号等账号信息明显相似的密码。
- 注册、邮件密码重置确认、管理员创建用户均使用同一后端策略。
- 密码重置确认不得把新密码设置为当前密码。

本阶段不新增 `password_history` 表，也不检查最近 3 次或 5 次历史密码重复。

## 3. 后端入口

| 入口 | 结果 |
|---|---|
| `POST /api/v1/auth/register` | 弱密码拒绝，合规密码进入 `pending` |
| `POST /api/v1/auth/password-reset/confirm` | 弱密码拒绝，当前相同密码拒绝，合规新密码可消费 token |
| `POST /api/v1/admin/users` | 弱初始密码拒绝，合规初始密码可创建 active 机构用户 |
| `GET /api/v1/auth/me` | 返回 profile/header 需要的 username、real name、email、mobile、organization、role、status |

密码仍使用现有 hash helper，不做可逆加密。

## 4. 前台账号体验

- 注册页展示统一密码规则提示，包括长度、复杂度、常见弱密码和账号信息相似限制。
- 注册成功后跳转门户首页。
- 首页顶部展示：注册已提交，等待审核，注意查收邮件。
- P3-A 只显示提示文案；P3-B 已在本地账号通知阶段实现 `dev_outbox` 注册通知验证，真实 SMTP 发送仍留到后续独立 UAT。
- 密码重置确认页展示同一密码规则提示，并透传后端拒绝原因。
- Header 未登录时显示登录 / 注册。
- Header 已登录时显示用户名或真实姓名、角色、个人中心和退出。
- `/profile` 是最小只读个人中心，仅展示用户名、真实姓名、邮箱、手机号、单位、角色和账号状态。

## 5. 后台管理端

管理员创建用户表单在初始密码输入框附近展示同一密码规则，包括常见弱密码和账号信息相似限制。后端仍是最终准入点，不在页面或日志中回显密码。

## 6. 未做事项

- 未实现真实 SMTP 注册邮件发送。
- 未修改 SMS verification login 或真实 SMS provider。
- 未修改服务器 Nginx、Docker、ECS 部署配置。
- 未实现修改密码页面。
- 未实现历史密码表。
- 未进入 V2 业务模块。

## 7. 验证入口

新增本地后端 smoke：

```bash
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_password_policy_backend.sh
```

该 smoke 使用隔离 SQLite runtime，覆盖弱密码拒绝、合规注册、弱密码重置拒绝、当前相同密码重置拒绝、合规重置、管理员弱密码创建拒绝和管理员合规创建。
