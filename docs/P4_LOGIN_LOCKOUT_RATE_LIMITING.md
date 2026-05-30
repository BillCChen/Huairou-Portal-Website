# P4-B2 Login Lockout and Rate Limiting

## 1. Scope

P4-B2 aligns Portal and Achievement login abuse protection. Portal adds durable login lockouts, notification controls, administrator unlock, audit evidence, and local smoke coverage.

This stage does not add CAPTCHA, SMS verification, device fingerprinting, GeoIP, WAF rules, machine-learning risk scoring, file-security changes, ClamAV changes, deployment changes, main-branch merge, or server rollout.

## 2. Policy

| Dimension | Window | Threshold | Lock Duration | Result |
|---|---:|---:|---:|---|
| account + IP | 24 hours | 10 failed attempts | 24 hours | That account identifier is restricted from that IP. |
| IP global | 24 hours | 30 failed attempts across identifiers | 24 hours | That IP is restricted for all login attempts. |

The IP global rule has higher operational priority because it detects credential stuffing across multiple accounts.

## 3. Configuration

- `LOGIN_LOCKOUT_ENABLED=true`
- `LOGIN_LOCKOUT_ACCOUNT_IP_FAILURES=10`
- `LOGIN_LOCKOUT_IP_FAILURES=30`
- `LOGIN_LOCKOUT_WINDOW_HOURS=24`
- `LOGIN_LOCKOUT_DURATION_HOURS=24`
- `LOGIN_LOCKOUT_EMAIL_COOLDOWN_HOURS=24`

These are non-secret runtime values. They do not replace `ACCESS_TOKEN_EXPIRE_MINUTES`.

## 4. Email Notification Rules

- `account_ip` lockout sends one login-protection email when the account exists and has an email address.
- Missing accounts never receive lockout email.
- IP global lockout never sends mass email to related accounts.
- A single lockout record sends at most one email.
- The cooldown avoids repeated lockout mail bursts for the same account.
- Local validation uses `dev_outbox` or `disabled`; P4-B2 does not run real SMTP UAT.

The email body must not include passwords, access tokens, reset tokens, reset links, internal lockout identifiers, or detailed attack rules.

## 5. Administrator Unlock

Administrators can list login lockouts and unlock them from the admin audit area.

Unlock requires a trimmed reason between 20 and 1000 characters. Unlock writes `AuditLog` with the acting administrator, IP/User-Agent context, lockout type, and reason. Unlock does not automatically send email in P4-B2.

## 6. Response Boundary

Login failures, account+IP lockout, IP global lockout, missing accounts, pending accounts, rejected accounts, and disabled accounts must not reveal whether a username exists.

The frontend displays a generic message:

`登录失败次数过多或暂时受限，请稍后重试，或联系管理员。`

The system must not log failed passwords, tokens, reset links, or raw secrets.

## 7. Audit

Portal records:

- failed login attempts
- `account_ip` lockout creation
- IP global lockout creation
- lockout email send attempt/result when applicable
- active lockout login rejection
- administrator unlock with reason

Audit records include IP address and User-Agent through the P3-D request-context helper.

## 8. Smoke

`scripts/smoke_login_lockout_backend.sh` validates:

- existing account reaches account+IP lockout after 10 failed attempts
- the next login attempt is rejected while locked
- one dev-outbox login-protection email is created
- missing account failures do not send email
- one IP reaches global lockout after 30 cross-identifier failures
- IP global lockout does not mass-email
- short unlock reason is rejected
- valid unlock reason succeeds
- correct login succeeds after unlock
- smoke output does not print password or token values

Test IPs:

- `203.0.113.60`
- `203.0.113.61`

## 9. Remaining Work

- P4-B3 or later may evaluate CAPTCHA, WAF, device fingerprinting, GeoIP, or external risk signals.
- P4-C1 covers account notification parity outside login lockout mail with local `dev_outbox` / `disabled` validation only.
- P4-C2 remains the separate real SMTP UAT stage.
- Server deployment and real SMTP behavior require a separately authorized rollout.
