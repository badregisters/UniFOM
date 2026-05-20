# DNS 泄露定义与各平台支持能力说明

## 定义

本项目对「DNS 泄露」的定义如下：

> **凡是不属于「判断为国内」或「规则指定直连」的域名，其 DNS 查询请求不应经过任何国内 DNS 服务器（包括 alidns、doh.pub 等）。**

换言之，境外域名的 DNS 查询应当由代理节点在其出口网络环境中完成解析，国内 DNS 服务器不应感知这些域名的存在。

---

## 各平台实现对比

### Shadowrocket ✅

**机制：不做本地 DNS 查询**

SR 采用传统代理模式（非 fake-ip）。对于命中 PROXY 规则的域名，SR 将 `CONNECT domain:port` 直接交给代理节点处理，**本地完全不发起 DNS 查询**。域名解析由节点在其出口网络完成，国内 DNS 全程不参与。

仅 DIRECT 规则的连接会触发本地 DNS 查询，而直连目标均为国内域名，CN DoH 结果完全正确。

因此，SR 使用 CN DoH（alidns / doh.pub）作为 dns-server，仍可通过 ipleak.net 等 DNS 泄露检测。

---

### OpenClash (Mihomo) ✅

**机制：DNS 查询本身走代理**

Mihomo 支持 nameserver 的代理组标签语法：

```yaml
nameserver:
  - "https://1.1.1.1/dns-query#🚀 节点选择"
```

`#proxy-group` 标签使 DoH 请求本身经由指定代理组转发，1.1.1.1 收到的查询来自节点出口 IP，国内 DNS 服务器在整条链路中消失。配合 `direct-nameserver` 保障国内域名直连解析，实现精确隔离：

- 境外域名 → DNS 查询走代理节点 → 节点出口解析 → alidns 不可见 ✅
- 国内域名 → `direct-nameserver` 直连 CN DoH → 获得正确国内 IP ✅

此为 Mihomo 独有的扩展语法，Clash Premium 内核（Stash 所基于的版本）不支持。

---

### Surge ✅（计划支持）

**机制：加密 DNS 请求经隧道路由**

Surge 提供 `encrypted-dns-server` 配合出口路由能力，将 DoH/DoT 请求导入 VPN 隧道，效果与 Mihomo 的 `#proxy-group` 等价——DNS 查询从节点出口发出，本地 ISP 及 CN DNS 全程不可见。

Surge 同时具备更细粒度的 DNS 分流策略（local DNS mapping、domain-based routing），在 DNS 架构设计上更接近 SR，兼具 Mihomo 的隧道路由能力。

---

### Stash ❌（已放弃）

**根本限制：DNS 查询无法经由代理**

Stash 基于 Clash Premium 内核，其 DNS 模块的默认行为是「所有 DNS 请求直接发送到 nameserver，不经过任何代理」。

唯一的绕过选项 `follow-rule: true` 存在不可回避的死锁问题：

1. DNS 查询需走规则 → 命中代理规则 → 需要连接代理节点
2. 代理节点地址为域名 → 需要 DNS 解析 → 回到步骤 1

机场节点地址普遍使用域名且随时变更，无法通过 `nameserver-policy` 硬编码绕过。

**结论**：在「节点地址为域名」的现实条件下，Stash 结构性地无法满足上述 DNS 泄露定义，不存在配置层面的解法。

---

## 平台能力对比表

| 平台 | 境外域名 DNS 不经国内 | 实现机制 |
|------|:-------------------:|---------|
| Shadowrocket | ✅ | PROXY 规则不做本地 DNS，域名交给节点解析 |
| OpenClash (Mihomo) | ✅ | `nameserver: url#proxy-group`，DoH 请求走代理节点 |
| Surge | ✅ | `encrypted-dns-server` + 隧道路由 |
| Stash | ❌ | 无 DNS 代理机制，`follow-rule` 与域名节点存在死锁 |
