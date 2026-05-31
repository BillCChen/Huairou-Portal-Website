# 双平台 100 并发性能测试报告

## 1. 测试结论

示例结论占位：

在 100 个并发虚拟用户、持续 20 分钟的典型只读/轻认证场景下，系统未出现 5xx；核心接口 P95 响应时间满足验收阈值；服务器 CPU、内存、数据库连接保持安全余量。

## 2. 测试环境

- ECS 规格：
- OS：
- Docker / Compose：
- Nginx：
- PostgreSQL：
- Portal commit：
- Achievement commit：
- 测试时间：
- 压测机：本地 Mac
- 网络条件：

## 3. 测试目标

- 100 concurrent virtual users。
- Not 100 QPS。
- Duration：
- Scenario mix：

## 4. 测试场景

- Portal public。
- Portal API。
- Portal admin static shell。
- Achievement public。
- Achievement API。

Excluded scenarios:

- 注册、审核、拒绝、创建用户、密码修改。
- 真实邮件。
- 连续错误登录和 lockout 阈值触发。
- 上传、EICAR、ClamAV worker。
- destructive writes。

## 5. 验收阈值

- 5xx = 0。
- total error rate < 0.5%。
- core API p95 < 800ms。
- page/html p95 < 1000ms。
- p99 < 1500ms。
- CPU peak < 70%。
- memory no sustained growth。
- no DB connection exhaustion。

## 6. k6 Summary

粘贴 k6 summary。

```text

```

## 7. 服务器资源

粘贴 `server-readonly-snapshot.sh` 或 `docker-stats-snapshot.sh` 摘要。

```text

```

## 8. 日志检查

- Nginx error log：
- API logs：
- 502/504/5xx 统计：

```text

```

## 9. 风险与限制

- 本次不覆盖批量注册、邮件、上传、ClamAV 扫描。
- 本次不等于安全渗透测试。
- 本次不等于最大容量测试。
- 本次不等于 SLA 承诺。
- 手机浏览器或运营商网络侧备案/代理/DNS 行为可能影响终端访问体验，但不代表应用服务端性能。

## 10. 附录

- k6 script：
- command：
- commit：
- snapshot paths：
