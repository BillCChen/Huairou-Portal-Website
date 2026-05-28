# Portal P1 Password Reset Reuse Map

## 1. Source Reference

Achievement-Transformation password reset implementation was audited as the reference design.

| Area | Achievement Evidence | Portal Current State | Reuse Decision |
|---|---|---|---|
| Backend request route | `backend/app/api/v1/auth.py` exposes `POST /api/v1/auth/password-reset/request` | missing; Portal only has SMS-code `/api/v1/auth/reset-password` | reuse route semantics and safe response behavior |
| Backend confirm route | `backend/app/api/v1/auth.py` exposes `POST /api/v1/auth/password-reset/confirm` | missing | reuse confirm semantics with Portal response envelope |
| Token model | `backend/app/models/auth.py` defines `PasswordResetToken`; migration `backend/migrations/versions/20260528_0008_auth_channel_foundation.py` creates `password_reset_tokens` | missing | reuse schema concept, adapted to Portal models |
| Token hash | `backend/app/services/auth_channels.py` stores `hash_secret(token)` in `token_hash` | missing | required |
| Expiry | `PasswordResetToken.expires_at`; `confirm_password_reset` expires stale tokens | missing | required |
| Consumed state | `PasswordResetToken.status` supports `active`, `consumed`, `expired`, `revoked`; confirm marks consumed | missing | required |
| Email provider | `backend/app/services/email_delivery.py`; `scripts/run_email_delivery_validation.sh` | missing | reuse provider abstraction pattern, not direct code copy |
| Frontend route | `frontend/src/router/index.ts` defines `/password-reset` and `/password-reset/confirm`; `frontend/src/services/auth.ts` calls request/confirm APIs | Portal has `/forgot-password` SMS-code page and no confirm route | implement Portal pages with matching reset link path |
| Full-link UAT | `docs/PASSWORD_RESET_FULL_LINK_UAT.md` | missing | reuse process and redaction rules |
| Tests | `backend/tests/test_auth_channels.py`, `backend/tests/test_config_guardrails.py` | missing focused reset tests | port minimal backend tests and add frontend build/typecheck coverage |

## 2. Evidence Chain

| Evidence Item | Audited Result |
|---|---|
| backend route paths | `/api/v1/auth/password-reset/request`, `/api/v1/auth/password-reset/confirm` |
| frontend route paths | `/password-reset`, `/password-reset/confirm` |
| model/table name | `PasswordResetToken`, `password_reset_tokens` |
| token storage | hash only through `token_hash`; plaintext token is delivery-channel only |
| expiry field | `expires_at` |
| consumed/reuse protection | `status=consumed` after success; replay returns invalid token response |
| email provider abstraction | `disabled`, `dev_outbox`, and `smtp` provider boundaries |
| public frontend base URL | `AT_PUBLIC_FRONTEND_BASE_URL` is used to build `/password-reset/confirm?token=...` |
| SMTP acceptance document | `docs/ALIYUN_DIRECT_MAIL_SMTP_ACCEPTANCE.md` |
| full-link UAT document | `docs/PASSWORD_RESET_FULL_LINK_UAT.md` |
| test coverage | request safety, token hashing, password rotation, replay rejection, expiry, account-state blocking, rate limiting, SMTP failure sanitization, monitoring redaction |
| can copy code directly? | no |
| can reuse design? | yes |

## 3. Reuse Boundary Decision

| Route | Applicability | Benefit | Cost / Failure Mode | Decision |
|---|---|---|---|---|
| Directly copy Achievement code | Low | Fastest if frameworks and models matched | Portal has a different package shape, current SMS reset endpoint, response conventions, seed model, and no migration framework parity yet | Not selected |
| Adapt Achievement design and selected helper patterns | High | Preserves proven token state machine, provider boundary, tests, and UAT process while fitting Portal | Requires careful schema/API adaptation and focused tests | Selected |
| Rebuild password reset from scratch | Low | Maximum local freedom | High chance of missing enumeration, replay, expiry, redaction, or UAT lessons already solved in Achievement | Not selected |

The selected route is to reuse the Achievement state machine, security requirements, test cases, and acceptance runbook while adapting code to Portal's current FastAPI routes, SQLAlchemy models, Nuxt pages, and validation gates.

## 4. Required Portal Backend Work

- Add password reset token persistence.
- Add request endpoint.
- Add confirm endpoint.
- Add email notification service or provider wrapper.
- Add config for public frontend base URL and SMTP/dev provider.
- Add audit events.
- Add tests.

## 5. Required Portal Frontend Work

- Add forgot password page.
- Add reset confirm page at `/password-reset/confirm?token=...`.
- Add login page link to forgot password.
- Do not expose SMS login as V1 capability.

## 6. Security Requirements

- No email enumeration.
- No raw token persistence.
- No token logging.
- No full reset link committed to docs.
- Token single-use.
- Expiry enforced.
- Password policy enforced.
- Old password invalidated by password hash update.

## 7. UAT Requirements

- Local mock/dev email test first.
- Optional real SMTP UAT later.
- Full-link UAT must not commit token/full link.
- Recipient email must be masked in docs.
