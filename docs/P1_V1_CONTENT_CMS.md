# Portal P1 V1 Content CMS Acceptance

## 1. Scope

P1-E closes the Portal V1 content acceptance surface for homepage, news, cases, about-us content, leaders, banners, categories, tags, and site settings.

This stage does not implement V2 business systems, full-text search, talent delivery, expert appointment, event registration, statistics/recommendation systems, external integrations, real SMS, or real SMTP.

Password reset and user lifecycle behavior are unchanged in P1-E.

## 2. V1 Content Acceptance Matrix

| Module | Public Surface | Admin Surface | P1-E Status |
|---|---|---|---|
| Homepage | `/api/v1/public/home`, `apps/web-portal/pages/index.vue` | Banners, pages, settings, articles, cases | Closed for V1 display |
| News | `/api/v1/public/news`, `/api/v1/public/news/{slug}` | `ListView.vue` article mode | Closed for list, search, category, detail, publish state |
| Cases | `/api/v1/public/cases`, `/api/v1/public/cases/{slug}` | `ListView.vue` case mode | Closed for intro, partner, benefits, stage, detail |
| About us | `/api/v1/public/pages/about`, `/api/v1/public/settings` | page blocks and site settings | Closed for mission, vision, strategy, governance, contact |
| Leaders | `/api/v1/public/leaders` | `LeadersView.vue` | Closed for visible leader list and admin maintenance |
| Banners | homepage payload | `ListView.vue` banner mode | Closed for title, subtitle, link, sort, enabled |
| Categories | `/api/v1/public/categories` | `CategoriesView.vue` | Closed for news/case category maintenance |
| Tags | `/api/v1/public/tags` | `CategoriesView.vue`, admin tag routes | Closed for basic tag list and edit |

## 3. Backend Closure

P1-E reuses the existing content models:

- `Article`
- `CaseStudy`
- `Page`
- `Leader`
- `Banner`
- `Category`
- `Tag`
- `SiteSetting`

The public serializers now expose category and tag metadata for articles and cases, while still only returning published or enabled public content. Draft or offline content remains hidden from public endpoints.

No migration framework was added. Portal still follows the current `Base.metadata.create_all` baseline; formal migrations remain later hardening work.

## 4. Frontend Closure

The public portal now displays the V1 homepage sections through backend content instead of hardcoded-only content:

- homepage banners
- institution profile
- homepage statistics
- latest news
- successful cases

News and case detail pages display the V1 fields needed for acceptance. Empty data states remain safe and do not expose raw JSON.

## 5. Admin Closure

The admin console now exposes the key V1 content controls:

- article category, tags, cover file id, publish time, top flag
- case category, tags, partner, stage, benefits, highlights, result blocks
- page blocks for about-us structured content
- banner image file id, sort, enabled state
- category and tag maintenance
- leader maintenance
- menu entries for pages, categories/tags, and leaders

Initial passwords, reset tokens, secrets, and full reset links are not part of any content CMS surface.

## 6. File Display Boundary

Current file records store file identifiers and storage paths for admin upload tracking. P1-E does not add a public file download or public image serving service. Frontend V1 pages keep safe fallbacks where a public image URL is not available.

Public file delivery, download access control, and file URL signing remain later hardening work.

## 7. Smoke Coverage

P1-E adds:

```bash
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/smoke_v1_content_backend.sh
```

The smoke uses isolated runtime SQLite under `.runtime-logs/v1-content-smoke/` and validates:

- API health
- homepage payload sections
- news list, search, category filter, and detail
- case list and detail
- about-us blocks
- leaders
- categories
- tags
- public settings
- draft content is not exposed publicly
- admin content endpoints are reachable with the seeded local admin account

The script does not send email, use real SMTP, read secrets, or write runtime artifacts to Git.

## 8. Remaining Work

- P1-F should consolidate public/auth/admin smoke evidence into acceptance documentation.
- Admin CRUD smoke can be broadened later to verify publish/offline transitions through UI/API.
- Public file delivery and file security gates remain later hardening work.
- V2 modules remain excluded from P1-E.
