# Portal P1 Contract Closure Plan

## 1. Scope

P1 closes Portal V1 contract functionality and does not implement V2 business systems.

P1 uses the P0 baseline as an admission gate and narrows the account scope according to the current stakeholder decision: SMS verification login is excluded from V1 acceptance, while email-based password reset is required.

## 2. Stage Plan

| Stage | Goal | Code? | Notes |
|---|---|---:|---|
| P1-A | V1 auth scope revision + Achievement reuse audit | docs only | current stage |
| P1-B | Email password reset backend | yes | model/routes/provider/tests completed; frontend remains P1-C |
| P1-C | Email password reset frontend | yes | forgot/reset confirm pages completed; full-link UAT remains later |
| P1-D | User approval/institution user/role closure | yes | reject/disable/enable/create/assign |
| P1-E | V1 content CMS acceptance closure | yes | homepage/news/cases/about/leaders |
| P1-F | V1 smoke tests and acceptance docs | scripts/docs | public/auth/admin/permission smoke |
| P1-G | P1 merge readiness | docs/scripts | final validation and tag |

## 3. Excluded From P1

- SMS verification login.
- Real SMS provider.
- SSO.
- V2 talent/expert/event/recommendation/search/statistics systems.
- Full K8s production hardening.
- 100-concurrency performance report.
- Full external system integration.

## 4. Validation Baseline

P1 must preserve P0 gates:

- `./scripts/portal_min_acceptance.sh`
- `pnpm check:web`
- `pnpm build:web`
- `pnpm check:admin`
- `pnpm build:admin`
- backend compileall
- `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_local_public_api_smoke.sh`

For P1-A, only non-service checks are required. The local public API smoke remains a later validation gate because it starts an API runtime.

## 5. Decision Points

| Decision | Current Direction | Reason |
|---|---|---|
| SMS login in V1 | Exclude | Stakeholder decision removes SMS verification login from V1 acceptance. |
| Password reset pattern | Adapt Achievement design | Achievement already validated one-time hashed tokens, email delivery, and full-link UAT. |
| P1 first code stage | Backend before frontend | Token persistence, email provider, and API semantics must be stable before UI wiring. |
| Real SMTP for Portal | Later UAT only | P1-B/P1-C can use mock/dev provider first; real SMTP must not be a prerequisite for local tests. |

## 6. P1-B Completion Boundary

P1-B implements the backend email password reset foundation by adapting the Achievement design to Portal's current FastAPI and create_all baseline.

Completed:

- `PasswordResetToken` persistence model.
- `POST /api/v1/auth/password-reset/request`.
- `POST /api/v1/auth/password-reset/confirm`.
- SHA-256 token hash storage.
- Expiry and consumed-token rejection.
- Generic request response for existing and missing accounts.
- Dev outbox / disabled provider boundary with no real SMTP send.
- Backend smoke coverage in `scripts/smoke_password_reset_backend.sh`.

Not included:

- Frontend forgot/reset pages.
- Real SMTP UAT.
- SMS verification login acceptance.
- Formal database migration framework.

## 7. P1-C Completion Boundary

P1-C implements the frontend email password reset flow against the P1-B backend endpoints.

Completed:

- `/forgot-password` email-or-username request page.
- `/password-reset/confirm?token=...` reset confirm page.
- Login-page forgot-password entry from the password login path.
- Frontend API client methods for request and confirm.
- Safe generic request success messaging.
- Generic invalid-or-expired reset-link messaging.
- No token display, token logging, browser token persistence, real SMTP send, or SMS provider work.

Not included:

- Backend password reset logic changes.
- Real SMTP UAT.
- SMS verification login acceptance.
- Full-link UAT.

## 8. Next Recommended Stage

P1-D: close user approval, rejection, disable/enable, institution-user creation, and role assignment gaps.
