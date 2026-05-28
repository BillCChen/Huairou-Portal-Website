# Portal Website P0 Validation Report

## 1. Baseline

- Branch: codex/portal-baseline-attribution
- Latest commits:
  - 9c0d7e9 chore: snapshot portal current implementation state
  - 6bbbf1b chore: add portal repository hygiene and readiness docs
  - e52e573 chore: track environment templates and workspace lockfile
  - bdc04a4 chore: stop tracking local claude settings
  - 77e3f05 chore: add minimal portal acceptance scripts

## 2. Tool Versions

- Node: v26.0.0
- pnpm: 10.33.0
- Python: Python 3.14.4
- Docker: Docker version 29.4.0, build 9d7ad9f
- Docker Compose: Docker Compose version v5.1.1

## 3. Validation Results

| Check | Command | Status | Notes |
|---|---|---|---|
| Minimal acceptance | `./scripts/portal_min_acceptance.sh` | PASS | Forbidden artifact scan, basic secret scan, API route extraction, pnpm availability, and Python availability passed. Route extraction reported 58 routes. |
| Web typecheck | `pnpm check:web` | FAIL | Root script currently runs `pnpm --dir apps/web-portal nuxi typecheck` and pnpm reports `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL Command "apps/web-portal" not found`. |
| Web build | `pnpm build:web` | PASS | Nuxt production build completed. Build generated ignored `.output` and Nuxt cache artifacts only. |
| Admin typecheck | `pnpm check:admin` | PASS | `vue-tsc --noEmit` completed successfully. |
| Admin build | `pnpm build:admin` | PASS | Vite build completed. It emitted a chunk-size warning for a 1,092.23 kB JS asset, but returned exit code 0. |
| Backend compileall | `cd apps/api-server && python3 -m compileall app` | PASS | Python bytecode compilation completed for `app`. Generated `__pycache__` artifacts are ignored. |
| Docker compose config | `docker compose -f deploy/docker/docker-compose.yml config` | FAIL | Docker is available, but compose config fails because `deploy/docker/.env` is required by `env_file` and is absent. Compose also warns unset variables default to blank. |

## 4. Missing Verification Entrypoints

| Category | Current Status | Required Later |
|---|---|---|
| Backend pytest | Missing | P1/P2 |
| API smoke | Present | P0/P1 |
| E2E | Missing | P3 |
| Security scan | Missing | P3 |
| Performance test | Missing | P3 |
| K8s validation | Missing | P3 or later |

Notes:

- The discovery command found Python test files under `.venv/lib/python3.13/site-packages`, which are third-party package files, not Portal project tests.
- API smoke is represented only by the P0 minimal acceptance scripts, especially `scripts/portal_min_acceptance.sh` and `scripts/extract_api_routes.py`; it does not yet exercise live HTTP endpoints.

## 5. Worktree After Validation

`git status --short` returned clean after all validation commands.

## 6. Interpretation

The following checks can become immediate P0/P1 admission gates:

- `./scripts/portal_min_acceptance.sh`
- `./scripts/check_forbidden_artifacts.sh`
- `./scripts/check_secrets_basic.sh`
- `python3 scripts/extract_api_routes.py`
- `pnpm build:web`
- `pnpm check:admin`
- `pnpm build:admin`
- `cd apps/api-server && python3 -m compileall app`

Current failures are baseline quality issues, not fixed in this run:

- `pnpm check:web` fails because the root package script command shape is invalid for the current pnpm invocation.
- `docker compose -f deploy/docker/docker-compose.yml config` fails because the required local `deploy/docker/.env` file is missing. This is an environment/template readiness issue rather than a container startup result.

Blocked or missing verification areas:

- No project-owned backend pytest suite was found.
- No Playwright or Cypress configuration was found.
- No Semgrep, Bandit, Gitleaks, or Trivy configuration was found.
- No k6, Locust, or JMeter performance test entry was found.
- API route extraction exists, but no live API smoke workflow exists yet.

## 7. Next Recommendation

Proceed to P0-4 only if the next task is to formalize validation gates and close non-business tooling gaps such as the web typecheck script and Docker env template workflow.

Proceed to P1 only after deciding whether P0/P1 is allowed to change validation scripts and package scripts. Without that allowance, `pnpm check:web` and Docker Compose config cannot be made passing gates.

## 8. P0-3b Validation Entrypoint Fix

P0-3b targeted two validation-entry failures from the first real validation run:

| Item | Previous Result | P0-3b Result | Notes |
|---|---|---|---|
| Web typecheck root script | FAIL | FAIL | Root script command form was corrected from direct pnpm binary invocation to `pnpm --dir apps/web-portal exec nuxi typecheck`. The command now reaches Nuxt typecheck but fails because no matching `tsconfig.json` exists in `apps/web-portal` or parent directories. This is a project typecheck configuration gap, not the previous root script parsing failure. |
| Docker compose config | FAIL | PASS | `deploy/docker/docker-compose.yml` now marks `.env` entries as optional and `scripts/check_docker_compose_config.sh` validates config with `--env-file deploy/docker/.env.example`, without creating or committing a real `.env` file. |

No business source code was modified.

## 9. P0-3c Web Typecheck Configuration Result

P0-3c added the minimal Nuxt web `tsconfig.json`:

```json
{
  "extends": "./.nuxt/tsconfig.json"
}
```

Result:

| Check | Before | After | Status |
|---|---|---|---|
| `nuxi prepare` | Not isolated | PASS | Nuxt generated `.nuxt/tsconfig.json` successfully |
| `pnpm check:web` | FAIL: missing matching `tsconfig.json` | FAIL: real TypeScript errors exposed | Configuration entrypoint improved; business/type errors remain |
| `pnpm build:web` | PASS | PASS | Build remains valid |
| `portal_min_acceptance.sh` | PASS | PASS after commit | Pre-commit run failed as designed because the worktree contained the intended untracked `apps/web-portal/tsconfig.json`; it should be run from a clean tree |

Current `pnpm check:web` errors are now real type-checking findings, not the previous missing-tsconfig entrypoint failure. Known error categories:

- `nuxt.config.ts`: `process` type is missing.
- Several pages access `message` / `detail` on values inferred as `{}`:
  - `pages/cases/index.vue`
  - `pages/index.vue`
  - `pages/institutes/index.vue`
  - `pages/news/index.vue`

No page, component, composable, API, database model, or business behavior was modified in P0-3c.
