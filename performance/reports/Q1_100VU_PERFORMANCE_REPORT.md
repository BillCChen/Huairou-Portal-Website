# Q1 Dual-platform Performance Gate Report

## 1. Test Conclusion

本次 Q1 目标是从本地 Mac 对 ECS 上的 Portal 与 Achievement 做正式 100 VU 前的分级压测，并在风险门禁通过后才进入 100 VU。结论为：**10 VU warmup 通过，50 VU observe 未出现 HTTP 失败或 5xx，但 HTML/page 延迟和整体 p99 超过阈值，因此未继续执行 100 VU**。

本轮不能声明 100 VU 达标。当前更准确的结论是：双平台只读端点在 50 VU 下可用性保持正常，但页面类请求存在高尾延迟，需要先定位 HTML/static/Nginx/network bottleneck，再重跑 50 VU，之后再进入 100 VU。

## 2. Test Environment

- Test time: 2026-05-31 22:45-22:59 CST.
- Load generator: local Mac, k6 v2.0.0.
- Portal target: `https://huairou.tech` and `https://portal-admin.huairou.tech`.
- Achievement target: `https://cg.huairou.tech`.
- Portal server HEAD observed read-only: `d494544885cc908e22fd9c25adcb8686f5c3c2b4`.
- Achievement server HEAD observed read-only: `8014c7a29272e6bda609082da5cecf827df01759`.
- Scenario type: public/read-only GET endpoints and static shells only.
- Local `curl` note: local Mac `curl` continued to hit a LibreSSL/proxy handshake issue; server-side snapshots and k6 results were used as the HTTP health evidence.

## 3. Test Target

- Planned target: 100 concurrent virtual users.
- 100 VU means 100 virtual users, not 100 QPS.
- Actual executed profiles:
  - `warmup10`: 10 VU for 4 minutes.
  - `baseline50`: ramp to 50 VU, hold, then ramp down.
- `baseline100` was intentionally not executed because `baseline50` crossed latency thresholds.

## 4. Scenario Scope

Included read-only checks:

- Portal public home page.
- Portal public home/news/cases/settings APIs.
- Portal admin static shell.
- Achievement public home page.
- Achievement public health/achievements/talents/facilities APIs.

Excluded scenarios:

- Registration, approval, rejection, admin-created users, password change, or password reset.
- Real email delivery or SMTP UAT.
- Failed-login loops and lockout threshold triggers.
- Uploads, EICAR, ClamAV worker, or file scanning.
- Any destructive write or production data mutation.

## 5. Acceptance Thresholds

- HTTP failure rate: `< 0.5%`.
- Check success rate: `> 99%`.
- API p95: `< 800ms`.
- HTML/page p95: `< 1000ms`.
- Overall p99: `< 1500ms`.
- No Nginx 5xx samples.
- Containers remain up/healthy.
- No database connection exhaustion.

## 6. k6 Summary

### 10 VU warmup

Result: passed.

```text
checks_succeeded: 100.00% 4276 out of 4276
http_req_failed: 0.00% 0 out of 4276
http_reqs: 4276, 17.568368/s
overall p99: 84.8ms
overall p95: 58.47ms
api p95: 31.72ms
html p95: 78.43ms
vus_max: 10
```

### 50 VU observe

Result: blocked by latency thresholds.

```text
checks_succeeded: 100.00% 31949 out of 31949
http_req_failed: 0.00% 0 out of 31949
http_reqs: 31949, 59.036658/s
overall p99: 3.41s, threshold < 1500ms
overall p95: 1.28s
api p95: 291.76ms, threshold < 800ms
html p95: 3.21s, threshold < 1000ms
max request duration: 30.83s
vus_max: 50
```

Observed failure:

```text
thresholds on metrics 'http_req_duration, http_req_duration{type:html}' have been crossed
```

## 7. Server Resource Evidence

End-of-run server snapshot showed both platforms remained healthy:

```text
portal-prod-api-1: Up, healthy
portal-prod-web-1: Up
portal-prod-admin-1: Up
portal-clamav-clamav-1: Up, healthy
achievement-prod-backend-1: Up, healthy
achievement-prod-frontend-1: Up, healthy
portal-prod-postgres-1: Up, healthy
achievement-prod-postgres-1: Up, healthy
```

Host snapshot after 50 VU:

```text
load average: 0.54, 0.78, 0.53
memory available: about 5.1 GiB
root filesystem used: 9%
Portal postgres active connections: 11
Achievement postgres active connections: 10
```

Container stats after 50 VU were low at the sampled moment. The sampled CPU and memory data did not show a sustained CPU or memory saturation signal, so the primary current symptom is high tail latency for HTML/page requests rather than backend API failure.

## 8. Log Evidence

Nginx access summary after the run:

```text
200 5000
```

Nginx 5xx samples:

```text
none
```

Nginx error logs contained background TLS handshake warnings from external clients. These were not business 5xx responses and were also present outside the k6 result path.

Portal and Achievement API log scans showed recent 200 responses for the sampled public endpoints. No secret, token, password, or full email was included in this report.

## 9. Script Changes

`performance/k6/dual-platform-100vu.js` now supports explicit profiles:

- `smoke`
- `warmup10`
- `baseline50`
- `baseline100`

The 100 VU profile still requires `RUN_FULL_LOAD=true`, so an accidental full load cannot be started by using only the default command.

Validation performed:

```text
k6 inspect performance/k6/dual-platform-100vu.js
k6 inspect -e PROFILE=warmup10 performance/k6/dual-platform-100vu.js
k6 inspect -e PROFILE=baseline50 performance/k6/dual-platform-100vu.js
k6 inspect -e PROFILE=baseline100 performance/k6/dual-platform-100vu.js
k6 inspect -e PROFILE=baseline100 -e RUN_FULL_LOAD=true performance/k6/dual-platform-100vu.js
node --check performance/k6/dual-platform-100vu.js
```

## 10. Runtime Evidence Paths

Runtime files are intentionally ignored and must not be committed.

- `performance/reports/runtime/q1_k6_10vu_warmup_20260531_224527.log`
- `performance/reports/runtime/q1_k6_50vu_observe_20260531_224942.log`
- `performance/reports/runtime/q1_start_server_snapshot_20260531_224505.log`
- `performance/reports/runtime/q1_start_nginx_summary_20260531_224509.log`
- `performance/reports/runtime/q1_start_docker_stats_20260531_224509.log`
- `performance/reports/runtime/q1_mid_docker_stats_20260531_225920.log`
- `performance/reports/runtime/q1_end_server_snapshot_20260531_225923.log`
- `performance/reports/runtime/q1_end_nginx_summary_20260531_225926.log`
- `performance/reports/runtime/q1_end_docker_stats_20260531_225926.log`

## 11. Risk and Limitations

- This is not a max-capacity test.
- This is not a security test.
- This is not an SLA guarantee.
- The test does not cover write paths, account workflows, email delivery, uploads, or virus scanning.
- Since 50 VU crossed latency thresholds, the 100 VU result is intentionally absent.
- The strongest observed bottleneck candidate is HTML/page high tail latency. API p95 remained below threshold at 50 VU.

## 12. Recommended Next Step

Before running 100 VU:

1. Inspect HTML/static request latency split by target host and path.
2. Check whether Nuxt/static shell responses are missing compression/cache headers or are constrained by Nginx/proxy/network behavior.
3. Rerun `baseline50` after mitigation and require both overall p99 and HTML p95 to pass.
4. Only then run `baseline100` with `RUN_FULL_LOAD=true`.
