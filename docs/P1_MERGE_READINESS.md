# Portal P1 Merge Readiness

## 1. Branch

- branch: `codex/portal-p1-contract-closure`
- base: `main` at P0 tag `v1.0-portal-p0-baseline-rc1`
- purpose: V1 contract closure

## 2. Completed P1 Stages

| Stage | Scope | Commit | Result |
|---|---|---|---|
| P1-A | Auth scope revision | `485a8f90a5e2a86b2f1e4e40fb453e1acd86d980` | PASS |
| P1-B | Email password reset backend | `1854ee2` | PASS |
| P1-C | Email password reset frontend | `f2d08ba` | PASS |
| P1-D | User lifecycle | `7326c61` | PASS |
| P1-E | V1 content CMS | `af8f2a814c26538ba1e9f0936bc866e0e6b6c676` | PASS |
| P1-F | V1 acceptance runner and report | `df7b806`, `f95ac91` | PASS |
| P1-G | Merge readiness and RC tag preparation | this document commit | PASS |

## 3. Final Validation

| Check | Result | Notes |
|---|---|---|
| `PORTAL_BACKEND_PYTHON=python3.11 ./scripts/run_v1_acceptance.sh` | PASS | Covers minimal acceptance, web/admin checks, backend compileall, public API smoke, password reset smoke, user lifecycle smoke, auth/permission smoke, V1 content smoke, diff check, forbidden artifact scan, and basic secret scan. |
| Forbidden artifact scan | PASS | No tracked runtime logs, outputs, env files, SQLite databases, build output, or dependency directories were detected. |
| Basic secret scan | PASS | No tracked secret-like value was reported by the repository basic scanner. |
| Route map stability | PASS | `python3 scripts/extract_api_routes.py` regenerated 68 routes without changing the worktree. |
| `git diff --check` | PASS | No whitespace errors. |
| Merge-tree | PASS | `main` is an ancestor of the P1 branch; no conflict marker was reported by merge-tree conflict scan. |
| Port cleanup | PASS | No listener remained on `127.0.0.1:18200` after validation. |

## 4. Scope Boundaries

- SMS verification login is excluded from Portal V1.
- Real SMS provider is not implemented.
- Email password reset is implemented with the local provider boundary; real SMTP full-link UAT remains a later track.
- V2 talent, expert, event, recommendation, full-site search, and statistics systems are not implemented in P1.
- Production performance test, external security scan report, Kubernetes manifests, formal migrations, and public file URL hardening remain later hardening items.

## 5. Known Warnings

- Vue language plugin warning during `pnpm check:web`; command exits 0.
- Nuxt sourcemap warning during `pnpm build:web`; command exits 0.
- Admin Vite chunk-size warning during `pnpm build:admin`; command exits 0.

## 6. Merge Recommendation

- Recommended merge mode after user approval: fast-forward merge into `main`.
- Recommended RC tag: `v1.0-portal-p1-v1-acceptance-rc1`.
- Do not push in this stage.
- Do not enter V2 until P1 is reviewed, accepted, and merged by explicit user instruction.
