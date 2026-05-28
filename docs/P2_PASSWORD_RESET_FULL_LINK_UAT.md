# Portal P2 Password Reset Full-Link UAT

## 1. Scope

This document records the Portal P2-A password reset full-link UAT with real SMTP email delivery, a temporary HTTPS tunnel, and masked evidence only.

The UAT covers:

- password reset request;
- real SMTP email delivery;
- reset link opening on the HTTPS frontend;
- new password submission;
- old password rejection;
- new password login acceptance;
- reset token reuse rejection.

The UAT does not cover SMS login, SSO, V2 business systems, production-domain deployment, performance testing, or external security scanning.

## 2. Preconditions

- Portal P1 baseline was fast-forwarded to `main`.
- P1 password reset backend and frontend were already implemented.
- The SMTP password file was stored outside the repository.
- The UAT used an ignored runtime SQLite database and ignored runtime uploads directory.
- The reset link path was confirmed as `/password-reset/confirm?token=...`.
- The UAT user was active in the local runtime database.

## 3. Environment

| Item | Value |
|---|---|
| Backend | `127.0.0.1:18300` |
| Frontend | `127.0.0.1:15373` |
| Same-origin proxy | `127.0.0.1:18380` |
| Tunnel | `https://lanka-plates-parameters-vista.trycloudflare.com` |
| Database | Ignored runtime SQLite |
| Uploads | Ignored runtime directory |

The tunnel was temporary UAT infrastructure and is not a production deployment endpoint.

## 4. SMTP Provider

| Item | Value |
|---|---|
| Provider mode | `smtp` |
| Host | `smtpdm.aliyun.com` |
| Port | `465` |
| TLS mode | Implicit SSL/TLS |
| Sender | `no-reply@notify.inside-chen.top` |
| Password source | Outside repository |
| Password committed | No |

Portal keeps `dev_outbox` as the default local provider mode. Real SMTP is enabled only through runtime environment variables.

## 5. UAT Test Account

| Item | Value |
|---|---|
| Username | `portal_uat_email_reset` |
| Recipient | `20***@stu.pku.edu.cn` |
| Status | Active |
| Full email committed | No |
| Password committed | No |

The old and new passwords were used only for local hidden verification and were not written to committed files.

## 6. UAT Steps

1. Start backend, frontend, same-origin proxy, and Cloudflare Quick Tunnel on the P2-A UAT ports.
2. Start backend with `EMAIL_PROVIDER=smtp` and `PUBLIC_FRONTEND_BASE_URL` set to the tunnel base URL.
3. Confirm `/forgot-password` and `/password-reset/confirm?token=dummy` load through the tunnel.
4. Trigger one password reset request for the active UAT user.
5. User opens the mailbox, clicks the email reset link, and submits a new temporary password in the browser.
6. Verify the old password is rejected through the login API.
7. Verify the new password is accepted through the login API.
8. User reopens the same reset link and confirms reuse is rejected.
9. Stop only the P2-A runtime processes.

## 7. Results

| Item | Result | Notes |
|---|---|---|
| Reset link path matched | Yes | `/password-reset/confirm?token=...` |
| Backend API reachable through tunnel | Yes | Public API route returned HTTP 200 |
| Frontend reset page reachable | Yes | Reset confirm route returned HTTP 200 |
| Active UAT user available | Yes | Local runtime database only |
| Reset email delivered | Yes | Normal inbox |
| Reset link opened | Yes | User-confirmed |
| Password changed | Yes | User-confirmed |
| Old password rejected | Yes | Login API returned failure |
| New password accepted | Yes | Login API returned success |
| Token reuse rejected | Yes | User-confirmed same-link reuse rejection |
| Secrets/tokens/full links committed | No | Verified by review and scans |

Exactly one real password reset email was sent in this UAT.

## 8. Security Observations

- No SMTP password was committed.
- No reset token was committed.
- No full reset link was committed.
- No full recipient email was committed.
- No old or new password was committed.
- Login access tokens were not printed or committed.
- Runtime SQLite, logs, uploads, and virtual environments remained ignored artifacts.
- SMTP delivery failures return safe errors without secret disclosure.

## 9. Remaining Work

- Replace the temporary tunnel with a production HTTPS frontend domain before production use.
- Add a formal SMTP operations runbook if production operations require one.
- Keep production performance testing, external security scanning, and Kubernetes hardening as separate tracks.
- Keep real SMS and SSO outside this P2-A scope.

## 10. Rollback

- Set `EMAIL_PROVIDER=dev_outbox` or `EMAIL_PROVIDER=disabled`.
- Remove SMTP runtime environment variables from the target environment.
- Stop the backend, frontend, proxy, and tunnel runtime processes.
- Keep the existing token hash, expiry, and consumed-token semantics unchanged.
