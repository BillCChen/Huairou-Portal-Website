# Portal P4 Postdeploy Audit

## 1. Scope

本文档记录 Portal P4 security alignment RC 在服务器完成部署后的只读审计，以及本地 main fast-forward merge 结果。

本轮只做审计、main 本地 fast-forward 和文档记录；未 push main，未部署新版本，未重启服务器服务。

## 2. Server Audit

- Audit time: 2026-05-31 21:54 CST
- Server branch before merge: `codex/p4d-ip-audit-log-alignment`
- Server HEAD before merge: `d494544885cc908e22fd9c25adcb8686f5c3c2b4`
- RC tag: `v1.0-portal-p4-security-alignment-rc1`
- RC tag target: `d494544885cc908e22fd9c25adcb8686f5c3c2b4`

## 3. Public Endpoints

| Endpoint | Result |
| --- | --- |
| `https://huairou.tech/` | 200 |
| `https://huairou.tech/api/v1/public/home` | 200 |
| `https://portal-admin.huairou.tech/` | 200 |

## 4. Runtime Status

Portal compose status:

- `portal-prod-api-1`: up and healthy
- `portal-prod-web-1`: up
- `portal-prod-admin-1`: up
- `portal-prod-postgres-1`: up and healthy

ClamAV status:

- `portal-clamav-clamav-1`: up and healthy

Nginx:

- `nginx -t` passed.
- Enabled sites include `portal-prod.conf` and `cg-prod.conf`.
- Recent Nginx error log includes external TLS handshake failures with `bad key share`; public HTTPS smoke still passed and no application 5xx was observed.

## 5. Log Review

Checked recent Portal API logs and Nginx status.

Result:

- No sustained 5xx found.
- No missing column error found.
- No migration error found.
- No leaked secret pattern found in the reviewed log summary.
- Health-check lines containing local ports were treated as non-errors.

## 6. Safety Boundary

- No real account email was triggered during audit.
- No login lockout threshold test was triggered during audit.
- No EICAR file was uploaded during audit.
- No server file was modified during audit.
- No server service was restarted during audit.
- Achievement remained healthy during audit.

## 7. Main Merge

| Item | Value |
| --- | --- |
| Main before | `a4b250238fe80ec3734459c388ea0f4a1eaf06a6` |
| Main after fast-forward | `d494544885cc908e22fd9c25adcb8686f5c3c2b4` |
| RC tag target | `d494544885cc908e22fd9c25adcb8686f5c3c2b4` |
| Fast-forward merge | yes |
| Merge commit created | no |
| Main pushed | no |

## 8. Validation Notes

Local validation before merge passed:

- `portal_min_acceptance`
- `run_v1_acceptance`
- password policy smoke
- account notification smoke
- login lockout smoke
- session expiry smoke
- audit IP smoke
- file download security smoke
- file scan status smoke
- ClamAV worker smoke
- web/admin typecheck and build
- backend compileall
- diff/artifact/secret scans

Known warnings:

- Existing npm configuration warnings were printed by the local Node toolchain.
- Nuxt reported a sourcemap warning during web build.
- Admin build reported chunk size warnings.
- Vue language tooling reported a plugin warning during web typecheck.

## 9. Next Step

Portal main is now locally aligned with the deployed P4 RC target plus this postdeploy audit commit. Pushing main remains a separate authorization step.
