# Portal P1 Email Password Reset Backend

## 1. Scope

P1-B implements the backend foundation for email-based password reset. It adds token persistence, request/confirm API endpoints, a local email notification provider boundary, and backend smoke coverage.

This stage does not implement frontend forgot/reset pages, does not send real email, does not connect a real SMTP provider, and does not treat SMS verification login as a V1 requirement.

## 2. Backend Contract

| Item | Result |
|---|---|
| Request endpoint | `POST /api/v1/auth/password-reset/request` |
| Confirm endpoint | `POST /api/v1/auth/password-reset/confirm` |
| Existing SMS reset route | Preserved as current-code/test-path at `POST /api/v1/auth/reset-password` |
| Token table | `password_reset_tokens` |
| Token storage | `token_hash` only, generated with SHA-256 from a one-time raw token |
| Token delivery | Raw token is passed only to the configured notification provider boundary |
| Link path | `/password-reset/confirm?token=...` |
| Expiry | `PASSWORD_RESET_TOKEN_TTL_MINUTES`, default 60 minutes |
| Consumption | `consumed_at` is set after successful reset or provider-disabled/config-failure invalidation |
| Generic request response | Existing and missing accounts receive the same safe response |
| Account status | Only active users with email can receive a usable reset token |

## 3. Provider Boundary

The backend supports a minimal provider boundary through `EMAIL_PROVIDER`.

Portal's current config style does not use the Achievement `AT_` prefix. The P1-B Portal keys are `PASSWORD_RESET_ENABLED`, `PASSWORD_RESET_TOKEN_TTL_MINUTES`, `PASSWORD_RESET_DEV_OUTBOX_DIR`, `PUBLIC_FRONTEND_BASE_URL`, and `EMAIL_PROVIDER`.

| Provider | Behavior |
|---|---|
| `dev_outbox` | Writes a local reset email into an ignored runtime outbox. This is for local tests only. |
| `disabled` | Does not send. The external response remains generic and any generated token is consumed. |
| Other values | Treated as not configured. The external response remains generic. |

P1-B intentionally does not implement real SMTP. A future Portal SMTP UAT stage should follow the Achievement full-link UAT pattern and must inject secrets through environment variables or a production secret mechanism.

## 4. Security Behavior

- The API response never returns the reset token.
- The database stores only `token_hash`, never the raw token.
- Audit records store masked recipient metadata and provider status, not raw tokens or full reset links.
- Expired, consumed, invalid, and account-unavailable tokens are rejected.
- A successful confirm updates `User.password_hash`, sets `consumed_at`, and invalidates other active reset tokens for the same user.
- Old password login fails after reset; new password login succeeds.
- Pending, disabled, or missing-email users do not receive a usable reset token.

## 5. Test and Smoke Coverage

`scripts/smoke_password_reset_backend.sh` starts an isolated local API using `.runtime-logs/password-reset-backend-smoke/`, dev outbox, runtime SQLite, and seed users. It verifies:

- unknown user request returns the same generic response as an existing user;
- existing user request writes one outbox message and stores only a 64-character token hash;
- valid confirm changes the password;
- old password is rejected and new password is accepted;
- consumed token replay is rejected;
- expired token is rejected;
- auth audit records exist and do not contain raw reset tokens.

The script does not send real email and does not read SMTP secrets.

## 6. Migration Note

Portal currently uses `Base.metadata.create_all` and has no Alembic migration framework. P1-B follows that baseline by adding the SQLAlchemy model only. Formal migration management remains a later production hardening item.

## 7. Remaining Work

- P1-C: implement frontend forgot password and `/password-reset/confirm` pages.
- Add a real email provider UAT only after frontend reset pages exist.
- Add formal migrations when the Portal database lifecycle is hardened.
- Keep SMS verification login excluded from V1 acceptance.
