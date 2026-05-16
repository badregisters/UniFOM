# Changelog

## Shadowrocket

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

## OpenClash (Mihomo)

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
