# Q3 Dual-platform 100 VU Performance Report

## 1. Scope

本报告记录 Q3 双平台 100 并发虚拟用户预发布性能验证。测试从本地 Mac 发起，请求目标为 ECS 上的 HTTPS 公开端点：

- Portal public: `https://huairou.tech`
- Portal admin shell: `https://portal-admin.huairou.tech`
- Achievement public: `https://cg.huairou.tech`

本轮 100 VU 表示 100 concurrent virtual users，不等同于 100 QPS。脚本只覆盖低扰动、只读 GET/HEAD 类访问，不覆盖注册、登录失败锁定、审核、创建用户、文件上传、EICAR、ClamAV worker、真实邮件或任何写操作。

## 2. Test Model

核心脚本：

- `performance/k6/dual-platform-100vu.js`
- `performance/scripts/portal-home-cache-check.sh`
- `performance/scripts/server-readonly-snapshot.sh`
- `performance/scripts/nginx-log-summary.sh`
- `performance/scripts/nginx-perf-log-summary.sh`
- `performance/scripts/docker-stats-watch.sh`

Q3 执行路径：

| Gate | Profile | Load shape | Result |
| --- | --- | --- | --- |
| Script inspection | `warmup10` / `diagnose50` / `baseline100` | syntax and profile guard check | PASS |
| Cache check | N/A | Portal root cache HIT and query BYPASS check | PASS |
| 10 VU check | `warmup10` | low-volume script/network validation | PASS |
| 50 VU gate | `diagnose50` | ramp to 50 VU, 8 minutes steady | PASS |
| 100 VU formal | `baseline100` | 2m ramp to 10, 5m ramp to 100, 20m steady, 2m down | FAIL |

`baseline100` 只有在 `RUN_FULL_LOAD=true` 时才允许运行，避免误触正式 100 VU 测试。

## 3. Cache Boundary

Portal home cache 在 Q3 开始和结束时均通过边界检查：

| Check | Start result | End result |
| --- | --- | --- |
| Portal root second request | `X-Cache-Status: HIT` | `X-Cache-Status: HIT` |
| Portal root query request | `X-Cache-Status: BYPASS` | `X-Cache-Status: BYPASS` |
| Portal public API | no cache HIT header | no cache HIT header |
| Portal admin shell | no cache HIT header | no cache HIT header |
| Achievement shell | no cache HIT header | no cache HIT header |

结束检查中 Portal root first request 返回 `STALE`，second request 返回 `HIT`，符合保守缓存边界：缓存可服务 stale/html 命中，但带 query 的注册提示类入口不会被普通首页缓存覆盖。

本地 `curl` 在 macOS 上多次出现 TLS `SSL_ERROR_SYSCALL`，脚本已按既有设计 fallback 到 Python urllib，并完成 HTTP status 与 cache header 断言。

## 4. k6 Results

### 4.1 10 VU

| Metric | Result |
| --- | --- |
| Checks | 100.00%, 4351 / 4351 |
| Failed requests | 0.00%, 0 / 4351 |
| Requests | 4351, 17.928 req/s |
| Overall p95 / p99 | 33.02 ms / 40.87 ms |
| Portal home HTML p95 / p99 | 29.33 ms / 41.13 ms |
| Portal API group p95 / p99 | 36.51 ms / 44.17 ms |
| Portal admin shell p95 / p99 | 14.78 ms / 15.70 ms |
| Achievement HTML p95 / p99 | 15.90 ms / 23.14 ms |
| Achievement API group p95 / p99 | 19.58 ms / 23.94 ms |

10 VU 预检通过。

### 4.2 50 VU Gate

| Metric | Result |
| --- | --- |
| Checks | 100.00%, 48824 / 48824 |
| Failed requests | 0.00%, 0 / 48824 |
| Requests | 48824, 81.306 req/s |
| Overall p95 / p99 | 37.52 ms / 63.10 ms |
| Portal home HTML p95 / p99 | 36.53 ms / 188.45 ms |
| Portal API group p95 / p99 | 44.02 ms / 74.00 ms |
| Portal admin shell p95 / p99 | 20.80 ms / 168.80 ms |
| Achievement HTML p95 / p99 | 20.39 ms / 55.56 ms |
| Achievement API group p95 / p99 | 23.24 ms / 32.37 ms |

50 VU gate 通过。50 VU 后的 Nginx access 摘要显示最近 12000 条均为 HTTP 200，无 5xx 样本。

### 4.3 100 VU Formal

| Metric | Threshold | Result | Verdict |
| --- | --- | --- | --- |
| Checks | `rate > 0.99` | 99.99%, 222009 / 222015 | PASS |
| Failed requests | `rate < 0.005` | 0.00%, 6 / 222015 | PASS |
| Overall p99 | `< 1500 ms` | 1.44 s | PASS |
| API type p95 | `< 800 ms` | 322.67 ms | PASS |
| HTML type p95 | `< 1000 ms` | 788.28 ms | PASS |
| Portal API group p95 | `< 800 ms` | 578.10 ms | PASS |
| Portal admin shell p95 | `< 1000 ms` | 28.00 ms | PASS |
| Achievement API group p95 | `< 800 ms` | 229.72 ms | PASS |
| Achievement HTML p95 | `< 1000 ms` | 31.35 ms | PASS |
| Portal home HTML p95 | `< 1000 ms` | 1.27 s | FAIL |

100 VU 正式测试不通过。失败项是 `endpoint_group_portal_html_duration p95=1.27s`，超过 1 秒门槛。

100 VU 细节：

| Metric | Result |
| --- | --- |
| Requests | 222015, 127.534 req/s |
| Iterations | 54200 |
| Interrupted iterations | 0 |
| Overall p95 / p99 | 445.95 ms / 1.44 s |
| Portal home HTML avg / med / p90 / p95 / p99 / max | 350.25 ms / 106.41 ms / 824.12 ms / 1.27 s / 2.83 s / 60 s |
| Portal public home API p95 / p99 / max | 981.48 ms / 2.08 s / 52.27 s |
| Portal public cases API p95 / p99 / max | 685.55 ms / 1.60 s / 13.74 s |
| Portal public news API p95 / p99 / max | 359.54 ms / 1.39 s / 13.66 s |
| Portal public settings API p95 / p99 / max | 239.36 ms / 340.11 ms / 3.39 s |
| Achievement public achievements API p95 / p99 / max | 246.58 ms / 689.19 ms / 27.69 s |
| Achievement public facilities API p95 / p99 / max | 245.48 ms / 684.98 ms / 7.02 s |
| Achievement public talents API p95 / p99 / max | 231.06 ms / 445.32 ms / 3.48 s |

k6 warning 中出现 1 次 request timeout 和多次 HTTP/2 GOAWAY close。最终 checks failed 为 6：Portal home HTML 1 次非 200，Achievement facilities API 5 次非 200。k6 未出现 interrupted iterations。

## 5. Server Observation

### 5.1 Health and Availability

结束端只读快照显示：

- Portal compose: api healthy, web up, admin up, postgres healthy.
- Portal ClamAV: healthy.
- Achievement compose: backend healthy, frontend healthy, postgres healthy.
- Nginx config test: OK.
- Portal root, Portal public home API, Portal admin shell: HTTP 200.
- Achievement shell, Achievement health API: HTTP 200.
- PostgreSQL active connections: Portal 11, Achievement 11.

结束端 Nginx access 摘要显示最近 5000 条状态均为 HTTP 200，无 5xx 样本。

### 5.2 Nginx Timing Summary

结束端 60 分钟 perf access 摘要中，目标端点均为 200：

| Endpoint | Count | Status | request p95 | request p99 | request max | upstream p95 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Portal `/` | 26767 | 200 | 0.0 ms | 0.0 ms | 8.331 s | 104.0 ms |
| Portal `/api/v1/public/home` | 26811 | 200 | 44.0 ms | 94.0 ms | 282.0 ms | 44.0 ms |
| Portal admin `/` | 6708 | 200 | 1.0 ms | 2.0 ms | 6.0 ms | 4.0 ms |
| Achievement `/` | 26940 | 200 | 1.0 ms | 2.0 ms | 11.0 ms | 4.0 ms |
| Achievement `/api/v1/health` | 26939 | 200 | 2.0 ms | 4.0 ms | 42.0 ms | 4.0 ms |

Nginx 服务端 timing 与 k6 客户端 timing 存在差异：Nginx 看到 Portal root 多数为 cache 命中，request p95/p99 近似 0 ms；k6 客户端仍记录到 Portal home HTML 长尾，说明 100 VU 失败更接近端到端连接、传输或客户端观测长尾问题，而不是后端 public API 大面积 5xx。

### 5.3 Container and Host Resources

Docker stats watch 摘要：

| Load | Max load1 | Portal API max CPU | Portal Postgres max CPU | Achievement backend max CPU | Achievement Postgres max CPU | ClamAV max CPU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 VU | 1.76 | 47.66% | 15.71% | 80.82% | 7.52% | 2.87% |
| 100 VU | 1.97 | 66.27% | 25.47% | 87.44% | 9.75% | 3.27% |

内存占用稳定：结束快照显示系统 7.1 GiB 总内存，available 约 5.1 GiB；主要容器内存百分比未出现失控增长。ClamAV 常驻内存约 12%，符合已知服务形态。

Nginx error log 中仍可见外部 TLS handshake `bad key share` 记录，这类记录在 Q3 前后均存在；本轮未观察到应用 5xx 级别故障样本。

## 6. Decision

Q3 结论：不通过 100 VU 性能门。

通过项：

- 10 VU 预检通过。
- 50 VU gate 通过。
- Portal home cache HIT/BYPASS 边界通过。
- 100 VU 下总体 request failed rate 仍低于阈值。
- 100 VU 下 overall p99 仍低于 1.5 秒阈值。
- 100 VU 结束后两平台服务仍健康，无 5xx 样本。

未通过项：

- 100 VU 下 Portal home HTML group p95 为 1.27 秒，高于 1 秒阈值。

风险判断：

- 这不是服务整体不可用问题，而是 100 VU 下 Portal home HTML 端到端长尾问题。
- Portal public home API 在 100 VU 中也出现 p95 981.48 ms、p99 2.08 s 的明显长尾，虽未单独触发 group 阈值失败，但应纳入下一轮定位。
- k6 warning 中出现少量 HTTP/2 GOAWAY 和 timeout，后续需要区分客户端连接复用、Nginx HTTP/2 行为、公网链路、Portal home HTML payload/压缩与 Nuxt SSR/cache 回源边界。

## 7. Limitations

- 本轮从本地 Mac 通过公网访问 ECS，结果包含本地网络、公网链路、TLS/HTTP2 连接行为和客户端观测成本。
- 本轮未触发真实邮件、注册、审核、创建用户、登录失败锁定、文件上传、ClamAV worker 或 EICAR。
- 本轮不等价于生产真实用户行为模型，也不等价于 100 QPS 容量声明。
- 本轮不包含数据库写入型事务、后台管理复杂查询或文件下载压力。
- 本轮未调整服务器配置，也未部署或修改业务代码。

## 8. Recommended Follow-up

建议进入 Q3-Fix / Q3-Diagnose，而不是进入更高并发：

1. 先对 Portal home HTML 长尾做定向诊断：区分 cache HIT 下的传输长尾、HTTP/2 连接复用长尾、Nginx cache lock/stale 行为、Nuxt SSR 回源和 HTML payload/压缩影响。
2. 对 Portal public home API 单端点增加小规模定向 timing 诊断，因为它在 100 VU 中 p95 接近 1 秒。
3. 保持 50 VU 作为当前通过门槛；100 VU 需要修复后再跑一次正式验证。

## 9. Runtime Evidence

Runtime evidence is intentionally ignored by Git and remains under `performance/reports/runtime/`.

Key files:

- `q3_start_cache_check_20260601_155213.log`
- `q3_start_server_snapshot_20260601_155229.log`
- `q3_start_nginx_summary_20260601_155229.log`
- `q3_start_nginx_perf_summary_20260601_155229.log`
- `q3_k6_10vu_check_20260601_155240.log`
- `q3_k6_50vu_gate_20260601_155701.log`
- `q3_50vu_docker_stats_watch_20260601_155701.log`
- `q3_after_50vu_nginx_summary_20260601_160926.log`
- `q3_k6_100vu_formal_20260601_160942.log`
- `q3_100vu_docker_stats_watch_20260601_160942.log`
- `q3_end_cache_check_20260601_164005.log`
- `q3_end_server_snapshot_20260601_164019.log`
- `q3_end_nginx_summary_20260601_164019.log`
- `q3_end_nginx_perf_summary_20260601_164019.log`
