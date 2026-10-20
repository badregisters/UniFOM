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

---

## iOS「连接助理」(Connectivity Assist) 与 OpenClash

### 现象

iPhone 插运营商卡（如 CMCC）、连的是经 OpenClash 分流的 Wi-Fi 时，若开启系统「连接助理」
（iOS 27 起由旧「无线局域网助理」更名并挪到「设置 → 无线局域网」；默认常开），系统会在
**仍显示连着 Wi-Fi 的同时**并行使用蜂窝补链路。部分 DNS 查询会直接打到运营商递归 DNS，
从不经过局域网里的 OpenClash `dns-hijack` / DHCP 下发的解析器，于是 ipleak 等检测会出现
CMCC（或其它运营商）解析器——这就是典型的 DNS 泄露。

Apple 官方说明见 [关于「连接助理」](https://support.apple.com/zh-cn/127686)：弱 Wi-Fi 时
用蜂窝改善连通性；并明确写到，若某套路由器配置（例如广告拦截）需要始终走 Wi-Fi，
**可以只对该网络关闭连接助理**。

### 为何改 OpenClash 配置解决不了

OpenClash 只能劫持**经过路由器**的流量。连接助理走蜂窝口发出的 DNS 根本不进 LAN，
因此无论 `fake-ip`、`nameserver#proxy-group`、`strict-route` 还是 `dns-hijack: any:53`，
都碰不到这条旁路。这是客户端 OS 多路径问题，不是 Mihomo 规则缺口。

社区在 Pi-hole / AdGuard Home 场景下的复现结论与此一致（见
[hagezi/dns-blocklists#11473](https://github.com/hagezi/dns-blocklists/discussions/11473)）：
仅当连接助理把查询送到运营商 DNS 时本地解析器才会被旁路；**仅转发 DNS 的分流隧道
（WireGuard / Tailscale split DNS）挡不住**，因为蜂窝侧查询从未进入隧道。

### 除全局关闭连接助理以外的办法

按「仍尽量保留连接助理、又符合本仓库 DNS 泄露定义」排序：

| 方案 | 做法 | 对 UniFOM / OpenClash 的影响 | 备注 |
|------|------|------------------------------|------|
| **仅对本 SSID 关闭连接助理** | 设置 → 无线局域网 → 点开 OpenClash 所在网络 → 关闭「对此网络使用连接助理」（文案以系统版本为准） | OpenClash 三层 DNS 继续生效 | Apple 官方为广告拦截/路由器 DNS 推荐的做法；出门用公共 Wi-Fi 仍可开全局连接助理 |
| **本机全量 TUN VPN（推荐替代）** | 在 iPhone 上开 Shadowrocket（或其它全隧道客户端）加载 UniFOM SR 配置，保持 VPN 连接 | DNS 进本机隧道，不再依赖路由器劫持；可与家宽 OpenClash 并存，注意避免无意义的双重代理（SR 侧国内直连 / 节点选择按需调） | 社区对照：**全隧道可堵住**；仅 DNS 进隧道 / split tunnel **仍会漏** |
| **蜂窝「低数据模式」** | 设置 → 蜂窝网络 → 蜂窝数据选项 → 低数据模式 | 不改路由器配置 | Apple 写明：蜂窝低数据模式下**不会使用**连接助理（国际漫游时同样不用） |
| **始终开启的加密 DNS 描述文件** | 安装系统级 DoH/DoT profile（全网络生效） | 运营商明文 DNS 消失，但查询也**不再经过** OpenClash 本地 DNS；境外域名若指向 CN DoH 仍违反本仓库定义，指向境外 DoH 则运营商仍可见「连了 1.1.1.1」的元数据 | 适合纯广告拦截场景；**不适合**想保留 OC 分流解析路径的用户 |
| **改善 Wi-Fi 覆盖** | 加 AP、调信道、减少边缘弱信号区 | 降低触发频率，非根治 | 连接助理在「Wi-Fi 慢或不可用」时更积极补蜂窝 |

### 明确无效或不足的做法

- 只改 OpenClash / UniFOM OC yaml（含 `strict-route`、加强 `dns-hijack`）
- 家里 WireGuard / Tailscale **只把 DNS 指回家**（split tunnel）
- 仅给蜂窝接口配加密 DNS、Wi-Fi 仍靠 DHCP：连接助理仍可能在「连着 Wi-Fi」时用运营商 DNS

### 验收建议

在目标 iPhone 上（已加载相关配置、流量路径与日常一致）打开 https://ipleak.net，
等 DNS detection 完成。若连接助理开启且无本机全隧道，解析器列表中出现运营商 DNS
应视为失败；关闭该 SSID 的连接助理或启用 SR 全隧道后复测，运营商解析器应消失。
浏览器自身「安全 DNS」会绕过系统解析器，记录结果时需注明其开关状态
（流程见 [build-validation.md](build-validation.md)）。
