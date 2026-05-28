# Portal P1 Email Password Reset Frontend

## 1. Scope

P1-C implements the Portal web frontend for the P1-B email password reset backend.

This stage adds the user-facing forgot-password request page, the reset-confirm route, and the login-page entry. It does not change backend password reset logic, does not send real email, does not use real SMTP secrets, and does not make SMS verification login part of Portal V1.

## 2. Frontend Routes

| Route | Purpose | Status |
|---|---|---|
| `/forgot-password` | Submit an email or username to request a reset email | Implemented |
| `/password-reset/confirm?token=...` | Submit a new password with the one-time reset token | Implemented |
| `/login` | Provides the forgot-password entry from the password login path | Updated |

The reset token is read from the URL query only for submission to the backend. The page does not display the token, does not write it to browser storage, and does not log it.

## 3. API Client Wiring

The web portal uses the P1-B endpoints:

| Method | API Path | Client Method |
|---|---|---|
| POST | `/api/v1/auth/password-reset/request` | `requestPasswordReset(emailOrUsername)` |
| POST | `/api/v1/auth/password-reset/confirm` | `confirmPasswordReset(token, newPassword)` |

Request payloads use `email_or_username`, `token`, and `new_password` to match the backend schema. Responses continue through the existing Portal API envelope and `getPortalErrorMessage()` fallback helper.

## 4. UX Behavior

| Case | Behavior |
|---|---|
| Request submitted | Shows a generic success message that does not reveal whether the account exists. |
| Missing identifier | Shows local validation asking for email or username. |
| Missing token | Blocks submit and shows an invalid-link message. |
| Invalid, expired, or reused token | Shows a generic invalid-or-expired link message. |
| Successful reset | Shows success and returns the user to `/login`. |

The confirm page validates non-empty passwords, matches confirmation input, and keeps the frontend minimum password length aligned with the current backend `min_length=8` schema.

## 5. SMS Boundary

SMS verification login remains excluded from Portal V1. P1-C does not add SMS provider configuration, does not send SMS codes, and does not make SMS login part of V1 acceptance.

The existing current-code SMS login path is not expanded in this stage.

## 6. Remaining Work

- Run a local full-link smoke with the backend `dev_outbox` provider.
- Add a later optional real SMTP UAT only after the Portal frontend URL and provider configuration are approved.
- Keep full reset links, reset tokens, recipient emails, and SMTP secrets out of committed docs and logs.
