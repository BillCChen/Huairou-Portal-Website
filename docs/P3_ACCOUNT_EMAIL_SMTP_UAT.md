# Portal P3 Account Email SMTP UAT

## 1. 范围

P3-B2 验证 P3-B 账号邮件通知可以通过真实 SMTP 投递。本阶段只做本地 SMTP UAT，不 push、不部署服务器、不修改 SMS/SSO、不修改部署配置。

## 2. 前置条件

- P3-B account notifications completed locally.
- SMTP provider configured through runtime env.
- SMTP password stored outside repo.
- Recipient controlled by user.
- Runtime database is an ignored local SQLite file under `.runtime-logs/`.

## 3. SMTP Provider

- host: smtpdm.aliyun.com
- port: 465
- TLS: implicit SSL/TLS
- sender: no-reply@notify.inside-chen.top
- password source: outside repo
- password committed: no

## 4. UAT Recipient

- recipient: 20***@stu.pku.edu.cn
- full recipient committed: no

## 5. Events Verified

| 事件 | 是否发送真实邮件 | 是否收到 | 备注 |
|---|---|---|---|
| 注册提交 | yes | yes |  |
| 审核通过 | yes | yes |  |
| 审核拒绝 | yes | yes | reason included |
| 管理员创建用户 | yes | yes | no initial password reported |
| 密码修改成功 | yes | yes | no anomaly reported |

## 6. Execution Notes

The first SMTP UAT script run sent the first three event emails, then stopped before the admin-created event because the local runtime database already had the same recipient email on an earlier test user and the admin-created user path enforces email uniqueness.

The script was adjusted to trigger the admin-created notification before the registration flow in a fresh isolated runtime database. The second run completed all five events:

- admin-created user
- registration submitted
- registration approved
- registration rejected
- password changed

Total real SMTP messages sent during this UAT: 8.

Final complete event set: 5/5 received.

## 7. Security Checks

- admin-created user email contains no initial password: yes, by user mailbox check
- rejection email contains formatted reason: yes, by user mailbox check
- password-changed email contains no reported token/reset-link anomaly: yes, by user mailbox check
- no SMTP password committed
- no full email committed
- no token committed
- no full reset link committed
- no full message body committed

## 8. Results

User mailbox feedback:

- All five required event emails were received.
- The rejection reason was received.
- No abnormal content was found by the user.

The UAT report records only yes/no and masked recipient information. It does not include the full message bodies.

## 9. Remaining Work

- P3-B2 is local SMTP UAT only.
- Server deployment of P3-B notifications is a later stage.
- HTML email templates are not implemented.
- SMS remains excluded.
