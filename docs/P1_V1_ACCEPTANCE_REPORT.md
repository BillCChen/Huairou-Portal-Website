# Portal P1 V1 Acceptance Report

## 1. Baseline

- Branch: `codex/portal-p1-contract-closure`
- P0 tag: `v1.0-portal-p0-baseline-rc1`
- P1 stages completed: P1-A, P1-B, P1-C, P1-D, P1-E, P1-F.
- Latest P1-E commit before this report: `af8f2a814c26538ba1e9f0936bc866e0e6b6c676`.

## 2. Objective

P1-F consolidates Portal V1 acceptance evidence. It does not add V2 business systems, does not send email, does not use real secrets, and does not change SMS, password reset, user lifecycle, or content CMS business logic.

## 3. Acceptance Result Overview

| Category | Result | Evidence |
|---|---|---|
| Repository hygiene | Passed in acceptance runner | `scripts/run_v1_acceptance.sh`, forbidden artifact scan, basic secret scan |
| Public API readiness | Passed in isolated runtime smoke | `scripts/run_local_public_api_smoke.sh` |
| V1 content CMS | Passed in isolated runtime smoke | `scripts/smoke_v1_content_backend.sh` |
| Email password reset backend | Passed in isolated runtime smoke | `scripts/smoke_password_reset_backend.sh` |
| User lifecycle | Passed in isolated runtime smoke | `scripts/smoke_user_lifecycle_backend.sh` |
| Auth and permission boundary | Passed in isolated runtime smoke | `scripts/smoke_auth_permission_backend.sh` |
| Frontend web static gates | Passed | `pnpm check:web`, `pnpm build:web` |
| Admin console static gates | Passed | `pnpm check:admin`, `pnpm build:admin` |
| Backend static gate | Passed | `python3 -m compileall app` |

## 4. Functional Acceptance Matrix

| Capability | Result | Evidence |
|---|---|---|
| Homepage entry, profile, stats, news, cases | Closed for V1 | `GET /api/v1/public/home`, `apps/web-portal/pages/index.vue`, `scripts/smoke_v1_content_backend.sh` |
| News list, category, search, detail | Closed for V1 | Public news APIs, news pages, content smoke |
| Successful case list/detail with partner and benefits | Closed for V1 | Public case APIs, case pages, content smoke |
| About us, mission, vision, strategy, governance, contact, email | Closed for V1 | Public page/settings APIs, about page, content smoke |
| Leader team | Closed for V1 | Public leaders API, leader admin surface, content smoke |
| Banner, categories, tags, site settings | Closed for V1 | Public/admin APIs and content smoke |
| Password login and current user | Closed for V1 baseline | User lifecycle and auth/permission smoke |
| Personal registration and review | Closed for V1 | User lifecycle smoke |
| Approve, reject, disable, enable | Closed for V1 | User lifecycle smoke and admin user endpoints |
| Admin-created institution user | Closed for V1 | User lifecycle smoke |
| Role assignment | Closed for V1 | User lifecycle smoke and auth/permission smoke |
| Email password reset | Backend/frontend foundation closed | Password reset backend smoke, P1-C frontend pages |
| SMS verification login | Excluded from V1 | P1-A scope decision; no V1 smoke counted |

## 5. Automated Validation

Primary command:

```bash
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_v1_acceptance.sh
```

The runner covers:

- `scripts/portal_min_acceptance.sh` when the worktree is clean, or the same minimal component checks during pre-commit validation.
- `pnpm check:web`.
- `pnpm build:web`.
- `pnpm check:admin`.
- `pnpm build:admin`.
- backend compileall.
- local public API smoke.
- password reset backend smoke.
- user lifecycle smoke.
- auth/permission smoke.
- V1 content smoke.
- `git diff --check`.
- forbidden artifact scan.
- basic secret scan.

## 6. Known Warnings

- Vue language plugin warning during `pnpm check:web`; command exits 0.
- Nuxt sourcemap warning during `pnpm build:web`; command exits 0.
- Vite chunk-size warning during `pnpm build:admin`; command exits 0.

## 7. Explicitly Unfinished

- V2 talent, expert, event, recommendation, full-site search, and statistics systems.
- Real SMTP full-link UAT.
- Real SMS provider and SMS login acceptance.
- SSO.
- Production security scan report.
- Production performance test report.
- Kubernetes manifests.
- Public file download and signed image delivery hardening.
- Formal migration framework.

## 8. Security Notes

- No real secrets, production passwords, tokens, or full reset links are committed.
- Runtime SQLite databases, logs, uploads, virtual environments, and generated build outputs remain ignored artifacts.
- Password reset tokens are stored as hashes by the P1-B backend and are not printed by smoke scripts.
- Smoke scripts use local demo credentials only inside isolated runtime requests and do not print raw passwords.
- SMS verification login is not counted as V1 acceptance evidence.

## 9. P1-G Merge Readiness Validation

P1-G reran the complete V1 acceptance chain and merge-readiness checks before RC tagging.

| Check | Result | Evidence |
|---|---|---|
| V1 acceptance runner | PASS | `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_v1_acceptance.sh` |
| Route map stability | PASS | `python3 scripts/extract_api_routes.py` regenerated 68 routes without a worktree diff. |
| Forbidden artifact scan | PASS | `./scripts/check_forbidden_artifacts.sh` |
| Basic secret scan | PASS | `./scripts/check_secrets_basic.sh` |
| Whitespace diff check | PASS | `git diff --check` |
| Merge-tree conflict check | PASS | `main` is an ancestor of the P1 branch and no merge-tree conflict marker was reported. |
| Runtime cleanup | PASS | No listener remained on port `18200`. |

P1-G does not push, does not claim production release readiness, and does not implement V2 business systems.

## 10. P2-A Password Reset Full-Link UAT Addendum

P2-A validates the real SMTP password reset full-link path after the P1 V1 acceptance baseline. It does not change the P1 acceptance matrix, SMS exclusion, password reset token semantics, user lifecycle behavior, V1 content CMS behavior, or V2 scope.

| Check | Result | Evidence |
|---|---|---|
| SMTP provider support | PASS | `EMAIL_PROVIDER=smtp` with runtime-injected SMTP credentials; default remains `dev_outbox`. |
| SMTP config smoke | PASS | `scripts/smoke_password_reset_smtp_config.sh` covers disabled and fail-closed SMTP misconfiguration paths without real email. |
| Real reset email delivery | PASS | One email delivered to a masked controlled recipient through Alibaba Cloud Direct Mail SMTP. |
| HTTPS reset page | PASS | Temporary tunnel opened `/password-reset/confirm?token=...` on the Portal frontend. |
| Password rotation | PASS | Old password rejected and new password accepted through the login API. |
| Token reuse rejection | PASS | User-confirmed same-link reuse rejection. |
| Secret handling | PASS | No SMTP password, reset token, full reset link, full recipient email, password, or login token is committed. |

The P2-A UAT is documented in `docs/P2_PASSWORD_RESET_FULL_LINK_UAT.md`. Production-domain HTTPS, formal SMTP operations, performance testing, external security scanning, Kubernetes validation, and V2 systems remain outside this addendum.
