# Portal Website API Smoke Runbook

## 1. Purpose

This runbook describes the minimal public API smoke check for Portal Website.

The smoke script verifies that a running API service can respond to selected non-destructive public GET endpoints with HTTP 200 and valid JSON.

## 2. Script

```bash
scripts/smoke_api_public.sh
```

## 3. Default Base URL

```bash
http://127.0.0.1:8000
```

Override with:

```bash
PORTAL_API_BASE=http://127.0.0.1:8000 ./scripts/smoke_api_public.sh
```

## 4. Scope

Current P0 public smoke endpoints:

| Method | Path | Reason |
|---|---|---|
| GET | `/healthz` | API process health |
| GET | `/api/v1/public/categories` | Public taxonomy |
| GET | `/api/v1/public/home` | Portal homepage data |
| GET | `/api/v1/public/news` | Public news list |
| GET | `/api/v1/public/cases` | Public case list |
| GET | `/api/v1/public/leaders` | Public leader list |
| GET | `/api/v1/public/institutes` | Public institute list |
| GET | `/api/v1/public/settings` | Public site settings |
| GET | `/api/v1/public/downloads` | Public download resource list |

## 5. Out of Scope for P0

The following are intentionally not covered in P0:

* Detail routes that require known slugs.
* `POST /api/v1/public/inquiries`, because it writes data.
* `/api/v1/auth/*`, because it requires login/SMS/test-account policy.
* `/api/v1/admin/*`, because it requires RBAC and test credentials.
* File upload/download security flows.
* Performance or concurrency tests.

## 6. Running Against an Existing API

Start the API by the documented local method, then run:

```bash
PORTAL_API_BASE=http://127.0.0.1:8000 ./scripts/smoke_api_public.sh
```

The script fails if any endpoint is unavailable, returns a non-200 status, or returns non-JSON content.

## 7. Documentation / CI Placeholder Mode

When the API service is not running and the goal is only to verify that the script itself is executable:

```bash
PORTAL_SMOKE_ALLOW_UNAVAILABLE=1 ./scripts/smoke_api_public.sh
```

This mode returns success with a `BLOCKED` message if the API is unavailable. It should not be treated as a real smoke PASS.

## 8. Future Extensions

Later stages should add:

* seeded slug checks for news/cases/institutes/pages detail routes;
* auth login smoke with a controlled test user;
* admin route RBAC smoke;
* file upload/download security smoke;
* inquiry POST smoke using isolated test data;
* Docker compose local acceptance smoke.
