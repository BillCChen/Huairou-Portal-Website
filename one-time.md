# Portal Website — One-Time Remediation Prompt

> Target: bring the current codebase to V1.0 acceptance criteria defined in
> 《附件-门户网站系统建设需求方案交付清单与功能清单》and
> 《门户网站系统_Claude开发规格书_乙方工作版》.
>
> Working directory root: `Portal-Website/`
> Three sub-apps: `apps/api-server` (FastAPI/SQLite→PostgreSQL), `apps/web-portal` (Nuxt 4),
> `apps/admin-console` (Vue 3 + Element Plus).
>
> **Rules:**
> - Code and comments in English only.
> - No AI tool names in code, comments, commit messages, or PR body.
> - No progress-phase words (FIXED, Step, Phase, AC-x) anywhere.
> - All changes must be runnable, verifiable, and rollback-safe.
> - Do not add features beyond what is listed below.

---

## 1. Security & Secrets (Critical — do first)

### 1-A  Remove hardcoded credentials from `docker-compose.yml`

File: `deploy/docker/docker-compose.yml`

Replace every hardcoded secret value with an env-var reference that reads from a
`.env` file.  Create `deploy/docker/.env.example` with safe placeholder values.
The compose file must never contain actual secret strings.

Fields to move out:
- `SECRET_KEY` → `${PORTAL_SECRET_KEY}`
- `ADMIN_PASSWORD` → `${PORTAL_ADMIN_PASSWORD}`
- `SMS_TEST_CODE` → `${PORTAL_SMS_TEST_CODE}`
- `POSTGRES_PASSWORD` (postgres service) → `${POSTGRES_PASSWORD}`
- `DATABASE_URL` (api service) → construct from `${POSTGRES_PASSWORD}`

Add to the `api` service:
```yaml
env_file:
  - .env
```

`.env.example` contents:
```
PORTAL_SECRET_KEY=replace-with-a-random-64-char-string
PORTAL_ADMIN_PASSWORD=replace-with-a-strong-password
PORTAL_SMS_TEST_CODE=replace-with-your-sms-test-code
POSTGRES_PASSWORD=replace-with-db-password
```

Add `.env` to `deploy/docker/.gitignore` (create the file if absent).

---

### 1-B  Remove credential pre-fill from `apps/web-portal/pages/login.vue`

The form reactive state currently initialises with:
```js
username: "admin", password: "ChangeMe123!", mobile: "13800000000", code: "123456"
```

Replace all four with empty strings `""`.  Remove any comment that references
the seed account.

---

### 1-C  Add file-upload validation in `apps/api-server/app/api/routes.py`

In the `admin_upload_file` route handler, before writing to disk:

1. Check `file.size` (if available) or read content and check `len(content)`.
   Reject with HTTP 413 if size > 52_428_800 bytes (50 MB).
2. Check `file.content_type` against an allowed set:
   `{"image/jpeg", "image/png", "image/webp", "application/pdf",
     "application/msword",
     "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
     "application/vnd.ms-excel",
     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}`.
   Reject with HTTP 415 if not in set.
3. Also validate the file extension matches the MIME type (prevent extension
   spoofing).

Return `{"code": 413, "message": "File too large"}` and
`{"code": 415, "message": "Unsupported file type"}` respectively, consistent
with the existing `APIResponse` envelope.

---

### 1-D  Gate system-settings endpoints on `require_super_admin`

File: `apps/api-server/app/api/routes.py`

The two settings routes (`GET /admin/settings/site` and `PUT /admin/settings/{key}`)
currently depend on `require_admin`.  Change their dependency to
`require_super_admin` so that content editors cannot alter site configuration.

The function `require_super_admin` already exists in `deps.py` — it is currently
unused.

---

## 2. Authentication & User Flow

### 2-A  Fix login flow in `apps/web-portal/pages/login.vue`

After a successful login response the page currently displays a truncated token
in the UI and does nothing else.  Replace that with:

1. Store the token: `localStorage.setItem("portal_token", token)`.
2. Store the user object: `localStorage.setItem("portal_user", JSON.stringify(user))`.
3. Navigate to the user's profile page: `navigateTo("/profile")`.

If the API returns an error, display the `message` field from the response body
in a visible error element (not `alert()`).

---

### 2-B  Fix registration flow in `apps/web-portal/pages/register.vue`

After a successful registration response, instead of displaying `status` and
`user_id` inline, show a clear success message:
> "注册申请已提交，请等待管理员审核，审核通过后您将收到通知。"

Provide a "返回首页" link (`/`).  Do not auto-redirect.

---

### 2-C  Implement `apps/web-portal/pages/forgot-password.vue`

The file already exists (it appears in build output).  Make it functional:

1. A single-step form: mobile number input + SMS code input + new password +
   confirm password.
2. "获取验证码" button calls `POST /api/v1/auth/sms-send` (add this endpoint
   to the API — see 2-D).
3. Submit calls `POST /api/v1/auth/reset-password` (add — see 2-D).
4. On success navigate to `/login`.
5. Client-side validation: password ≥ 8 chars, passwords match.

---

### 2-D  Add SMS and password-reset endpoints to `apps/api-server/app/api/routes.py`

**`POST /auth/sms-send`** (public)
- Body: `{"mobile": "138xxxxxxxx"}`
- For now, always return `{"code": 200, "message": "ok", "data": null}`.
- Log the call (print or audit log) so it is clear the code would be sent here.
- Rate-limit awareness: add a TODO comment marking where a real SMS provider call goes.

**`POST /auth/reset-password`** (public)
- Body: `{"mobile": "138xxxxxxxx", "code": "123456", "new_password": "..."}`
- Validate `code` against `settings.sms_test_code`.
- Look up user by `mobile`; if not found return 404.
- Hash and persist the new password.
- Return `{"code": 200, "message": "ok", "data": null}`.

Add corresponding Pydantic schemas to `app/schemas.py`.

---

### 2-E  Implement `apps/web-portal/pages/profile.vue`

The file exists (build output shows it).  Implement a basic profile page:

1. On mount, read token from `localStorage`.  If absent, `navigateTo("/login")`.
2. Call `GET /api/v1/auth/me` with `Authorization: Bearer <token>`.
3. Display: real_name, username, mobile, organization, expertise, status badge.
4. Add a logout button that clears localStorage and navigates to `/`.
5. Show 401 errors as a redirect to `/login`.

---

## 3. Admin Console Gaps

### 3-A  Wire edit (PUT) action in `apps/admin-console/src/views/ListView.vue`

The component currently only supports POST (create new).  The backend already
has `PUT /admin/{kind}/{id}`.

Add an edit flow:
1. Add an "编辑" button to each table row.
2. Clicking it populates the existing dialog form with the row's data and sets
   a local `editingId` ref.
3. On dialog submit, if `editingId` is set call `PUT /admin/{kind}/{editingId}`
   with the form payload; otherwise call `POST /admin/{kind}`.
4. After success, close dialog, reset `editingId`, reload the list.
5. The dialog title should read "新建内容" or "编辑内容" depending on mode.

---

### 3-B  Add missing admin menu items and views

File: `apps/admin-console/src/router/index.ts` and
`apps/admin-console/src/components/AppLayout.vue`

Add routes and sidebar links for:

| Route | View | Description |
|---|---|---|
| `/categories` | `CategoriesView.vue` | List + create/edit categories |
| `/leaders` | `LeadersView.vue` | List + create/edit leaders |
| `/institutes` | `InstitutesView.vue` | List + create/edit institutes |
| `/audit-logs` | `AuditLogsView.vue` | Read-only audit log list |

**CategoriesView.vue**: table columns title, slug, type, enabled; create/edit dialog
with fields name, slug (auto-generated from name, editable), type, parent_id
(dropdown), sort_order, enabled.  API: `GET /admin/categories`,
`POST /admin/categories`, `PUT /admin/categories/{id}`.

**LeadersView.vue**: table columns name, title, sort_order, is_visible;
create/edit dialog with fields name, title, photo (file upload via
`/admin/files/upload`), intro, sort_order, is_visible toggle.
API: `GET /admin/leaders`, `POST /admin/leaders`, `PUT /admin/leaders/{id}`.

**InstitutesView.vue**: table columns name, slug, status, sort_order;
create/edit dialog with fields name, slug, intro (textarea), directions
(textarea JSON hint), status dropdown (hidden/published), sort_order.
API: `GET /admin/institutes`, `POST /admin/institutes`, `PUT /admin/institutes/{id}`.

**AuditLogsView.vue**: read-only table with columns created_at, module, action,
object_type, user_id; paginated; no create.  API: `GET /admin/audit-logs`.

Verify the backend already exposes `GET /admin/audit-logs` in `routes.py` — it
does.  Verify `GET /admin/categories`, `POST/PUT /admin/categories/{id}` are
present — add any that are missing.

---

### 3-C  Add pagination to `UsersView.vue`

The current `UsersView.vue` fetches all users without pagination.  Add:
- `page` and `page_size=20` query params.
- `el-pagination` component at the bottom.
- A "状态" filter dropdown (all / pending / active / disabled).

---

### 3-D  Add leaders and institutes CRUD endpoints to the API

File: `apps/api-server/app/api/routes.py`

Check that the following endpoints exist; add any that are missing:

- `GET /admin/leaders` — list all leaders (admin auth)
- `POST /admin/leaders` — create leader
- `PUT /admin/leaders/{id}` — update leader
- `GET /admin/institutes` — list all institutes (admin auth)
- `POST /admin/institutes` — create institute
- `PUT /admin/institutes/{id}` — update institute
- `GET /admin/categories` — list all categories (admin auth)
- `POST /admin/categories` — create category
- `PUT /admin/categories/{id}` — update category

All responses must follow `{"code": 200, "message": "ok", "data": ...}` envelope.

---

## 4. Frontend Portal — V1.0 Feature Gaps

### 4-A  News list: add category filter

File: `apps/web-portal/pages/news/index.vue`

1. Call `GET /api/v1/public/categories?type=news` on page load.
2. Render a horizontal pill/tab row above the list: "全部" + one tab per category.
3. Clicking a tab sets `category_slug` query param and re-fetches.
4. The API endpoint `GET /public/news` already accepts `category` param — pass it.

Add `category` query param support to the backend:
In `routes.py`, `list_public_news` — add `category: str | None = None` to the
function signature; filter by `Category.slug == category` when provided.

---

### 4-B  News list: show pinned articles first

File: `apps/web-portal/pages/news/index.vue`

The spec requires "置顶优先排序".  The `Article` model has `is_top` field.
The backend `list_public_news` route currently sorts by `publish_at DESC`.
Change the order to `is_top DESC, publish_at DESC`.

Show a "置顶" badge next to pinned articles in the list (red pill label "置顶").

---

### 4-C  Home page: multi-item banner carousel

File: `apps/web-portal/pages/index.vue`

The page currently uses only the first banner (`banners[0]`).  Replace with a
functional carousel:

1. Fetch `/public/home` already returns all banners.
2. Implement auto-advance every 5 seconds; allow manual prev/next dots.
3. Each slide shows: background image, title, subtitle, button (if `button_text`
   and `button_url` are non-empty).
4. Use pure CSS transitions (no third-party carousel library).

---

### 4-D  Add SEO meta tags to all pages

All pages currently use only the global `<head>` from `nuxt.config.ts`.

Add `useSeoMeta()` calls to each page using data from the API:

- `news/[slug].vue`: title = article.seo_title || article.title,
  description = article.seo_desc || article.summary
- `cases/[slug].vue`: title = case.seo_title || case.title,
  description = case.seo_desc || case.summary
- `about.vue`: title = "关于我们 | " + site_name,
  description = page.seo_desc
- `news/index.vue`: title = "新闻动态 | " + site_name
- `cases/index.vue`: title = "成功案例 | " + site_name
- `index.vue`: title = site_name, description = site subtitle

Use `useHead()` or `useSeoMeta()` (Nuxt 4 built-in).

---

### 4-E  Implement proper 404 handling

File: `apps/web-portal/pages/404.vue` already exists.

1. In `apps/web-portal/error.vue`, when `error.statusCode === 404`, render the
   404 page content rather than a raw error dump.
2. In `news/[slug].vue` and `cases/[slug].vue`, if the API returns a 404/null
   result, call `throw createError({ statusCode: 404 })`.
3. In `institutes/[slug].vue`, same pattern.

---

### 4-F  Eliminate duplicate `/public/settings` request

`SiteFooter.vue` fetches `/public/settings` on every page.
`index.vue` already fetches `/public/home` which includes site_settings.

Create a Nuxt composable `composables/useSiteSettings.ts`:

```ts
export const useSiteSettings = () => {
  return useAsyncData("site-settings", () =>
    usePortalApi<SiteSettingsData>("/public/settings")
  );
};
```

Replace the direct `$fetch` in `SiteFooter.vue` with `useSiteSettings()`.
Nuxt's `useAsyncData` with the same key deduplicates the request across SSR/CSR.

---

### 4-G  Handle loading and error states

In the following pages, add skeleton/loading state and error fallback:

- `news/index.vue`: show loading skeleton while fetching; show "暂无新闻" if
  items is empty; show error message if fetch fails.
- `cases/index.vue`: same pattern — "暂无案例".
- `about.vue`: if leaders is empty, hide the leaders section entirely.
- `institutes/index.vue`: if list is empty, show "暂无研究所信息，敬请期待".

---

### 4-H  Cases list: add tag/category filter

File: `apps/web-portal/pages/cases/index.vue`

1. Fetch `/public/categories?type=case` on load.
2. Render filter tabs same as 4-A.
3. Pass `category` param to `/public/cases`.
4. Add `category` param support to `list_public_cases` in the backend
   (`routes.py`), same pattern as 4-A.

---

### 4-I  `cooperation.vue` page: fetch from CMS, not hardcode

File: `apps/web-portal/pages/cooperation.vue`

The page fetches `/public/pages/cooperation` but the seeded `cooperation` page
content is empty.  Update the seed data in `apps/api-server/app/db/seed.py`:
provide placeholder HTML content for the `cooperation` page key that describes
how to apply for partnership, including a contact email placeholder.

---

## 5. Backend API Gaps

### 5-A  Consistent slug-uniqueness error responses

In `routes.py`, when creating or updating articles/cases/institutes with a
duplicate slug, the database will raise an `IntegrityError`.  Currently this
propagates as HTTP 500.

Add a try/except around the `session.commit()` call in each create/update
route that can produce a unique-constraint violation.  Catch
`sqlalchemy.exc.IntegrityError` and return:
```json
{"code": 409, "message": "Slug already exists", "data": null}
```
with HTTP status 409.

---

### 5-B  Add `GET /public/categories` endpoint

File: `apps/api-server/app/api/routes.py`

The frontend filters need a public categories list.  Add:

```python
@router.get("/public/categories")
def list_public_categories(type: str | None = None, db: Session = Depends(get_db)):
    q = select(Category).where(Category.enabled.is_(True)).order_by(Category.sort_order)
    if type:
        q = q.where(Category.type == type)
    rows = db.scalars(q).all()
    return {"code": 200, "message": "ok",
            "data": [{"id": r.id, "name": r.name, "slug": r.slug, "type": r.type}
                     for r in rows]}
```

---

### 5-C  Add `DownloadResource` public and admin endpoints

The `DownloadResource` model exists in `models.py` but has no routes.

Add:
- `GET /public/downloads?category=&page=1&page_size=12` — public download list
  filtered to `is_public=True`.
- `GET /admin/downloads` — admin list (all resources).
- `POST /admin/downloads` — create resource.
- `PUT /admin/downloads/{id}` — update resource.

This is needed for the "资源下载" V2.0 path but the model is already in place.
The endpoints can return empty lists until content is added.

---

### 5-D  `ServiceRequest` persistence

File: `apps/api-server/app/api/routes.py`, handler `create_public_inquiry`.

Verify the handler saves the `ServiceRequest` row to the database and commits.
The endpoint body schema is `ServiceRequestIn` — confirm the route actually
calls `session.add()` and `session.commit()`.  If it only returns a success
response without persisting, add the persistence.

Add `GET /admin/service-requests` (admin auth) that lists all service requests,
paginated, sorted by `created_at DESC`.

---

### 5-E  Tighten CORS configuration

File: `apps/api-server/app/main.py`

Change `allow_methods=["*"]` to `allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]`.
Change `allow_headers=["*"]` to `allow_headers=["Authorization", "Content-Type", "Accept"]`.

---

### 5-F  Audit log for all state-changing admin operations

File: `apps/api-server/app/api/routes.py`

The `write_audit_log()` helper already exists.  Verify it is called in every
admin route that mutates data (create, update, approve-user, upsert-settings).
Add any missing `write_audit_log()` calls.  Each call must include:
- `module`: string name of the module (e.g. `"articles"`)
- `action`: `"create"` | `"update"` | `"delete"` | `"approve"`
- `object_type`: model class name string
- `object_id`: the row's primary key

---

## 6. Deployment & Operations

### 6-A  HTTPS configuration for nginx

File: `deploy/docker/nginx.portal.conf` and `deploy/docker/nginx.admin.conf`

Add an HTTPS server block to each nginx config file.  Use self-signed
certificate paths as placeholders (`/etc/ssl/certs/portal.crt` and
`/etc/ssl/private/portal.key`) with a comment block explaining how to replace
with a real certificate.

Redirect HTTP → HTTPS (301) for both configs.

Update `docker-compose.yml` to expose port 443 for both web and admin services.

---

### 6-B  PostgreSQL migration: remove SQLite fallback in compose

The API defaults to SQLite when `DATABASE_URL` is not set.  In
`docker-compose.yml` the api service must set `DATABASE_URL` using the
postgres service credentials.  Add a `depends_on: postgres: condition:
service_healthy` and a `healthcheck` to the postgres service so the API does
not start before the database is ready.

Also update `deploy/docker/.env.example` to include the full `DATABASE_URL`
example for postgres.

---

### 6-C  Remove Redis from compose if unused, or wire it

Redis is declared in `docker-compose.yml` but no application code uses it.

Choose one:
- Option A: Remove the `redis` service and its volumes from the compose file.
- Option B: Add a TODO comment at the redis service explaining it is reserved
  for session caching and rate-limiting in a future release.

Prefer Option A (smaller attack surface, simpler deployment).

---

## 7. Data Model Corrections

### 7-A  Add missing `site_settings` keys to seed

File: `apps/api-server/app/db/seed.py`

The `SiteSetting` rows seeded currently cover `site_profile`, `home_stats`,
`quick_links`.  The spec requires also:
- `seo_defaults` — `{"seo_title": "...", "seo_desc": "...", "seo_keywords": "..."}`
- `footer_links` — `{"links": []}` (for footer nav links)
- `icp_info` — `{"icp_no": "", "police_no": "", "analytics_code": ""}` (compliance)

Add these three rows to the seed function, guarded by the same "abort if roles
already exist" check.

---

### 7-B  `Article` category association fix

In `routes.py` `list_public_news`, confirm the join to `Category` is correct
when `category` param is provided.  The `Article` model has `category_id` FK.
The join should be `Article.category_id == Category.id`.

If `JOIN` is missing, add:
```python
.join(Category, Article.category_id == Category.id, isouter=True)
```
so articles without a category are still returned when no filter is applied.

---

## 8. Acceptance Criteria Verification Checklist

After implementing all items above, manually verify each acceptance item
from the spec (TABLE 10 of the spec book):

| ID | Item | Verify by |
|---|---|---|
| A-01 | Homepage accessible | `curl http://localhost:3100/` returns 200 |
| A-02 | Homepage modules visible | All 5 sections render with data |
| A-03 | News category filter | Select a tab, list updates |
| A-04 | News detail | Open any article, verify body/date/cover |
| A-05 | Cases list/detail | Open any case, verify all fields |
| A-06 | Admin login | Login with admin credentials, land on dashboard |
| A-07 | Content publish cycle | Create article → save draft → publish → unpublish |
| A-08 | File upload validation | Upload a .exe file → 415 error; upload a 60MB file → 413 error |
| A-09 | Registration approval | Register new user → check admin /users → approve → user can login |
| A-10 | Permission isolation | Login as content_admin → try GET /admin/settings → 403 |
| A-11 | Page performance | `curl -w "%{time_total}" http://localhost:3100/news` < 2.0s |
| A-12 | Concurrency | `ab -n 100 -c 100 http://localhost:3100/` → all 200 responses |
| A-13 | HTTPS active | `curl -I https://localhost/` returns valid redirect/200 |
| A-14 | Password hashing | Inspect `users` table: `password_hash` starts with `$pbkdf2` |
| A-15 | Deployment docs | `docs/deployment.md` covers docker-compose steps |

---

## 9. Execution Order

Execute the items in this order to minimise risk of breakage:

1. **1-A, 1-B** — secrets and credential pre-fill (no logic change)
2. **5-E** — CORS tightening (no functional impact)
3. **1-C, 1-D** — file validation, settings gate
4. **5-A, 5-B, 5-C, 5-D, 5-F** — backend API completeness
5. **2-D** — new auth endpoints (SMS send + reset password)
6. **7-A, 7-B** — seed and model fixes
7. **2-A, 2-B, 2-C, 2-E** — login/register/profile/forgot-password flows
8. **3-A, 3-B, 3-C, 3-D** — admin console edit + new views
9. **4-A, 4-B, 4-C, 4-D, 4-E, 4-F, 4-G, 4-H, 4-I** — frontend features
10. **6-A, 6-B, 6-C** — deployment hardening
11. Run acceptance checklist (section 8)
