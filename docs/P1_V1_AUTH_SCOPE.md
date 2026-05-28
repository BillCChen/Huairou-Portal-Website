# Portal P1 V1 Auth Scope

## 1. Decision Summary

- SMS verification login is explicitly excluded from Portal V1.
- Email-based password reset is required for Portal V1.
- Password reset should reuse the Achievement-Transformation design where appropriate.
- Existing SMS code, if present, must not be claimed as V1 acceptance.

The source contract still mentions SMS verification login in the V1 login path, but the current stakeholder decision supersedes that item for Portal V1 acceptance. The P1 implementation plan must therefore close email password reset and user-management gaps without adding a real SMS provider or SMS login smoke.

## 2. Final V1 Auth Capability Matrix

| Capability | V1 Status | Acceptance Requirement | Notes |
|---|---|---|---|
| Password login | Required | active user can log in; invalid/disabled/pending users rejected | Existing API and UI are present, but P1 still needs focused auth smoke and negative cases. |
| SMS verification login | Excluded | not part of V1 acceptance | Existing `/api/v1/auth/login/sms` and SMS tab are current-code/test-path only; no real SMS provider in V1. |
| Email password reset | Required | request email, open link, set new password, old password rejected, token reuse rejected | Reuse Achievement pattern; current Portal reset is SMS-code based and does not satisfy V1. |
| Personal registration | Required | new personal user enters pending review | Existing registration creates pending users. |
| Admin approval | Required | approve/reject pending users | Current admin UI/API supports approve only; reject remains P1 work. |
| Disable/enable user | Required | disabled users cannot log in | Current login checks user status, but admin disable/enable operations are missing. |
| Admin-created institution user | Required | admin can create assigned institution account | Missing. |
| Role assignment | Required minimal | admin can assign minimal roles | Role model and seed data exist; admin assignment flow is missing. |
| Audit/login logs | Required minimal | key auth/user events recorded | Login logs and audit table exist; auth/user coverage is partial. |

## 3. Portal Current Auth/User Gap Audit

| Item | Current State | Evidence | P1 Interpretation |
|---|---|---|---|
| password login API/page | exists | `apps/api-server/app/api/routes.py`, `apps/web-portal/pages/login.vue` | Keep as V1 capability and add smoke coverage. |
| SMS login API/page | exists | `/api/v1/auth/login/sms`, SMS tab in `apps/web-portal/pages/login.vue` | legacy/current-code, not V1 requirement. |
| password reset API | partial | `/api/v1/auth/reset-password` accepts mobile, SMS code, and new password | Does not meet email reset requirement. |
| forgot-password frontend page | exists | `apps/web-portal/pages/forgot-password.vue` | Current page is SMS-code reset, not email reset. |
| password-reset confirm frontend page | missing | no `/password-reset/confirm` Nuxt page found | Required in P1. |
| email field in user model | exists | `User.email` in `apps/api-server/app/db/models.py` | May need uniqueness or lookup policy in P1-B. |
| password reset token model/table | missing | no `PasswordResetToken` model/table in Portal | Required in P1-B. |
| SMTP/email provider config | missing | `apps/api-server/app/core/config.py` only has `sms_test_code` | Required in P1-B. |
| personal registration | exists/partial | `/api/v1/auth/register`, `RegistrationApplication` | Pending default exists; needs tests and review-state closure. |
| approval | approve only | `/api/v1/admin/users/{user_id}/approve`, `UsersView.vue` approve action | Reject remains P1 work. |
| user disable/enable | missing | no admin disable/enable route found | Required in P1-D. |
| admin-created institution user | missing | no admin create-user route found | Required in P1-D. |
| role assignment | missing/partial | `Role` model and seed data exist, but no admin assignment API/UI found | Required minimal P1-D closure. |
| audit logs for auth/user events | partial | `AuditLog` exists; approve writes audit; login/reset/register coverage is incomplete | Extend only for P1 auth/user events. |
| login logs | exists/partial | `LoginLog` writes password success/failure and SMS success | Add smoke and ensure negative cases are covered. |

## 4. SMS Login Handling

- Do not implement real SMS provider.
- Do not add SMS V1 smoke.
- If SMS UI/API exists, mark as legacy/test-path/non-acceptance.
- Prefer hiding or disabling SMS login UI in a later P1 task unless there is a stakeholder reason to keep it visible.
- Do not remove backend SMS test code in this stage.

## 5. Email Password Reset Required Behavior

- Generic reset request response to prevent account enumeration.
- One-time token.
- Token hash stored server-side, not raw token.
- Expiry timestamp.
- Consumed/reused token rejected.
- Reset link path should be `/password-reset/confirm?token=...`.
- Old password rejected after successful reset.
- New password accepted.
- Events recorded in audit/login logs where appropriate.
- SMTP provider should be configurable; local tests may use mock/dev mode.
- Production SMTP UAT should follow Achievement full-link UAT pattern.

## 6. Non-goals

- SSO.
- Real SMS.
- K8s.
- 100-concurrency performance test.
- Full security scan.
- V2 talent/expert/event/search/recommendation systems.
