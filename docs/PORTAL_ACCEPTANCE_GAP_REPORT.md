# Portal Website 验收差距报告

## 1. 当前基线

- 分支：codex/portal-baseline-attribution
- 基线快照提交：9c0d7e9
- 当前目标：P0 仓库卫生、验收差距固化、后续 P1/P2 开发依据

## 2. 结论摘要

Portal 当前处于“V1 雏形 + V2 展示/占位外壳 + 生产验收体系缺失”的状态。

P1-A 范围修订确认：手机号验证码登录不再作为 Portal V1 验收项；邮箱邮件密码重置是 Portal V1 必做项。现有短信登录和短信验证码重置只能标记为 current-code/test-path，不能计入 V1 acceptance。

V1 中首页、新闻、案例、关于我们、登录、注册、审核、领导团队已有基础实现，但尚不能按合同验收闭环描述。主要缺口包括：邮箱密码重置、机构用户管理员分配、拒绝/禁用/启用、角色赋权、权限矩阵、测试报告、性能压测、安全扫描、生产部署验收。

V2 多数模块当前只能定性为展示页、CMS 内容承载或占位入口，尚未形成简历投递、专家预约、活动报名、全站搜索、统计、推荐、第三方系统对接等业务闭环。

## 3. V1 差距矩阵

| 功能项 | 当前状态 | 主要证据 | 缺口 | 下一步 |
|---|---|---|---|---|
| 首页访问入口 | 基本可用 | apps/web-portal/pages/index.vue | 缺验收脚本、SSG/ISR 与方案不一致 | P1 |
| 登录按钮与登录页 | 基本可用 | SiteHeader.vue, LoginView.vue | 缺失败用例、锁定/限流 | P1/P2 |
| 账号密码登录 | 基本可用 | /api/v1/auth/login/password | 缺测试、刷新/吊销 | P1/P2 |
| 手机号验证码登录 | 现有测试外壳；V1 排除 | /auth/sms-send, SMS_TEST_CODE | 不纳入 V1 acceptance；不接真实 SMS provider | 后置/非 P1 |
| 邮箱密码重置 | 后端基础已实现 | `/auth/password-reset/request`, `/auth/password-reset/confirm`, `password_reset_tokens` | 仍需前端 forgot/reset-confirm 页面、真实 SMTP UAT、full-link UAT | P1 |
| 机构用户管理员分配 | 缺失 | 无创建机构用户闭环 | 需 admin create user + role assignment | P1 |
| 个人注册 | 基本可用 | /auth/register | 缺状态机测试 | P1 |
| 注册审核 | 基本可用 | /admin/users/{id}/approve | 缺 reject/resubmit/disable/enable | P1/P2 |
| 机构概况/关于我们 | 内容承载 | Page/SiteSetting | 缺结构化 blocks 校验 | P1 |
| 新闻动态 | 基本可用 | Article routes/pages | 缺测试、删除/预览/附件展示 | P1 |
| 成功案例 | 基本可用 | Case routes/pages | 经济效益字段弱，关联研究所弱 | P1 |
| 领导团队 | 基本可用 | Leader model/routes | 图片 URL 解析与展示需核查 | P1 |

## 4. V2 差距矩阵

| 模块 | 当前状态 | 缺口 | 建议阶段 |
|---|---|---|---|
| 研究所 | CMS 内容管理 | 团队/成果/专利/论文实体弱 | P4 |
| 成果孵化 | 静态展示 | 无项目孵化业务流 | P4/P5 |
| 共性平台 | 静态展示 | 无平台实体列表/详情 | P4 |
| 人才招聘 | 静态展示 | 无职位/简历投递闭环 | P5 |
| 专家库/专家服务 | 缺失 | 无专家模型/预约状态机 | P5 |
| 活动报名/签到 | 缺失 | 无活动、报名、签到模型 | P5 |
| 在线咨询 | 轻量闭环 | 后台菜单/状态流不足 | P2/P5 |
| 文档下载 | 接口外壳 | 无下载门禁/前台资料库页不足 | P2/P4 |
| 全站搜索 | 缺失 | 无统一 search API | P5 |
| 统计/推荐 | 占位 | 无埋点、浏览量、推荐逻辑 | P5 |
| 第三方系统对接 | 占位/本地外链 | 不能作为生产集成 | P5 |

## 5. 生产验收缺口

| 类别 | 当前状态 | 缺口 | 建议阶段 |
|---|---|---|---|
| Docker | 有 compose 基线 | 未完整验收 | P3 |
| Kubernetes | 缺失 | 无 manifests/Helm | P3 或后置 |
| HTTPS | 占位配置 | 无证书/域名验收 | P3 |
| 性能 | 缺失 | 无 100 并发压测 | P3 |
| 安全扫描 | 缺失 | 无 bandit/semgrep/trivy/gitleaks 报告 | P3 |
| 测试报告 | 缺失 | 无自动化测试体系 | P1-P3 |
| API 合约 | 部分存在 | 文档与代码不一致 | P0/P1 |
| 迁移体系 | 缺失 | create_all + 临时 ALTER | P2/P3 |

## 6. Achievement 可复用边界

| 能力 | Portal 是否应复用 | 方式 |
|---|---|---|
| API 合约 | 是 | route map、统一响应、错误码、smoke |
| RBAC | 是 | 简化角色-权限矩阵 |
| 注册审核 | 是 | pending/approved/rejected/disabled 状态机 |
| 邮箱密码重置 | 是 | 复用 Achievement hashed token、expiry、consumed/revoked、email provider、full-link UAT 设计 |
| 文件安全 | 是 | 下载门禁、scan_status、审计 |
| 审计日志 | 是 | 统一事件类型和覆盖范围 |
| 本地验收 | 是 | smoke、release readiness、secret scan |
| S3/SSO/SMS | 后置 | 先保留 provider-ready 边界 |
