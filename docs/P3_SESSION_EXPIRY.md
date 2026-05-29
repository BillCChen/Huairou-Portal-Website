# Portal P3-C Session Expiry

## 1. Scope

P3-C 只覆盖 Portal 会话过期与登录态回收：

- 后端 access token 有效期配置化。
- Portal 前台遇到认证 401 后清理登录态并跳转登录页。
- Admin Console 遇到认证 401 后清理登录态并跳转登录页。
- 本地 smoke 使用 1 分钟过期配置验证 token 初始可用、过期后被拒绝。

P3-C 不覆盖：

- refresh token。
- token blacklist。
- 多端登录互踢。
- IP 审计。
- SMS 或 SSO 修改。
- 真实邮件发送。
- 服务器部署。

## 2. Configuration

| Key | Default | Notes |
|---|---:|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `180` | 后端 access token 有效期，单位为分钟。 |

本地 smoke 使用：

```bash
ACCESS_TOKEN_EXPIRE_MINUTES=1
```

默认 180 分钟用于本地和后续部署的初始账号体验，后续可按运维策略改短。

## 3. Backend Behavior

- 登录成功后签发包含 `exp` 的 JWT。
- `exp` 使用 UTC 时间计算，避免本地时区差异。
- `/api/v1/auth/me` 和后台受保护接口通过统一认证依赖解码 JWT。
- token 过期或无效时返回 401。
- 认证失败响应不包含 token 内容。

## 4. Portal Frontend Behavior

- Portal API client 遇到 401 时清理 `portal_token` 和 `portal_user`。
- 前台自动跳转 `/login?reason=expired`。
- 登录页显示“登录已过期，请重新登录。”。
- `/profile` 仍保护当前用户信息；未登录访问跳转登录，token 过期时由 API 401 处理登录态回收。

## 5. Admin Behavior

- Admin API client 遇到 401 时清理 `portal_admin_token`。
- Admin router 收到过期事件后清理 Pinia 用户状态。
- 后台自动跳转 `/login?reason=expired`。
- LoginView 显示“登录已过期，请重新登录。”。
- router guard 继续保护后台路由，无 token 时不能进入后台页面。

## 6. Smoke

新增本地 smoke：

```bash
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_session_expiry_backend.sh
```

该 smoke 使用隔离 SQLite runtime：

1. 以 `ACCESS_TOKEN_EXPIRE_MINUTES=1` 启动本地 API。
2. 登录获得 access token，但不打印 token。
3. 立即访问 `/api/v1/auth/me`，期望 200。
4. 等待 70 秒。
5. 再次访问 `/api/v1/auth/me`，期望 401。

## 7. Manual Frontend Verification

Portal 前台人工验证建议：

1. 本地以 `ACCESS_TOKEN_EXPIRE_MINUTES=1` 启动 API。
2. 登录 Portal。
3. 等待超过 1 分钟。
4. 访问 `/profile` 或触发 `/auth/me`。
5. 应跳转 `/login?reason=expired` 并显示“登录已过期，请重新登录。”。

Admin Console 人工验证建议同理：登录后台后等待 token 过期，再触发任一后台 API 请求，应跳转后台登录页并显示过期提示。

## 8. Security Boundary

- no refresh token
- no token blacklist
- no multi-device logout
- no SMS/SSO changes
- no email sending
- no server deploy
- no token, password, or secret committed
