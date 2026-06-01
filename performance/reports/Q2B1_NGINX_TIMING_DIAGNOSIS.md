# Q2-B1 Nginx Timing Log 诊断报告

## 1. 结论

本阶段未运行 100 VU，未设置 `RUN_FULL_LOAD=true`，未运行 `PROFILE=baseline100`。

本阶段在 ECS 服务器上受控新增了 Nginx performance timing access log，并运行了 10 VU 快速检查和 50 VU `diagnose50` 复测。50 VU 再次复现 Portal home HTML 高尾：`portal_home_html` p95 为 `4.58s`，p99 为 `9.79s`，max 为 `1m0s`，并出现 2 次 `https://huairou.tech/` request timeout。

Nginx timing log 显示 `huairou.tech GET /` 的 `request_time` 与 `upstream_response_time` 同步高尾：`request_time p95=2.643s`、`p99=7.089s`、`max=59.999s`；`upstream_response_time p95=2.644s`、`p99=7.088s`、`max=60.000s`。`upstream_connect_time p95=0.0ms`，`upstream_header_time p95=2.616s`。

归因：Portal home HTML 高尾主要来自 Portal web upstream/SSR 首包生成路径。Nginx 自身连接建立不是主因，Portal API、Portal admin shell、Achievement HTML/API 不呈现同级高尾，Docker stats 未显示 Portal web/API/Postgres CPU 或内存饱和。

## 2. 背景

Q2-A 中 `portal_home_html` 高尾为：

```text
portal_home_html p95: 4.84s
portal_home_html p99: 7.97s
portal_home_html max: 37.02s
```

Q2-A 缺口是 Nginx access log 不含 `request_time` / `upstream_response_time`，无法区分 client/network、Nginx 层、Portal web upstream 或 backend/API。

## 3. 本次变更

- 新增服务器 Nginx performance timing log。
- 新增 `performance/scripts/nginx-perf-log-summary.sh`。
- 更新只读日志采集脚本，避免 runtime 日志输出真实 IPv4。
- 运行 10 VU 快速检查。
- 运行 50 VU `diagnose50` 复测。
- 未修改 Portal / Achievement 业务代码。
- 未部署应用服务，未重启 Portal / Achievement 容器。

## 4. Nginx 配置变更

服务器新增文件：

```text
/etc/nginx/conf.d/huairou_perf_log.conf
```

新增 log format 记录：

```text
request_time
upstream_connect_time
upstream_header_time
upstream_response_time
```

Nginx 配置备份：

```text
/opt/huairou/backups/nginx/q2b1/nginx_conf_20260601_093501.tar.gz
```

配置验证与 reload：

```text
nginx -t: passed
systemctl reload nginx: passed
```

应用服务未执行 `docker compose up` / `build` / `restart`。

## 5. k6 结果

### 10 VU check

```text
checks_succeeded: 100.00% 4222 out of 4222
http_req_failed: 0.00% 0 out of 4222
http_reqs: 4222, 17.423651/s
overall p99: 91.49ms
portal_home_html p95: 99.55ms
portal_api p95: 34.5ms
```

### 50 VU diagnose

```text
checks_succeeded: 99.99% 34893 out of 34895
checks_failed: 2 out of 34895
http_req_failed: 0.00% 2 out of 34895
http_reqs: 34895, 58.055316/s
overall p95: 1.43s
overall p99: 3.57s
html p95: 3.34s
api p95: 298.61ms
```

Endpoint group:

| group | p95 | p99 | max |
| --- | ---: | ---: | ---: |
| `portal_html` | `4.58s` | `9.79s` | `1m0s` |
| `portal_api` | `492.31ms` | `1.22s` | `6.65s` |
| `portal_admin_shell` | `177.33ms` | `239.86ms` | `455.24ms` |
| `achievement_html` | `91.53ms` | `231.72ms` | `890.13ms` |
| `achievement_api` | `229.44ms` | `289.17ms` | `13.67s` |

Endpoint detail:

| endpoint | p95 | p99 | max |
| --- | ---: | ---: | ---: |
| `portal_home_html` | `4.58s` | `9.79s` | `1m0s` |
| `portal_public_home_api` | `767.77ms` | `1.73s` | `6.65s` |
| `portal_admin_shell_html` | `177.33ms` | `239.86ms` | `455.24ms` |
| `achievement_home_html` | `91.53ms` | `231.72ms` | `890.13ms` |

Threshold failure:

```text
endpoint_group_portal_html_duration
http_req_duration
http_req_duration{type:html}
```

## 6. Nginx Timing 结果

Nginx performance log sample window: 30 minutes.

| host | method | uri | count | statuses | request p95 | request p99 | request max | upstream response p95 | upstream response p99 | upstream response max |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `huairou.tech` | `GET` | `/` | `3852` | `200:3850,499:2` | `2.643s` | `7.089s` | `59.999s` | `2.644s` | `7.088s` | `60.000s` |
| `huairou.tech` | `GET` | `/api/v1/public/home` | `7706` | `200:7706` | `40.0ms` | `61.0ms` | `105.0ms` | `40.0ms` | `60.0ms` | `104.0ms` |
| `portal-admin.huairou.tech` | `GET` | `/` | `934` | `200:934` | `1.0ms` | `1.0ms` | `6.0ms` | `4.0ms` | `4.0ms` | `8.0ms` |
| `cg.huairou.tech` | `GET` | `/` | `3786` | `200:3786` | `1.0ms` | `1.0ms` | `8.0ms` | `4.0ms` | `4.0ms` | `8.0ms` |
| `cg.huairou.tech` | `GET` | `/api/v1/health` | `3787` | `200:3787` | `2.0ms` | `3.0ms` | `15.0ms` | `4.0ms` | `4.0ms` | `16.0ms` |

Interpretation:

- `huairou.tech GET /` 的 `request_time` 与 `upstream_response_time` 几乎等值。
- `upstream_connect_time p95=0.0ms`，连接建立不是瓶颈。
- `upstream_header_time p95=2.616s`，高尾集中在 upstream 返回首包前。
- Portal public home API 的 Nginx p95 只有 `40.0ms`，backend/API 不是本轮主因。
- Achievement 与 Portal admin shell 在 Nginx 层均低延迟。

## 7. Docker stats

Continuous docker stats watch summary:

| container | max CPU | max memory |
| --- | ---: | ---: |
| `portal-prod-web-1` | `22.87%` | `1.25%` |
| `portal-prod-api-1` | `52.51%` | `1.11%` |
| `portal-prod-postgres-1` | `17.97%` | `0.92%` |
| `portal-prod-admin-1` | `0.09%` | `0.06%` |
| `achievement-prod-backend-1` | `71.49%` | `2.54%` |
| `achievement-prod-frontend-1` | `3.16%` | `0.06%` |
| `achievement-prod-postgres-1` | `7.91%` | `0.73%` |
| `portal-clamav-clamav-1` | `2.93%` | `12.04%` |

Portal web sampled CPU and memory do not indicate saturation. Portal API and Postgres sampled values also do not explain `GET /` HTML p95 and p99.

## 8. 初步归因

归因类别：Portal web upstream/SSR 首包生成高尾。

Evidence chain:

```text
k6 portal_home_html p95=4.58s, p99=9.79s, max=1m0s
-> Nginx huairou.tech GET / request_time p95=2.643s, p99=7.089s, max=59.999s
-> Nginx huairou.tech GET / upstream_response_time p95=2.644s, p99=7.088s, max=60.000s
-> upstream_connect_time p95=0.0ms
-> Portal public home API Nginx request p95=40.0ms
-> Portal admin shell and Achievement HTML are low-latency
-> Docker stats do not show Portal web/API/Postgres resource saturation
```

This matches case A from the Q2-B1 decision tree: k6 high tail, Nginx request high tail, and Nginx upstream response high tail align on `huairou.tech GET /`.

There is still a visible gap between k6 p95 (`4.58s`) and Nginx request p95 (`2.643s`). That can include client-side TLS/network scheduling and percentile population differences, but it does not remove the upstream/SSR finding because Nginx itself recorded multi-second upstream waits for the same route.

## 9. 下一步建议

Q2-B2 should focus on Portal home HTML upstream/SSR/cache/static tuning before any 100 VU run:

1. Inspect Portal home rendering path, data fetch pattern, compression, and cache headers.
2. Decide whether `/` can be statically generated, cached at Nginx, or split from slow runtime data.
3. Re-run `PROFILE=diagnose50` and require `portal_home_html p95 < 1000ms` before returning to the 100 VU gate.

Do not start Q2-B2 by tuning Portal API or DB globally; Q2-B1 shows `/api/v1/public/home` is not the primary latency source under Nginx timing.

## 10. 安全边界

- No 100 VU.
- No `RUN_FULL_LOAD=true`.
- No real email.
- No login lockout trigger.
- No registration, review, or admin user creation.
- No upload.
- No EICAR.
- No ClamAV worker.
- No app deployment.
- No Portal / Achievement container restart.
- No server `.env.production` read or modified.
- No runtime logs committed.
- No secret, token, password, full email, or reset URL in this report.
