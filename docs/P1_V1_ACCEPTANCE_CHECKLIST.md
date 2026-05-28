# Portal P1 V1 Acceptance Checklist

## 1. Scope

This checklist covers the Portal V1 acceptance surface consolidated in P1-F.

- SMS verification login is excluded from Portal V1 by stakeholder decision.
- Email password reset is included in Portal V1.
- V2 business systems are outside this checklist.
- Real SMTP, real SMS, SSO, production performance testing, and production security scanning are later acceptance tracks.

## 2. V1 Acceptance Matrix

| Capability | Frontend Evidence | Admin Evidence | Backend/API Evidence | Smoke Evidence | Status | Notes |
|---|---|---|---|---|---|---|
| Portal entry / homepage | `apps/web-portal/pages/index.vue` | Content managed through article, case, banner, page, and setting views | `GET /api/v1/public/home` | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Aggregates published content and safe fallbacks. |
| Institution profile | Homepage and about page display profile blocks | `SettingsView.vue`, `ListView.vue` page blocks | `SiteSetting`, `Page`, public home/settings/pages APIs | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Public file delivery remains later hardening. |
| Core statistics | Homepage stats display | Site setting maintenance | `site_settings.home_stats` in public home/settings | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Uses seeded setting data. |
| News dynamics | News list and detail pages | `ListView.vue` article form | Public news list/detail APIs | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Published-only filter is smoke-tested. |
| News categories | News list filtering | `CategoriesView.vue` category management | `GET /api/v1/public/categories?type=news` | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Category metadata appears in payloads. |
| News search | News list keyword query | Article title/summary/content maintenance | `GET /api/v1/public/news?keyword=...` | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | This is keyword filtering, not full-site search. |
| News detail | `apps/web-portal/pages/news/[slug].vue` | Article edit fields | `GET /api/v1/public/news/{slug}` | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Draft detail route is checked as hidden. |
| Successful cases | Case list and detail pages | `ListView.vue` case form | Public case list/detail APIs | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Covers list/detail payload shape. |
| Case partner / benefits | Case list and detail fields | Partner, stage, benefits, result blocks in case form | `CaseStudy.partner_name`, `benefits`, `result_blocks` | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Does not create a V2 incubator workflow. |
| About us | `apps/web-portal/pages/about.vue` | Page and setting maintenance | `GET /api/v1/public/pages/about`, settings APIs | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Blocks cover profile content. |
| Mission / vision / strategy / governance / contact / email | About page sections | `ListView.vue` page blocks and `SettingsView.vue` | Page blocks and site profile settings | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Smoke checks required block titles and contact email. |
| Leader team | About page leader area | `LeadersView.vue` | `GET /api/v1/public/leaders` | `scripts/smoke_v1_content_backend.sh` | Closed for V1 | Visible leaders are returned sorted. |
| Password login | Login page | Admin console login | `POST /api/v1/auth/login/password`, `GET /api/v1/auth/me` | `scripts/smoke_user_lifecycle_backend.sh`, `scripts/smoke_auth_permission_backend.sh` | Closed for V1 | Pending, rejected, and disabled users are rejected. |
| Personal registration | Register page | Pending user review in admin console | `POST /api/v1/auth/register` | `scripts/smoke_user_lifecycle_backend.sh` | Closed for V1 | Creates pending users. |
| Approval accepted | Admin user management | Approve action in `UsersView.vue` | `POST /api/v1/admin/users/{user_id}/approve` | `scripts/smoke_user_lifecycle_backend.sh` | Closed for V1 | Approved users can log in. |
| Approval rejected | Admin user management | Reject action in `UsersView.vue` | `POST /api/v1/admin/users/{user_id}/reject` | `scripts/smoke_user_lifecycle_backend.sh` | Closed for V1 | Rejected users cannot log in. |
| Disable / enable | Admin user management | Disable and enable actions in `UsersView.vue` | Disable/enable admin endpoints | `scripts/smoke_user_lifecycle_backend.sh` | Closed for V1 | Disabled token and login are rejected. |
| Admin-created institution user | Admin user creation form | `UsersView.vue` create dialog | `POST /api/v1/admin/users` | `scripts/smoke_user_lifecycle_backend.sh` | Closed for V1 | Initial password is never returned in API response. |
| Role assignment | Admin role control | `UsersView.vue` role assignment | `PUT /api/v1/admin/users/{user_id}/role` | `scripts/smoke_user_lifecycle_backend.sh`, `scripts/smoke_auth_permission_backend.sh` | Closed for V1 | Super-admin boundary and ordinary-user rejection are smoke-tested. |
| Email password reset | `/forgot-password`, `/password-reset/confirm?token=...` | Not applicable | Request/confirm endpoints and `PasswordResetToken` | `scripts/smoke_password_reset_backend.sh` | Backend and frontend foundation closed | Real SMTP full-link UAT is not part of P1-F. |
| SMS verification login | Existing code path only | Not accepted | `/auth/sms-send`, `/auth/login/sms` remain test-path | Not counted | Excluded | No real SMS provider or V1 smoke. |

## 3. Smoke Coverage

| Script | Coverage |
|---|---|
| `scripts/run_v1_acceptance.sh` | Orchestrates repository hygiene, frontend/admin checks, backend compileall, public API smoke, password reset smoke, user lifecycle smoke, auth/permission smoke, V1 content smoke, diff check, forbidden artifact scan, and basic secret scan. |
| `scripts/run_local_public_api_smoke.sh` | Starts an isolated local API runtime and runs public API readiness smoke. |
| `scripts/smoke_password_reset_backend.sh` | Verifies generic reset request response, hash-only token storage, expiry, consumed/reuse rejection, old/new password behavior, and audit redaction. |
| `scripts/smoke_user_lifecycle_backend.sh` | Verifies pending, approved, rejected, disabled, enabled, institution-user creation, role assignment, and user audit records. |
| `scripts/smoke_auth_permission_backend.sh` | Verifies anonymous admin rejection, ordinary user admin rejection, super-admin access, and role-assignment permission boundary. |
| `scripts/smoke_v1_content_backend.sh` | Verifies V1 public content payloads, published-only filtering, detail routes, settings, leaders, categories, tags, and admin content endpoint reachability. |

## 4. Non-V1 Items

- V2 talent delivery, expert services, event registration, full-site search, recommendation, and statistics systems.
- Real SMTP full-link UAT.
- Real SMS provider and SMS login acceptance.
- SSO.
- Kubernetes manifests.
- Production performance testing.
- Full external security scan report.
- Public file download and signed image delivery hardening.
