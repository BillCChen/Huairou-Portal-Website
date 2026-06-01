# Q3-R 性能测试结论整理

## 1. 结论摘要

本次 Q3 100 VU 测试不能表述为“100 并发完全无压力通过”。

更准确的结论是：

- 100 VU 稳定性 / 可用性通过。
- 请求失败率为 0.00%（`6 / 222015`，按 k6 百分比显示四舍五入）。
- 结束端 Nginx access 摘要无 5xx 样本。
- 测试结束后 Portal 与 Achievement 均保持健康。
- 严格 Portal 首页 HTML p95 `< 1000ms` 延迟门槛未通过，实测为 `1.27s`。

因此，本轮应定性为：**100 VU 稳定性 / 可用性通过，严格 Portal 首页 HTML p95 延迟门槛仍有优化空间**。

## 2. 可用性证据

Q3 100 VU 正式测试完成了完整负载曲线，并保留以下可用性证据：

| Metric | Evidence |
| --- | --- |
| Total requests | `222015` |
| Request rate | `127.53 req/s` |
| Failed request rate | `0.00%`, `6 / 222015`, passed threshold |
| Overall p99 | `1.44s` |
| Nginx 5xx samples | none in the end access summary |
| Runtime health | Portal / Achievement / Nginx / Compose remained healthy after the run |
| Interrupted iterations | `0` |

这些指标说明：在低扰动只读访问模型下，系统没有出现整体不可用、服务崩溃、数据库连接耗尽或持续 5xx。它不表示“零异常样本”，因为 k6 仍记录到 6 个失败请求 / 检查样本。

## 3. 延迟门禁证据

Q3 的分级结果如下：

| Gate | Result |
| --- | --- |
| 10 VU overall p95 | `33.02ms` |
| 50 VU overall p95 | `37.52ms` |
| 100 VU overall p99 | `1.44s`, threshold `< 1500ms`, pass |
| 100 VU HTML type p95 | `788.28ms`, threshold `< 1000ms`, pass |
| 100 VU Portal home HTML p95 | `1.27s`, threshold `< 1000ms`, fail |

严格失败项是 `endpoint_group_portal_html_duration p95=1.27s`。这说明“稳定性通过”和“首页 HTML 严格延迟门槛未通过”可以同时成立：系统在 100 VU 下保持可访问，但 Portal 首页 HTML 的端到端长尾仍超过 1 秒目标。

## 4. 业务语义解释

对普通门户平台和当前开发阶段的低访问量只读场景，100 VU 下 failed request rate 四舍五入显示为 0.00%、无 Nginx 5xx 样本、测试后双平台健康，已经说明系统具备较好的并发稳定性基础。

但如果甲方验收标准明确要求“100 并发下 Portal 首页 HTML p95 `< 1s`”，本轮还不能作为完整性能验收通过材料。该口径必须保留 Portal 首页 HTML 长尾优化项，不能将结果包装为“100 并发无压力”。

## 5. 限制说明

本轮是低扰动只读访问模型，不覆盖：

- 注册。
- 审核。
- 管理员创建用户。
- 真实邮件。
- 登录失败锁定。
- 文件上传。
- EICAR。
- ClamAV worker。
- 写操作吞吐。
- 最大容量上限。
- 安全渗透测试。

100 VU 表示 100 个并发虚拟用户持续访问典型页面和公开接口，不等同于 100 QPS，也不等同于真实浏览器全链路容量上限。

## 6. 推荐对外表述

建议对外使用以下表述：

> 系统在 100 个并发虚拟用户的低扰动只读访问场景下保持稳定，未观察到 Nginx 5xx 错误，请求失败率为 0.00%，测试结束后门户网站、门户后台和成果转化平台均保持健康。当前主要待优化项为门户首页 HTML 在严格 p95 `< 1s` 门槛下略有超标，后续可继续针对首页长尾延迟进行优化。

更短版本：

> 100 并发稳定性通过，首页 HTML 长尾延迟仍有优化空间。

## 7. 不建议使用的表述

不要使用：

- 100 并发完全无压力。
- 100 VU 全部指标通过。
- 系统已经完成性能验收。
- 可承诺 100 QPS。
- 首页性能已经完全达标。

这些说法会掩盖 Portal 首页 HTML p95 `1.27s` 超过 1 秒门槛的事实。

## 8. 下一步建议

方案 A：如果甲方接受“稳定性通过，延迟继续优化”的阶段性口径，可进入阶段性验收材料整理。

方案 B：如果必须严格满足 Portal 首页 HTML p95 `< 1s`，则继续 Q3-Diagnose / Q4 优化 Portal home HTML 长尾。

方案 C：如需更接近真实用户体验，可引入云端压测机或不同网络环境复测，进一步区分本地 Mac 到 ECS 公网链路、HTTP/2 连接复用、Nginx cache 行为和 Portal 首页 HTML payload / 压缩影响。
