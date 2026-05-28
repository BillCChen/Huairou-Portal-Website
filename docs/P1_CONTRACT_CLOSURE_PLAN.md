# Portal P1 Contract Closure Plan

## 1. Scope

P1 closes Portal V1 contract functionality and does not implement V2 business systems.

P1 uses the P0 baseline as an admission gate and narrows the account scope according to the current stakeholder decision: SMS verification login is excluded from V1 acceptance, while email-based password reset is required.

## 2. Stage Plan

| Stage | Goal | Code? | Notes |
|---|---|---:|---|
| P1-A | V1 auth scope revision + Achievement reuse audit | docs only | current stage |
| P1-B | Email password reset backend | yes | model/routes/provider/tests |
| P1-C | Email password reset frontend | yes | forgot/reset confirm pages |
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

## 6. Next Recommended Stage

P1-B: implement email password reset backend by adapting Achievement design.
