# Portal Website API Route Map

## 1. Public Routes

| Method | Path | 说明 | 状态 |
|---|---|---|---|
| GET | /healthz | 健康检查 | 已有 |
| GET | /api/v1/public/categories | 公开分类 | 已有 |
| GET | /api/v1/public/home | 首页数据 | 已有 |
| GET | /api/v1/public/news | 新闻列表 | 已有 |
| GET | /api/v1/public/news/{slug} | 新闻详情 | 已有 |
| GET | /api/v1/public/cases | 案例列表 | 已有 |
| GET | /api/v1/public/cases/{slug} | 案例详情 | 已有 |
| GET | /api/v1/public/pages/{page_key} | 单页内容 | 已有 |
| GET | /api/v1/public/leaders | 领导团队 | 已有 |
| GET | /api/v1/public/institutes | 研究所列表 | 已有 |
| GET | /api/v1/public/institutes/{slug} | 研究所详情 | 已有 |
| GET | /api/v1/public/settings | 公开设置 | 已有 |
| GET | /api/v1/public/downloads | 下载资源列表 | 已有 |
| POST | /api/v1/public/inquiries | 在线咨询提交 | 已有 |

## 2. Auth Routes

| Method | Path | 说明 | 状态 |
|---|---|---|---|
| POST | /api/v1/auth/sms-send | 发送短信验证码 | 测试外壳 |
| POST | /api/v1/auth/reset-password | 重置密码 | 基础实现 |
| POST | /api/v1/auth/password-reset/request | 邮箱密码重置请求 | P1-B 后端已实现；P1-C 前端已接入 |
| POST | /api/v1/auth/password-reset/confirm | 邮箱密码重置确认 | P1-B 后端已实现；P1-C 前端已接入 |
| POST | /api/v1/auth/login/password | 账号密码登录 | 已有 |
| POST | /api/v1/auth/login/sms | 短信登录 | 测试外壳 |
| POST | /api/v1/auth/register | 个人注册 | 已有 |
| GET | /api/v1/auth/me | 当前用户 | 已有 |

## 3. Admin Routes

| Method | Path | 说明 | 状态 |
|---|---|---|---|
| GET | /api/v1/admin/dashboard | 后台仪表盘 | 已有 |
| GET/POST/PUT | /api/v1/admin/articles | 文章管理 | 已有 |
| GET/POST/PUT | /api/v1/admin/cases | 案例管理 | 已有 |
| GET/POST/PUT | /api/v1/admin/pages | 单页管理 | 已有 |
| GET/POST/PUT | /api/v1/admin/banners | Banner 管理 | 已有 |
| GET/POST/PUT | /api/v1/admin/categories | 分类管理 | 已有 |
| GET/POST | /api/v1/admin/tags | 标签管理 | 已有 |
| GET/POST/PUT | /api/v1/admin/leaders | 领导管理 | 已有 |
| GET/POST/PUT | /api/v1/admin/institutes | 研究所管理 | 已有 |
| GET | /api/v1/admin/files | 文件列表 | 已有 |
| POST | /api/v1/admin/files/upload | 文件上传 | 已有 |
| GET | /api/v1/admin/settings | 设置列表 | 已有 |
| GET | /api/v1/admin/settings/site | 站点设置 | 已有 |
| PUT | /api/v1/admin/settings/{setting_key} | 更新设置 | 已有 |
| GET | /api/v1/admin/users | 用户列表 | 已有 |
| GET | /api/v1/admin/users/pending | 待审核用户 | 已有 |
| GET | /api/v1/admin/roles | 角色元数据 | P1-D 已实现 |
| POST | /api/v1/admin/users | 管理员创建机构用户 | P1-D 已实现 |
| POST | /api/v1/admin/users/{user_id}/approve | 审核通过 | 已有 |
| POST | /api/v1/admin/users/{user_id}/reject | 审核驳回 | P1-D 已实现 |
| POST | /api/v1/admin/users/{user_id}/disable | 禁用用户 | P1-D 已实现 |
| POST | /api/v1/admin/users/{user_id}/enable | 启用用户 | P1-D 已实现 |
| PUT | /api/v1/admin/users/{user_id}/role | 用户角色分配 | P1-D 已实现 |
| GET/POST/PUT | /api/v1/admin/downloads | 下载资源管理 | 已有 |
| GET | /api/v1/admin/service-requests | 服务请求列表 | 已有 |
| GET | /api/v1/admin/audit-logs | 操作日志 | 已有 |
| GET | /api/v1/admin/login-logs | 登录日志 | 已有 |

## 4. Known API Gaps

- 缺统一业务错误码。
- 文档中响应 `code` 口径与代码可能不一致。
- 缺完整认证 API smoke 脚本；P1-B 已增加邮箱密码重置后端 smoke。
- 缺权限矩阵测试；P1-D 已增加用户生命周期后端 smoke。
- 缺文件下载门禁接口。
- 缺邮箱密码重置完整链接 UAT；前端页面已在 P1-C 接入。
- 缺全站搜索接口。
- 缺统计/推荐接口。
