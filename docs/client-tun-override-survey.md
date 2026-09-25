# 客户端配置遵循度调研：`tun:` / `dns:` / `sniffer:` 等全局字段

## 目的

`clash/src/platform/mihomo.yaml` 里的全局字段（`tun:`、`dns:`、`sniffer:`、`geo-*` 等）假设"客户端会原样把 yaml 交给 mihomo 内核解析"。但几乎每个打包客户端都有自己的 App 级设置 UI（网络栈选择、DNS 接管开关、VPN 权限……），会在内核解析之前或之后对配置做二次加工。本调研逐个查证：本仓库 yaml 里写的这些字段，在实际跑起来的客户端上，哪些是真被读取生效的，哪些是被无视/覆盖的。

**方法论**：只认一手源码和官方文档，不凭经验推断。每条结论都标了文件路径、行号或函数名；查不到实现细节的，明确写"未查证"而不是拍脑袋填。所有仓库都是活跃开发中的开源项目，行为可能随版本变化——本文档记录的是下方"查证时间与版本"里锁定的那个 commit 的状态。

## 查证时间与版本

| 日期 | 2026-09-24 ~ 2026-09-25 |
|---|---|

| 仓库 | 分支 | commit |
|---|---|---|
| `vernesong/OpenClash` | `master` | `c3a33c1` |
| `TokenPLS/Hako-Client` | `main` | `62aa2f2` |
| `TokenPLS/Hako`（Hako 核心） | `main` | `7ea70d1` |
| `MetaCubeX/ClashMetaForAndroid`（CMFA） | `main` | `559594d` |
| `chen08209/FlClash` | `main` | `c7be702` |
| `chen08209/Clash.Meta`（FlClash 的 mihomo fork） | `FlClash` | `d0c8d44` |
| `KaringX/clashmi`（Clash Mi） | `main` | `9f89d3f` |
| `MetaCubeX/mihomo`（上游内核） | `Alpha` | `8d57a8c` |

---

## 结论先行：一条贯穿所有客户端的规律

**没有一个客户端会把 yaml 的 `tun:` 段直接交给内核用。** 开 TUN/VPN 接口在每个平台上都是需要 OS 授权的敏感操作（OpenWrt 防火墙、iOS NetworkExtension、Android VpnService），每个客户端都不能让一份不受自己控制的订阅文件替用户做"要不要劫持 DNS、要不要全量隧道"这种决定，所以这段必须由 App 自己的设置 UI 兜底。

`dns:`/`sniffer:`/`geo-*` 等非 TUN 字段的命运则分化很大：有的客户端原样转发给内核（Hako、CMFA、FlClash 桌面端），有的会整段/按字段替换（OpenClash、ClashMi 开启"覆写"时）。

---

## OpenClash（Mihomo 插件，跑在 OpenWrt 路由器上，如 R2S）

**机制：Ruby 脚本在启动时逐字段重写运行 YAML**

处理脚本是 `luci-app-openclash/root/usr/share/openclash/yml_change.sh`，运行时读取约 48 个 UCI（LuCI 配置）参数，对拿到的 YAML 做原地修改后再交给内核。

### 无条件失效（不管 UCI 怎么配，我们写的值都不算）

| 字段 | 覆盖方式 | 源码位置 |
|---|---|---|
| `tun:` 整段 | `Value['tun'] = {enable:true, stack:stack_type, device:'utun', dns-hijack:['127.0.0.1:53'], endpoint-independent-nat:true, auto-route:false, auto-detect-interface:false, auto-redirect:false, strict-route:false, disable-icmp-forwarding:false}` —— 整体赋值，只有 `stack` 从 UCI `stack_type` 读；`stack_type` 本身如果 UCI 里是空值，回退默认是 `"system"` 不是 `gvisor` | `yml_change.sh:519-525`；`stack_type` 溯源见 `yml_change.sh:29-32` + `init.d/openclash:3541,3619-3624`（正是这次 R2S 卡顿排查定位到的字段） |
| `sniffer:` 整段（含我们的 `skip-domain` 12306 规则、`sniff.QUIC.ports` 等） | `Value['sniffer'] = sniffer_config`，`sniffer_config` 是独立构造的字典，跟 yaml 无关；skip-domain 固定为 `[Mijia Cloud, dlg.io.mi.com, +.oray.com, +.sunlogin.net, +.push.apple.com]`（**没有 12306**）；QUIC 端口固定 `[443]`（我们写的是 `[443,8443]`）；还会额外注入 `force-domain: [+.netflix.com, +.nflxvideo.net, +.amazonaws.com, +.media.dssott.com]`（我们的 yaml 根本没设这个字段） | `yml_change.sh:503-511` |
| `dns.ipv6` / `dns.enhanced-mode` / `dns.fake-ip-range` / `dns.listen` / `dns.respect-rules` | 逐个从 UCI 强制写入 | `yml_change.sh:486,490-496,499-500` |
| `allow-lan` / `bind-address` / `external-controller` | 固定值 | `yml_change.sh:418-421` |
| `mode` / `log-level` / `port` / `socks-port` / `redir-port` / `tproxy-port` | 固定来自 UCI 端口与模式设置 | `yml_change.sh` 前段（端口/模式赋值） |
| `profile.store-selected` | 固定 `true` | `yml_change.sh:532` |

### 条件性失效（取决于 OpenClash 面板上某个开关，需用户自己去查）

| 字段 | 触发条件 |
|---|---|
| `dns.nameserver` / `fallback` / `default-nameserver` / `proxy-server-nameserver` / `direct-nameserver` / `nameserver-policy` | 仅当面板「自定义 DNS」（UCI `enable_custom_dns`）开着时才被整体替换/追加；关闭时我们的三层 DNS 架构原样生效 | `yml_change.sh:556-639` |
| `geox-url.*` | 仅当面板「GEO 数据库」手动填了自定义下载地址时，对应那一项才被覆盖；否则我们写的 MetaCubeX/meta-rules-dat 地址原样生效 | `yml_change.sh:471-482` |

### 真正生效

`geo-auto-update` / `geo-update-interval`（`yml_change.sh` 全文搜索，无任何覆盖代码碰这两个字段）、`dns.direct-nameserver-follow-policy`（同样未被碰，且在 mihomo 源码里真实驱动 `DirectResolver.policy`，见下方 mihomo 小节）、`tcp-concurrent` / `unified-delay`（`yml_change.sh:451-452` 只会往 `true` 改，不会覆盖成 `false`，我们写的就是 `true`，结果一致）。

---

## Clash by Hako（iOS / macOS / tvOS，mihomo 核心自建）

**机制：核心自己维护一份「配置偏差登记表」**（`bind/hako/config_deviations.go`），每条偏差都带 `field`/`category`（`stripped`/`forced`/`unavailable`）/`reason`/`mechanism`/`source`，比前两个客户端都更容易查证——直接读登记表即可，不用反推。

### 无条件失效

| 字段 | 效果 | 依据 |
|---|---|---|
| `redir-port` | 不开监听 | `deviationUnavailable`——"App 沙盒不允许打开 redirect 所需的系统设施"，源自 `/System/Library/Sandbox/Profiles/application.sb` |
| `tproxy-port` | 不开监听 | `deviationUnavailable`——"透明代理是纯 Linux 设施" |
| `tun.auto-route` | 永远 `false` | `deviationForced`，无条件——"路由由 Apple 层（`NEPacketTunnelNetworkSettings`）装，核心侧路由开关无事可做" |
| `tun.auto-detect-interface` | 永远 `false` | 同上，出口网卡由 Extension 自己决定 |
| `geo-auto-update` | 永远 `false` | `deviationForced`，无条件——**不是 Apple 限制，是 Hako 自己的产品设计**：GEO 数据由 App 预先下载好交给 Core |
| `geo-update-interval` | 完全无用 | 跟着上一条，没有周期下载器在跑 |
| `dns.listen-routing-mark` | 不生效（我们没设，仅供对照） | `SO_MARK` 是 Linux socket 选项，Apple SDK 没有 |

### 条件性失效

| 字段 | 触发条件 |
|---|---|
| `allow-lan: true` | 仅当用户没在 App 里开「局域网共享」权限时被摘掉；权限一旦授予即生效 |
| `tun.stack: gvisor` | 仅当「Include All Networks」开关是开的才强制成 `gvisor`；关闭时我们写的值就是我们写的值（我们写的本来就是 `gvisor`，所以对我们没有可见影响，但这条对将来想换 `system`/`mixed` 有意义） |
| `tun.dns-hijack` | 若写的值"已经等效于劫持全部 DNS"就不算偏差；我们写的 `[any:53, tcp://any:53]` 满足这个条件，实质等效，不用改 |

### 名义 forced、实际对我们无影响

`unified-delay`、`profile.store-fake-ip`、`dns.enable` 三条在登记表里标了 `deviationForced`，但源码逻辑是"仅当用户没写这个字段时才强制"（`defaultOnly: true`）——既然我们显式写了期望值，源码原话是"an explicit true or false is always honoured"，对我们来说是真实生效的。

### 真正生效

`sniffer:` 整段（含 12306 那两条）、`dns:` 段除上述几个字段外的全部（`nameserver`/`fallback`/`default-nameserver`/`proxy-server-nameserver`/`direct-nameserver`/`direct-nameserver-follow-policy`/`nameserver-policy`/`fake-ip-filter`/`cache-algorithm`）、`tun.strict-route`（通过 App 内路由设置的"继承/覆盖"机制映射到 `NEVPNProtocol.enforceRoutes`，不在这份"偏差"登记表里，因为它是真实可配置项而非被迫的平台限制）、`port`/`socks-port`/`mode`/`log-level`/`ipv6`（顶层）/`tcp-concurrent`/`profile.store-selected`/`geox-url.*`。

---

## Clash Meta for Android（CMFA，MetaCubeX 官方安卓客户端）

**机制：Kotlin 层用 Android `VpnService.Builder` 自己搭 TUN 设备，非 TUN 字段直接交给原生 mihomo 核心解析（`Clash.load()`），没有额外覆写层**

`TunService.kt` 的 `handleStart` 函数里，`Builder` 的全部参数（`addAddress`/`addRoute`/`setMtu`/`addDnsServer`）来自 App 自己的 `ServiceStore`（Android SharedPreferences），跟 yaml 完全无关：

```kotlin
TunModule.TunDevice(
    fd = establish()?.detachFd() ?: throw ...,
    stack = store.tunStackMode,        // 不是 tun.stack
    dns = if (store.dnsHijacking) NET_ANY else (TUN_DNS + ...),  // 不是 tun.dns-hijack
    gateway = "...", portal = "...",
)
```
（`service/src/main/java/com/github/kr328/clash/service/TunService.kt`）

`ConfigurationModule.kt` 只调用 `Clash.load(profileDir)` 把整份 yaml 交给原生核心解析——**这意味着 `dns:`/`sniffer:`/`geo-*` 等非 TUN 字段走的是原生 mihomo 解析逻辑，跟上游 mihomo 源码结论完全一致，没有额外一层覆写**，是三个 App 级客户端里最"干净"的一个。

`redir-port`/`tproxy-port`：`Builder` 代码里没有对应的监听器搭建逻辑；这两个字段在架构上就是"TUN 模式下没用"的通用死因（见开头结论），不需要额外解释为 CMFA 特有限制。

`tun:` 段其余字段（`enable`/`auto-route`/`auto-detect-interface`/`strict-route`/`dns-hijack`）：`Builder` 完全不读这些字段，全部来自 App 设置。

---

## FlClash（`chen08209/FlClash`，跨平台：macOS / Windows / Linux / Android，不含 iOS）

### 桌面端（macOS / Windows / Linux）：几乎是原生 mihomo

FlClash 自己 fork 了一份 mihomo 核心（`chen08209/Clash.Meta`，分支 `FlClash`），跟上游 `MetaCubeX/mihomo` 的 `config/config.go` 逐行 diff，**只多一行**（`SetProxyNameList(proxyList)`，跟本文档讨论的字段无关）：

```
995a996
> 	SetProxyNameList(proxyList)
```

**结论：桌面端上，我们核对过的所有 mihomo 源码结论可以直接套用，`tun:`/`dns:`/`sniffer:` 等全部字段都是原生解析行为，没有额外覆写层。**

### Android 端：跟 CMFA 同一套模式

`android/service/src/main/java/com/follow/clash/service/VpnService.kt` 的 `handleStart` 函数，`Builder` 参数全部来自 Dart 层的 `VpnOptions`（Flutter 应用自己的「网络设置」页面 `lib/views/config/network.dart`，状态源头 `lib/providers/state/system.dart` 里的 `vpnSetting`）：

```kotlin
Core.startTun(
    fd = fd, stack = options.stack,        // 不是 tun.stack
    dns = options.tunDns,                  // 不是 tun.dns-hijack, 是布尔开关 dnsHijacking
    address = options.tunAddress,
    protect = this::protect, resolveUid = this::resolveUid, resolvePackage = this::resolvePackage,
)
```

`IPV4_ADDRESS = "172.19.0.1/30"`、`MTU = 9000` 等也是硬编码常量，不读 yaml。**结论：FlClash Android 上 `tun:` 段和 CMFA 一样是摆设；其余字段走原生解析（同一份几乎未改的 mihomo fork），同样干净。**

---

## Clash Mi（`KaringX/clashmi`，iOS / macOS / Android / Windows / Linux）

**机制：Dart 层维护一份独立的 App 内设置对象（`_setting: RawConfig`），有一个「覆写」（overwrite）开关，决定这份设置替换 profile 的范围**

核心函数 `getPatchContent`（`lib/app/modules/clash_setting_manager.dart:415` 附近）：

```dart
static Future<...> getPatchContent(String profileId, bool overwrite, ...) async {
  if (Platform.isIOS || Platform.isMacOS) {
    if (_setting.Tun?.Stack != gvisor && _setting.Tun?.Stack != mips) {
      _setting.Tun?.Stack = gvisor;      // 强制
    }
  }
  _setting.DNS?.IPv6 = _setting.IPv6;
  _setting.Tun?.Inet4Address = [...];     // 无条件用 App 自己的 TUN 地址
  ...
  if (overwrite) {
    return _setting.toJson();             // Mode/DNS/Sniffer/TLS/Tun 全部用 App 内设置覆盖
  }
  return getPatchFinalContent();          // 仅 Tun 用 App 内设置, DNS/Sniffer/TLS 保留 profile 原值
}

static RawConfig defaultConfigNoOverwrite() {
  return RawConfig.by(
    Mode: _setting.Mode, MixedPort: _setting.MixedPort, LogLevel: _setting.LogLevel,
    ExternalController: _setting.ExternalController, Secret: _setting.Secret, IPv6: _setting.IPv6,
    DNS: null, NTP: null, Sniffer: null, TLS: null,   // ← null 意味着"保留 profile 自己的值"
    Tun: _setting.Tun,                                 // ← 但 Tun 从来不是 null
    ...
  );
}
```

**关键发现**：不管「覆写」开关开不开，`Tun`（含 `stack`/`Inet4Address`/`Inet6Address`）**永远是 App 自己的设置，不是 profile 的 `tun:` 段**。`Mode`/`MixedPort`/`LogLevel`/`ExternalController`/`Secret`/`IPv6`（顶层）这几个字段也是**永远**用 App 自己的值（在 `defaultConfigNoOverwrite()` 里就已经写死，不受 overwrite 开关影响）。

只有 `DNS`/`NTP`/`Sniffer`/`TLS` 这四段的命运真正取决于「覆写」开关：**关闭时保留我们 yaml 的值，开启时也变成 App 自己的设置，我们写的东西整体作废。**

---

## 补充：`ipv6` / `dns.ipv6` 开关

审计范围原本聚焦 `tun:`/`sniffer:`，漏了顶层 `ipv6:`（`RawConfig.IPv6`，控制出站是否允许走 IPv6）和 `dns.ipv6`（`RawDNS.IPv6`，控制是否解析 AAAA 记录）这两个字段。两者在 mihomo 源码里都是真实生效的字段，但客户端层面的命运跟 `tun:` 段是同一个规律：

| 客户端 | 结果 | 依据 |
|---|---|---|
| **OpenClash** | 无条件失效 | `Value['ipv6'] = enable_ipv6`，随后 `Value['ipv6'] = true if dns_ipv6` 再次强制——两次赋值均来自 UCI，跟 `dns.ipv6`（同样在 `yml_change.sh:486` 被覆盖）是同一批 UCI 驱动的字段。`yml_change.sh:447,486-487` |
| **CMFA** | 无条件失效 | `TunService.kt`：`if (store.allowIpv6) { addAddress(TUN_GATEWAY6, ...) }`——App 自己的开关，不读 yaml |
| **FlClash（Android）** | 无条件失效 | `VpnOptions.ipv6` 与 `dnsHijacking` 同一个来源（`lib/providers/state/system.dart` 的 `vpnSetting`），走 App「网络设置」页面，不是 profile |
| **Clash Mi** | 顶层 `ipv6` 无条件失效（已见前文「关键发现」）；`dns.ipv6` 视「覆写」开关而定 | `defaultConfigNoOverwrite()` 里 `IPv6: _setting.IPv6` 恒定用 App 自己的值；`DNS` 段整体是否为 `null`（即是否保留 profile 原值）才决定 `dns.ipv6` 命运，跟前文 DNS 段结论一致 |
| **Hako** | 配置值本身真实生效，但运行时是否对外声明 IPv6 隧道另有前提 | 不在偏差登记表里，我们写的值会被采纳；但 `declaresIPv6(coreOffersIPv6, physicalPathSupportsIPv6)` 还要看当前网络路径是否真的有 IPv6——写 `true` 不代表隧道一定会声明 IPv6，没有物理 IPv6 时 Hako 会自动撤回声明 |
| **FlClash 桌面端** | 真实生效 | 原生 mihomo，无覆写层 |

---

## 汇总表

| | `tun:` 段 | `redir/tproxy-port` | `dns:`/`sniffer:` 等非 TUN 字段 |
|---|---|---|---|
| **OpenClash** | 整体替换（UCI 驱动） | 固定来自 UCI 端口设置 | 大量条件覆写（取决于「自定义 DNS」等面板开关） |
| **Hako** | 逐字段强制（源码登记表可查，`strict-route` 例外，真实生效） | 沙盒禁止，不开监听 | 基本原样生效 |
| **CMFA** | App 设置驱动，yaml 段不读 | 架构性无用（TUN 模式下没有对应监听逻辑） | 原样交给原生 mihomo 解析，无额外覆写层 |
| **FlClash 桌面端** | **原生 mihomo，无覆写**（fork 与上游几乎零差异） | 架构性无用 | **原生 mihomo，无覆写** |
| **FlClash Android** | App 设置驱动，yaml 段不读 | 架构性无用 | 原样交给原生 mihomo 解析（同一份 fork） |
| **Clash Mi** | 永远是 App 设置，跟「覆写」开关无关 | 未专项查证 | 覆写关：原样生效；覆写开：全部作废 |

---

## 本仓库当前的处理决定

审计完成后评估过是否要从 `clash/src/platform/mihomo.yaml` 里删掉在所有已知客户端上都确认无效的字段（`redir-port`/`tproxy-port`/`tun.auto-route`/`tun.auto-detect-interface`）——**最终决定全部保留**：这些字段目前没有任何客户端真正读取，但保留的代价是零（多写几行 yaml，不影响任何一个客户端的实际行为），而万一将来出现新客户端、或者现有客户端改变了覆写逻辑（比如某天 OpenClash/ClashMi 决定尊重 `auto-route`），这些字段已经在那儿，不需要再补。删除换来的唯一好处是"文件更干净"，但这次调研做完之后，这份文件本身以及未来查阅这份文档的人，已经清楚知道哪些字段是死代码——不需要再靠删代码来传达这个信息。
