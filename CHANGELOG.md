# 更新日志

## Shadowrocket

### v1.3.0 (2026-09-09)
**策略组**
- `🎬 影音节点` 恢复原名 `💰 省流节点`，筛选逻辑不变
- 新增 `🐦 X` 策略组，默认香港节点（美国节点常打不开视频）
- `💰 省流节点` 更名 `🎬 影音节点`，筛选条件定为 `实验性 | 1x 倍率 | 流媒体`
- 新增 `🚄 Speedtest` 策略组，默认全球直连
- 移除 `🖥️ FXRDP` 策略组及 DST-PORT 3389 规则，RDP 改由 GEOIP 自动分流
- 移除 `🇰🇷 韩国节点`、`🇲🇾 马来节点` 策略组及对应筛选正则
- `🎮 游戏平台` 候选补充新加坡、台湾，默认香港
- `Non-HK` → `🧠 AI 节点` → `🧠 AI 服务` 更名重构，默认节点最终定为日本
- `📺 哔哩哔哩`/`🌏 国内媒体`/`🎶 网易音乐` 简化为 直连 + 节点选择 + 手动切换
- `🅿️ PayPal` 默认美国，依次英国 / 香港 / 手动

**规则修正**
- 修复原神国际服 `dispatchosglobal.yuanshen.com` 被误判直连（新增 `DOMAIN-KEYWORD,osglobal`）
- 收窄 `DOMAIN-KEYWORD,ims` → `ims.mnc`：原三字母子串匹配误伤 whimsical / claims / sims / dimsum 等
- 收窄 `DOMAIN-KEYWORD,wise` → `DOMAIN-SUFFIX,wise.com`：原误伤 otherwise / likewise / bitwise / cloudwise 等
- 规则集优先级修正：`NetEaseMusic` 提至 `ChinaMedia` 之前（原 40% 域名被抢）
- 游戏规则移除过于宽泛的 CODM 关键词

**排查结论与失败记录**
- `tun-excluded-routes` 加入 `0.0.0.0/31` 无法隐藏 iOS 状态栏 VPN 图标，已回退。
  真实原因不在配置层，而是客户端 Tunnel 设置中的 **Enforce Routes**
  （`NEVPNProtocol.enforceRoutes`）开启后按强制全量 VPN 处理，覆盖了 `excludedRoutes`。
  该属性由 App 写入系统 VPN profile，配置文件无对应项。SR 与 Clash by Hako
  共用同一套 NetworkExtension 基础设施，此结论两端通用
- 启用 `ipv6 = true` 未能解决蜂窝网络下的 IPv6 黑洞，假设被证伪，已回退

### v1.2.0 (2026-05-20)
- Rule-set CDN 迁移: Loyalsoldier 规则集全部从 jsDelivr 切换为 raw.githubusercontent.com 直链，消除 CDN 缓存延迟和封锁风险
- `🇺🇳 小众节点` 新增印度节点匹配 (印度 / 🇮🇳 / India)
- `💰 省流节点` 过滤器补充 0.1x 倍率节点
- `Non-HK` 正则修正: `US` 改为 `\bUS\b` 避免误匹配 ASUS 等字符串
- 新增 `🖥️ FXRDP` 策略组 + DST-PORT 3389 规则，远程桌面专道
- 新增 `🏦 香港金融`、`🅿️ PayPal`、`🦉 Wise` 独立策略组

### v1.1.1-rc.1 (2026-05-16)
- DNS 测试: 阿里 DoH + 腾讯 DoH; fallback 阿里/腾讯明文

### v1.1.0 (2026-05-15)
- 架构定稿，规则集持续测试优化
- 引入 Loyalsoldier/surge-rules RULE-SET，替换可等价基础规则集，保留无等价专项规则
- DNS 定稿: Cloudflare DoH + Google DoH; fallback 阿里/腾讯明文
- 修复 DNS 泄露根因: IP-CIDR 规则集在无 no-resolve 时强制触发域名解析
  - 泄露路径: 域名穿透规则链 → cncidr.txt → SR 解析域名 → fallback 明文 DNS → 运营商在移动网络透明劫持 UDP 53
  - 修复: 废弃 cncidr.txt (已由 GEOIP/ASN/域名规则集覆盖); telegramcidr.txt 加 no-resolve
- 补充苹果 Akamai CDN 直连规则 (apple.com.akadns.net, mail.me.com.akadns.net)
- 补充苹果 CDN 直连规则 (ls-apple.com.akadns.net, apple-relay.fastly-edge.com)

### v1.0.12
- 修正 BM7 订阅目录调用错位 (Surge -> Shadowrocket)，补齐底层特化拦截与局域网防线

### v1.0.11
- 废弃 ACL4SSR 全量挂载，改用 BM7，解决 iCloud 及国内长尾域名漏网问题
- 切换回 ACL4SSR (BM7 及 GEOSITE 均有覆盖及格式问题，回滚观察)

### 早期迭代
- 绝对 DNS 隔离 (国内阿里DoH / 国外 CloudFlare/Google DoH)
- Rule-Provider 异步挂载 (全量替换为 Blackmatrix7 工业级规则集)
- 策略组设置微调，按使用频率排序
- 增量注入: 高敏金融、第三方支付、加密货币及流媒体独立分流架构
- 精简冗余本地规则 (遵循原生 String 解析标准，弃用冗余域名后缀，保留 ASN)
- 修正国旗字符、编码匹配及正则逻辑
- 增量注入: VoWiFi 容灾备份通道可切换美区
- 节点防抖: 基础容差 自动测速 50ms，地区策略组 75ms，AI 用 Non-HK 独立高容差 100ms
- 妥协1: 放弃绝对 DNS 隔离思路，全面采用国内 DoH
- 妥协2: 放弃 DoH，采用国内明文 DNS 以提高弱网生存率
- 策略组 emoji 批量替换

---

## Stash

### v1.2.0 (2026-05-20) — 首个稳定版
- DNS 三层防泄露架构: primary 境外 DoH (1.1.1.1 / dns.google)，CN 域名经 nameserver-policy geosite:cn 精准路由至国内 DoH，境外域名查询不再接触 CN DoH
- nameserver-policy 升级为双 CN DoH 列表值 (alidns + doh.pub)，提高冗余性（修正历史记录: Stash 实际上支持 nameserver-policy 列表值）
- 启用 AND 复合规则 (Stash 3.0.0+ 支持): VoWiFi IKEv2/IPSec 端口匹配 + 游戏 UDP 端口分流
- 所有 IP 类规则 (GEOIP / IP-ASN / IP-CIDR) 均携带 no-resolve，彻底消除 fake-ip 模式下 IP 规则触发预解析导致的 DNS 泄露
- 继承共享规则集全部更新: 新增 🖥️ FXRDP、🏦 香港金融、🅿️ PayPal、🦉 Wise 策略组；小众节点新增印度；省流节点补充 0.1x 过滤

### v1.1.0 (2026-05-14)
- 架构定稿，从 OpenClash 配置移植，规则集与策略组保持一致
- 剔除 Mihomo 专属指令: redir-port、tproxy-port、tcp-concurrent、geo-auto-update、QUIC 嗅探、direct-nameserver
- DNS 补偿策略: nameserver-policy (geosite:cn → 阿里 DoH) + fallback (geoip:CN → 阿里/腾讯 DoH)，弥补 Stash 不支持 direct-nameserver 的缺口

---

## OpenClash (Mihomo)

### v1.4.0 (2026-09-09)
**策略组**
- `🎬 影音节点` 恢复原名 `💰 省流节点`，筛选逻辑不变
- 新增 `🐦 X` 策略组，默认香港节点（美国节点常打不开视频）
- `🎮 游戏平台` 候选补充新加坡、台湾
- 移除 `🇰🇷 韩国节点`、`🇲🇾 马来节点` 策略组及对应筛选正则
- `🧠 AI 服务` 默认节点几经调整（日本 → 台湾 → 日本），最终定为日本

**机场分层**
- 优选层 = 花云 + 墙洞；标准层 = 魅影 + 良心云
- `📡 自动测速` 改为花云 + 墙洞（原花云 + 魅影）
- 地区 fallback 组显式设 `lazy: false`，避免闲置超过 interval 后健康状态过期。
  查证 Mihomo 源码：`lazy` 非「从不检测」，而是「闲置超过一个 interval 才跳过」，
  且 `Touch` 仅在真实流量 `DialContext` 时发生；父组探测走 `Now()` 不会级联激活内层子组，
  故内层优选/标准子组无需设置。实测开销约 7MB/天

**订阅**
- 花云订阅由 SS-2022 换为 Trojan，并改用机场原始订阅直连，不再经 subconverter 转换层

**规则修正**
- 修复原神国际服 `dispatchosglobal.yuanshen.com` 被 `GEOSITE:cn` 误判直连
- 收窄 `DOMAIN-KEYWORD,ims` → `ims.mnc`：原三字母子串匹配在规则集域名池中误伤 31 个无关域名
  （whimsical / claims / sims / dimsum 等），且位置靠前会强制其走 VoWiFi 组（默认直连）
- 收窄 `DOMAIN-KEYWORD,wise` → `DOMAIN-SUFFIX,wise.com`：原误伤 39 个域名
  （otherwise / likewise / bitwise / cloudwise 等）
- `ProxyMedia` 改用 `GlobalMedia_Classical.yaml`：原 `GlobalMedia.yaml` 实为纯 IP 版
  （918 IP-CIDR + 26 keyword，0 条域名规则），与 `behavior: classical` 不匹配，
  导致 Disney+ / Hulu / HBO / Prime Video / DAZN 等无独立 GEOSITE 分类的服务
  无法进入 `🌍 国外媒体`，改后恢复
- 规则集优先级修正（括号内为修正前实测遮蔽率）：
  `category-ads-all` 提至最前（26%，244/910 条广告未拦截）、
  `google-cn` 提至 `ProxyGFWlist` 前（72%）、
  `NetEaseMusic` 提至 `ChinaMedia` 前（40%）、
  `bahamut` 提至 `ProxyMedia` 前（换 Classical 版后其含 bahamut.com.tw，不提前会 100% 遮蔽）
- GitHub 冷启动硬编码规则去重并修正来源注释（保留冗余以锁定优先级，防未来误伤）

**排查结论：iOS 隐藏状态栏 VPN 图标不属于配置层问题**
- 曾三次尝试用 `tun.route-exclude-address: [0.0.0.0/31]` 隐藏角标，均实测无效并回退。
  配置链路本身没有问题：Hako `bind/hako/tun.go` 的 `GetInet4RouteExcludeAddress()`
  确实透传该字段，Swift 侧也确实写入 `ipv4Settings.excludedRoutes`
- 真实原因是客户端 Tunnel 设置中的 **Enforce Routes** 开关（`NEVPNProtocol.enforceRoutes`）。
  按 Apple 文档，该属性「supersedes the system routing table and scoping operations by apps」，
  开启后系统按强制全量 VPN 处理，角标必然显示，`excludedRoutes` 在这一层被覆盖
- 该属性由 App 在保存 VPN 配置时写入系统 profile，**不经过 core，yaml 无任何对应字段**
  （`TunOptions` 接口仅暴露地址 / MTU / DNS / route-address / route-exclude-address /
  auto-route / strict-route）。关闭它可隐藏角标，代价是应用可绕过隧道、
  `excludeLocalNetworks` 连带失效，属防泄漏强度换观感，本项目选择维持开启
- 附带更正：`tun.strict-route` 与该开关无关，sing-box for Apple 全仓库未消费 `strictRoute`

### v1.3.0 (2026-07-12)
**地区组分层架构（本版核心）**
- 地区组由单层 `url-test` 改为两层 `fallback`：`优选`（premium 标签机场）健康检查失败后
  自动降级到 `标准`（standard 标签机场），恢复后自动切回
- 新增 `premium` / `standard` 分组标签；`次选` 更名为 `标准`
- `🧠 AI 服务`、`🏦 香港金融`、`🎮 游戏平台` 的专属标签（`ai` / `finance` / `gaming`）
  先后引入后全部撤销，改为直接复用地区分层组，减少标签体系复杂度
- `🇺🇳 小众节点` 改用 `manual` 标签，覆盖全部机场

**策略组**
- `💰 省流节点` 更名 `🎬 影音节点`，筛选逻辑几经调整（0.1x / 0.5x / 1x / 实验性 / 流媒体 / BGP）
- 新增 `🚄 Speedtest` 策略组
- 移除 `🖥️ FXRDP` 策略组及 DST-PORT 3389 规则，RDP 改由 GEOIP 自动分流
- `Non-HK` → `🧠 AI 节点` → `🧠 AI 服务` 更名与重构
- 补全空壳组导流：巴哈姆特 / 国内媒体 / 网易音乐

**构建与机场管理**
- 新增 `oc-shared` target，输出共享版 dist；build 后自动同步至 Secret Gist
- 新增 `shared_groups` 字段：仅共享版生效的分组覆盖，解决共享版地区组空壳导致
  Mihomo 加载报错（`use` 或 `proxies` 缺失）
- 新增 `full` 字段：控制机场是否纳入个人完整版，可实现「仅共享版」
- 新增 `provider_filter` 字段：按机场覆盖订阅拉取时的过滤正则
- dist 输出剥离行内注释，文件头增加生成时间
- `proxy-provider` interval 由 14400 改为 86400；health-check 改用 Cloudflare HTTPS
  端点、interval 调整为 1800

**机场**
- 移除奶昔（Nexitally）
- 墙洞（oixCloud）降级为仅手动切换，后随分层架构调整

### v1.2.0 (2026-05-20)
- DNS 架构重构: nameserver 通过 `#proxy-group` 标签强制经代理查询境外 DoH，彻底隔离 CN DoH 与境外域名
- 新增 `direct-nameserver` + `direct-nameserver-follow-policy: true`，国内域名解析走 CN DoH 直连通道
- 新增 `proxy-server-nameserver`，代理节点域名解析独立路径，避免循环解析
- nameserver-policy 沿用 Mihomo `geosite:cn,private` 复合键语法 + 双 CN DoH 列表值
- 新增 rule-providers: ProxyMedia (BM7)、Crypto_Rules (BM7)、LocalAreaNetwork，规则集覆盖面扩展
- 继承共享规则集全部更新: 新增 🖥️ FXRDP、🏦 香港金融、🅿️ PayPal、🦉 Wise 策略组；小众节点新增印度；省流节点补充 0.1x 过滤

### v1.1.0 (2026-05-13)
- 架构定稿，规则集持续测试优化
- 将可等价替换的远程规则集改为 GEOSITE:
  Apple / Microsoft / OneDrive / GoogleFCM / Telegram / OpenAi /
  YouTube / Netflix / Spotify / Epic / Steam / TikTok / Bilibili / GoogleCN / SteamCN
- 补充苹果 Akamai CDN 直连规则 (apple.com.akadns.net, mail.me.com.akadns.net)
- 补充苹果 CDN 直连规则 (ls-apple.com.akadns.net, apple-relay.fastly-edge.com)
- 苹果域名移出 fake-ip-filter，交由 direct-nameserver 处理，修复 CNAME 漏网并优化冷启动

### 早期迭代
- 绝对 DNS 隔离 (国内阿里DoH / 国外 CloudFlare/Google DoH)
- 多机场异步聚合 (FlowerCloud, oixCloud, Maying, Nexitally, LiangXin) Proxy-Provider
- Rule-Provider 异步挂载 (ACL4SSR 为主，Crypto 采用 BM7)
- 策略组设置微调，按使用频率排序
- 增量注入: 高敏金融、第三方支付、加密货币及流媒体独立分流架构
- 精简冗余本地规则
- Maying SSR 只用于手动切换以确保 VoWiFi 稳定工作
- 增量注入: VoWiFi 容灾备份通道可切换美区; respect-rules: false 降低 DNS 预解析耗时
- 节点防抖: 基础容差 自动测速 50ms，其它策略组 75ms，Non-HK for AI 独立高容差 100ms
- 妥协: 放弃绝对 DNS 隔离思路，全面采用国内 DoH
- 策略组 emoji 批量替换
- sniffer 增加 QUIC 协议，改善 UDP 分流效率，豁免米家产品的嗅探阻断
- 重构 dns，使用 Mihomo 的 direct-nameserver 建立分流防线
- 废弃部分文本型远程规则集，改用 Geosite，降低系统占用，提高查询效率及冷启动生存率
- 重新测试筛选远程规则集，混用 BM7 和 ACL4SSR
