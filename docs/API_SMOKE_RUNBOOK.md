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

## 9. P0-5 Local Real Smoke Record

P0-5 validated that `allow-unavailable` is only a placeholder mode and not a real PASS. Real public API smoke requires a running Portal API service.

Runtime attempts:

| Attempt | Runtime | Result | Notes |
|---|---|---|---|
| P0-5 | default `python3` | BLOCKED | `uvicorn` was not installed in the system Python environment. |
| P0-5a | Python 3.14 | BLOCKED | `psycopg[binary]==3.2.9` could not resolve a compatible `psycopg-binary==3.2.9` wheel. |
| P0-5b | Python 3.12.11 | BLOCKED | `python3.12 -m venv` failed at `ensurepip`. |
| P0-5c | Python 3.11.15 | PASS | Isolated venv under `.runtime-logs/p0-5/backend-venv-py311/` installed only `apps/api-server/requirements.txt`. |

P0-5c command used for real smoke:

```bash
PORTAL_API_BASE=http://127.0.0.1:18200 ./scripts/smoke_api_public.sh
```

Result: real public API smoke PASS against the controlled local API instance on `127.0.0.1:18200`.

Runtime artifacts were kept under `.runtime-logs/p0-5/` and must not be committed.

## 10. Reusable Local Real Smoke Runner

P0-6 added a reusable local runner:

```bash
PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_local_public_api_smoke.sh
```

The runner:

* selects a compatible Python interpreter;
* creates or reuses an ignored runtime venv under `.runtime-logs/local-public-api-smoke/`;
* installs only `apps/api-server/requirements.txt`;
* starts the API on `127.0.0.1:18200` by default;
* refuses to use port `8000`;
* fails if the target smoke port is already occupied and does not kill unknown processes;
* uses ignored SQLite and upload directories;
* runs `scripts/smoke_api_public.sh`;
* stops only the API process it started.

`PORTAL_SMOKE_ALLOW_UNAVAILABLE=1` is still only a placeholder mode and must not be counted as a real smoke PASS.
