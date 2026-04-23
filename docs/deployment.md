# Portal Deployment Guide

## Local development

### API

1. Create the virtual environment at the project root: `uv venv .venv`.
2. Install API dependencies: `uv pip install --python .venv/bin/python -r apps/api-server/requirements.txt`.
3. Start the API from `apps/api-server` with `../../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8100`.

### Admin console

1. Copy `apps/admin-console/.env.example` to `.env`.
2. Install dependencies with `pnpm install`.
3. Run `pnpm --dir apps/admin-console dev`.

### Portal frontend

1. Copy `apps/web-portal/.env.example` to `.env`.
2. Install dependencies with `pnpm install`.
3. Run `pnpm --dir apps/web-portal dev`.

## Container baseline

1. Copy `deploy/docker/.env.example` to `deploy/docker/.env`.
2. Replace all placeholder values in `deploy/docker/.env`:
   - `PORTAL_SECRET_KEY`
   - `PORTAL_ADMIN_PASSWORD`
   - `PORTAL_SMS_TEST_CODE`
   - `POSTGRES_PASSWORD`
   - `DATABASE_URL`
3. Review `deploy/docker/nginx.portal.conf` and `deploy/docker/nginx.admin.conf`.
   - Both files include HTTP to HTTPS redirects.
   - Both files use placeholder certificate paths `/etc/ssl/certs/portal.crt` and `/etc/ssl/private/portal.key`.
   - Replace those paths with real certificate and key files before external deployment.
4. Start the stack from `deploy/docker`:
   - `docker compose up -d --build`
5. Verify service readiness:
   - PostgreSQL passes its health check before the API starts.
   - Portal frontend is exposed on port `3100` and HTTPS placeholder port `3443`.
   - Admin console is exposed on port `5174` and HTTPS placeholder port `8443`.
6. Stop the stack when needed:
   - `docker compose down`

`deploy/docker/docker-compose.yml` provides PostgreSQL, API, portal frontend, and admin console. The backend uses PostgreSQL in containers and SQLite only for local fallback development.

## Default credentials

- Username: `admin`
- Password: `ChangeMe123!`

Replace the administrator password in environment variables before any shared or external deployment.
