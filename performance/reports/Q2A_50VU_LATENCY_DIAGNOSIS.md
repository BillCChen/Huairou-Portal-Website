# Q2-A 50 VU 高尾延迟诊断报告

## 1. 结论

本阶段未运行 100 VU，未设置 `RUN_FULL_LOAD=true`，未运行 `PROFILE=baseline100`。

Q2-A 复现了 Q1 的 50 VU 高尾延迟，并把主要来源定位到 `portal_html`，具体 endpoint 为 `portal_home_html`。50 VU 诊断结果中 `portal_home_html` p95 为 `4.84s`，p99 为 `7.97s`，max 为 `37.02s`；其他 HTML/API 组没有达到同等高尾。

初步归因：`https://huairou.tech/` 的 Portal public home HTML/SSR 路径是主要高尾来源。Achievement HTML、Portal admin static shell、Achievement API 和 Portal API 的 p95 均未触发阈值；Portal API 存在 p99 尾延迟，但不是本轮 p95 门禁失败的主因。当前 Nginx access log 不包含 `request_time` / `upstream_response_time`，因此 Q2-A 不能进一步把 `portal_home_html` 高尾拆分为 Nginx upstream、frontend container、或公网链路耗时。

## 2. 背景

Q1 50 VU 结果：

```text
http_req_failed: 0.00%
checks: 100%
overall p99: 3.41s
HTML p95: 3.21s
100 VU: not run
```

Q1 只能确认 HTML 总类高尾，不能区分 Portal public HTML、Portal admin shell、Achievement HTML 或具体 endpoint。

## 3. 本次变更

- `performance/k6/dual-platform-100vu.js`
  - 新增 `diagnose50` profile：1m ramp、8m steady、1m rampdown。
  - 新增 `endpoint_group` tags：`portal_html`、`portal_api`、`portal_admin_shell`、`achievement_html`、`achievement_api`。
  - 新增 `name` tags 和 endpoint-level Trend metrics。
  - 新增 endpoint group Trend metrics，并在 summary 中输出 p95/p99。
  - 保留 `baseline100` 必须显式设置 `RUN_FULL_LOAD=true` 的防误跑保护。

- `performance/scripts/docker-stats-watch.sh`
  - 每 5 秒通过 SSH 只读采集 `docker stats --no-stream`、`uptime`、`free -h`。
  - 输出到 `performance/reports/runtime/`。
  - 不读取 `.env`，不修改服务器，不输出 secret。

- `performance/scripts/nginx-timing-capability.sh`
  - 只读检查 Nginx `log_format` / `access_log` 是否包含 timing 字段。
  - 检查 access log 近样本是否有命名 timing marker。
  - 不修改 Nginx 配置，不 reload。

## 4. 测试环境

- Test time: 2026-05-31 23:15-23:32 CST.
- Load generator: local Mac, k6 v2.0.0.
- Portal public: `https://huairou.tech`
- Portal admin shell: `https://portal-admin.huairou.tech`
- Achievement public: `https://cg.huairou.tech`
- Server state: Portal and Achievement containers healthy/up before and after the diagnostic run.

## 5. 测试场景

只读 GET 场景：

| endpoint_group | endpoint |
| --- | --- |
| `portal_html` | `portal_home_html` |
| `portal_api` | `portal_public_home_api`, `portal_public_news_api`, `portal_public_cases_api`, `portal_public_settings_api` |
| `portal_admin_shell` | `portal_admin_shell_html` |
| `achievement_html` | `achievement_home_html` |
| `achievement_api` | `achievement_health_api`, `achievement_public_achievements_api`, `achievement_public_talents_api`, `achievement_public_facilities_api` |

未覆盖并且未触发：

- 注册、审核、拒绝、创建用户、改密、密码重置。
- 真实邮件。
- 连续错误登录与 lockout。
- 上传、EICAR、ClamAV worker。
- 服务器部署或配置修改。

## 6. k6 结果

### 10 VU check

```text
checks_succeeded: 100.00% 4312 out of 4312
http_req_failed: 0.00% 0 out of 4312
http_reqs: 4312, 17.599752/s
overall p99: 94.1ms
html p95: 86.49ms
api p95: 31.44ms
```

Endpoint group:

| group | p95 | p99 |
| --- | ---: | ---: |
| `portal_html` | `102.02ms` | `151.76ms` |
| `portal_api` | `33.78ms` | `42.78ms` |
| `portal_admin_shell` | `14.42ms` | `23.29ms` |
| `achievement_html` | `13.54ms` | `19.97ms` |
| `achievement_api` | `18.71ms` | `21.83ms` |

### 50 VU diagnose

```text
checks_succeeded: 100.00% 34772 out of 34772
http_req_failed: 0.00% 0 out of 34772
http_reqs: 34772, 57.7598/s
overall p95: 1.48s
overall p99: 3.7s
html p95: 3.5s
html p99: 6.16s
api p95: 301.44ms
api p99: 807.98ms
```

Endpoint group:

| group | p95 | p99 | max |
| --- | ---: | ---: | ---: |
| `portal_html` | `4.84s` | `7.97s` | `37.02s` |
| `portal_api` | `512.88ms` | `1.2s` | `13.92s` |
| `portal_admin_shell` | `18.49ms` | `228.92ms` | `233.93ms` |
| `achievement_html` | `29.55ms` | `229.82ms` | `896.23ms` |
| `achievement_api` | `230.21ms` | `286.62ms` | `6.73s` |

Endpoint detail:

| endpoint | p95 | p99 | max |
| --- | ---: | ---: | ---: |
| `portal_home_html` | `4.84s` | `7.97s` | `37.02s` |
| `portal_public_home_api` | `774.06ms` | `2.11s` | `13.92s` |
| `portal_public_cases_api` | `519.27ms` | `1.57s` | `13.75s` |
| `portal_public_news_api` | `300.63ms` | `947.97ms` | `13.68s` |
| `portal_public_settings_api` | `186.84ms` | `283.9ms` | `1.58s` |
| `portal_admin_shell_html` | `18.49ms` | `228.92ms` | `233.93ms` |
| `achievement_home_html` | `29.55ms` | `229.82ms` | `896.23ms` |
| `achievement_health_api` | `15.28ms` | `31.35ms` | `285.04ms` |

Threshold failure:

```text
endpoint_group_portal_html_duration
http_req_duration
http_req_duration{type:html}
```

## 7. 服务器资源

Continuous docker stats watch summary:

| container | max CPU | max memory |
| --- | ---: | ---: |
| `portal-prod-web-1` | `22.15%` | `1.65%` |
| `portal-prod-api-1` | `48.22%` | `1.11%` |
| `portal-prod-postgres-1` | `18.58%` | `0.89%` |
| `portal-prod-admin-1` | `0.11%` | `0.06%` |
| `achievement-prod-backend-1` | `73.55%` | `2.53%` |
| `achievement-prod-frontend-1` | `3.14%` | `0.06%` |
| `achievement-prod-postgres-1` | `8.37%` | `0.70%` |
| `portal-clamav-clamav-1` | `3.09%` | `12.04%` |

End snapshot:

```text
Portal public home API status: 200
Achievement health API status: 200
Portal postgres active connections: 11
Achievement postgres active connections: 10
Nginx access status summary: 200 5000
Nginx 5xx samples: none
```

Resource interpretation:

- Portal home HTML 高尾出现时，`portal-prod-web-1` sampled max CPU 为 `22.15%`，未显示 CPU 饱和。
- `portal-prod-api-1` 和 `portal-prod-postgres-1` sampled max CPU 低于 `50%` 和 `20%`，API p95 仍在阈值内。
- `achievement-prod-backend-1` 有 `73.55%` sampled CPU spike，但 Achievement HTML/API p95 未高尾，因此该 spike 不是 Portal HTML 高尾的直接解释。
- 内存没有持续增长或接近上限迹象。

## 8. Nginx 日志能力

只读检查结果：

```text
timing_fields_in_config=no
named_timing_markers_in_access_log=no
```

当前 Nginx access log 只有状态码统计能力，不能直接回答：

- Nginx 自身处理耗时。
- upstream response time。
- Portal web upstream 是否在特定时间段变慢。

Q2-B 如需继续定位，需要受控增加性能 log_format，例如包含 `$request_time` 与 `$upstream_response_time`，并保留 secret/query 参数脱敏边界。

## 9. 初步归因

归因类别：`HTML/static/SSR high tail`，更精确地说是 Portal public home HTML/SSR 高尾。

证据链：

```text
50 VU high tail
-> endpoint_group_portal_html_duration p95=4.84s, p99=7.97s
-> endpoint_portal_home_html_duration same as group
-> portal_admin_shell_html p95=18.49ms
-> achievement_home_html p95=29.55ms
-> type:api p95=301.44ms
-> Nginx 5xx=0
-> containers healthy/up after run
```

这说明问题不是全站公网访问都慢，也不是两个平台的所有 HTML 都慢。最可疑路径是 Portal public home HTML 的 Nuxt/SSR/upstream 链路，或其在公网链路上的响应体传输高尾。现有 Nginx 日志缺少 timing 字段，因此 Q2-A 不能把这两者完全拆开。

## 10. 下一步建议

Q2-B 建议只做受控诊断增强和低风险优化，不直接跑 100 VU：

1. 受控增加 Nginx performance access log，记录 `$request_time`、`$upstream_response_time`、host、URI、status，避免 query secret。
2. 对 Portal public home 做响应头和路径检查：是否 SSR、是否 gzip/br 压缩、是否可缓存、是否可静态化或缓存 HTML。
3. 重跑 `PROFILE=diagnose50`，确认 `portal_home_html` p95 是否低于 `1000ms`，再考虑恢复 Q1 的 100 VU gate。

## 11. 安全边界

- No 100 VU.
- No `RUN_FULL_LOAD=true`.
- No real email.
- No login lockout trigger.
- No upload.
- No EICAR.
- No ClamAV worker.
- No server config change.
- No deployment.
- No runtime logs committed.
- No secret, token, password, full email, or reset URL in this report.
