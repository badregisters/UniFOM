# UniFOM

![version](https://img.shields.io/github/v/tag/badregisters/UniFOM?label=latest&style=flat-square)
![license](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![platform](https://img.shields.io/badge/Platform-Clash%20%7C%20Shadowrocket-lightgrey?style=flat-square)
![stash](https://img.shields.io/badge/Stash-discontinued-red?style=flat-square)

多平台代理客户端分流规则配置统一仓库 · Unified multi-client proxy traffic-splitting configurations

---

| 特性 | 说明 |
|:-----|:-----|
| DNS 安全 | DoH 全程加密，严格隔离境内/境外解析路径，防 DNS 泄漏与运营商劫持 |
| 精细化分流 | 金融、支付、加密货币、流媒体、VoWiFi、RDP 独立策略组，减少误判 |
| 节点防抖 | 自动测速 50ms 容差 / 地区组 75ms / AI 专用 Non-HK 组 100ms 高容差 |
| 冷启动生存 | GitHub 域名硬编码 + 多级 DNS 兜底（nameserver-policy → fallback），弱网维持基础可用 |
| 工业化规则集 | GEOSITE/GEOIP 优先，按需混用 BM7 / Loyalsoldier / ACL4SSR |
| 多平台统一 | Shadowrocket、Mihomo (OpenClash)、Stash 共享规则体系，差异仅在平台头部 |
| 在线生成器 | 订阅链接纯浏览器内处理，不经过任何服务器，无泄露风险 |

---

## 快速开始

**在线生成（推荐）**：填写机场订阅链接后直接在浏览器内生成，订阅链接不经过任何服务器

**[→ 在线生成配置 / Generate Config](https://badregisters.github.io/UniFOM/)**

**Shadowrocket 预构建版**：节点自举区含示例机场域名，不影响使用，可直接导入；如需替换域名，使用上方在线生成器或手动修改

**[→ UniFOM.conf](https://github.com/badregisters/UniFOM/releases/download/sr-v1.2.0/UniFOM.conf)**

**本地构建（Clash）**：
1. 复制 `clash/src/secrets.example.yaml` → `clash/src/secrets.yaml`，填写机场订阅链接
2. `pip install -r requirements.txt && python3 scripts/build.py`
3. 输出文件分别位于 `clash/openclash/dist/` 和 `clash/stash/dist/`

---

## 策略组

### 核心

| 策略组 | 类型 | 说明 |
|:-------|:----:|:-----|
| 🚀 节点选择 | select | 主入口，手动选择或自动测速 |
| 📡 自动测速 | url-test 50ms | 全地区节点中最优选 |
| 🎛️ 手动切换 | select | 全量节点手动选 |
| 💰 省流节点 | url-test 75ms | 过滤 0.1x / 1x 倍率节点 |
| 🗺️ Non-HK | url-test 100ms | 排除香港节点，AI 专用（规避 OpenAI 封锁） |
| 🐟 漏网之鱼 | select | 未匹配流量的最终 fallback |
| 🎯 全球直连 | select | 强制直连 |
| 🛑 广告拦截 | select | 默认 REJECT |

### 地区

| 🇭🇰 香港 | 🇹🇼 台湾 | 🇯🇵 日本 | 🇰🇷 韩国 | 🇸🇬 狮城 | 🇺🇸 美国 | 🇬🇧 英国 | 🇲🇾 马来 | 🇺🇳 小众 |
|:------:|:------:|:------:|:------:|:------:|:------:|:------:|:------:|:------:|
| url-test 75ms | url-test 75ms | url-test 75ms | url-test 75ms | url-test 75ms | url-test 75ms | url-test 75ms | url-test 75ms | select |

### 服务

| 策略组 | 默认节点 | 类别 |
|:-------|:---------|:-----|
| 🤖 AI 服务 | Non-HK | AI |
| ▶️ 油管视频 | 节点选择 | 流媒体 |
| 🎥 奈飞视频 | 节点选择 | 流媒体 |
| 📱 TikTok | 节点选择 | 流媒体 |
| 🎧 Spotify | 香港节点 | 流媒体 |
| 🌍 国外媒体 | 节点选择 | 流媒体 |
| 📺 哔哩哔哩 | 全球直连 | 国内媒体 |
| 🌏 国内媒体 | 全球直连 | 国内媒体 |
| 📺 巴哈姆特 | 台湾节点 | 流媒体 |
| 🎶 网易音乐 | 全球直连 | 国内媒体 |
| ✈️ 电报消息 | 美国节点 | 社交 |
| 🍎 苹果服务 | 全球直连 | 平台 |
| 🪟 微软服务 | 全球直连 | 平台 |
| ☁️ 微软云盘 | 全球直连 | 平台 |
| 🎮 游戏平台 | 香港节点 | 游戏 |
| 🏦 香港金融 | 香港节点 | 金融 |
| 🅿️ PayPal | 全球直连 | 金融 |
| 🦉 Wise | 全球直连 | 金融 |
| 🪙 Crypto | 狮城节点 | 金融 |
| 📞 VoWiFi | 全球直连 | 通话 |
| 🖥️ FXRDP | 全球直连 | 远程桌面 |
| 📢 谷歌FCM | 节点选择 | 推送 |
| 📇 HTTPDNS | REJECT | 安全 |

---

## 规则优先级

| # | 类别 | 说明 |
|--:|:-----|:-----|
| 1 | 传输层基础 | Apple APNs、Google/Cloudflare DNS IP 段 |
| 2 | 冷启动保障 | GitHub 域名硬编码（规则集拉取前生效） |
| 3 | VoWiFi 专道 | SIP/IKEv2/ePDG 端口与域名 |
| 4 | 内网直连 | RFC 1918 私有地址 + UnBan 误杀恢复 |
| 5 | 游戏平台 | Activision、Hoyoverse、Ubisoft 等硬编码 |
| 6 | 金融 / 支付 | Wise、PayPal、港银、Crypto 规则集 |
| 7 | 自定义覆写 | RDP 端口、HTTPDNS 拦截、AI 精准域名 |
| 8 | 腾讯/阿里 ASN | 国内厂商海外托管 IP 强制直连 |
| 9 | HTTPDNS 拦截 | 国内厂商 DNS IP 段封锁 |
| 10 | 地理锁定服务 | Truth Social 美区强制 |
| 11 | 规则集挂载 | FCM、Telegram、AI、Apple、微软、流媒体等 |
| 12 | GFW 列表 | ProxyGFWlist |
| 13 | 国内媒体 | ChinaMedia、GEOSITE:cn、.cn 后缀 |
| 14 | GeoIP CN | 中国大陆 IP 段直连 |
| 15 | 漏网之鱼 | 未匹配流量 |

---

## 目录结构

```
clash/
  src/
    base.yaml              - 共享规则集 / 代理提供商 / 策略组（所有 Clash 平台通用）
    secrets.yaml           - 订阅链接，已 gitignore，仅本地使用
    platform/
      mihomo.yaml          - Mihomo (OpenClash) 专属头部：端口、TUN、Geo、嗅探、DNS
      stash.yaml           - Stash (Clash Premium) 专属头部：端口、TUN、嗅探、DNS
  openclash/dist/          - OC 可部署输出，已 gitignore，仅本地使用
  stash/dist/              - Stash 可部署输出，已 gitignore，仅本地使用

shadowrocket/
  src/base.conf            - SR 配置源文件（纳入 git 管理）
  dist/UniFOM.conf         - SR 可部署输出（纳入 git 管理）

scripts/
  build.py                 - 拼接平台头部 + base.yaml，注入订阅信息；同步生成 SR dist
```

## 分支策略

- `main`      : 稳定版
- `feat/*`    : 功能开发
- `release/*` : 发布与 RC 稳定化

## 版本标签

- Shadowrocket : `sr-vX.Y.Z` / `sr-vX.Y.Z-rc.N`
- OpenClash    : `oc-vX.Y.Z` / `oc-vX.Y.Z-rc.N`
- Stash        : `stash-vX.Y.Z` — 最终版本 `stash-v1.2.0`，已停止维护

## Stash 停止维护说明

Stash 基于 Clash Premium 内核，其 DNS 架构无法满足本项目对 DNS 泄露防护的要求：境外域名的 DNS 查询无法经由代理节点发出，`follow-rule` 选项在节点地址为域名时存在不可回避的死锁。详见 [docs/dns-leak-platform-notes.md](docs/dns-leak-platform-notes.md)。

代码与历史记录完整保留，最终可用版本为 [`stash-v1.2.0`](https://github.com/badregisters/UniFOM/tree/stash-v1.2.0)。

---

## 致谢

- [a-nomad](https://github.com/colin-chang/YouTubeResources) — 配置理念与 DNS 泄漏防护方案的核心参考
- [blackmatrix7](https://github.com/blackmatrix7/ios_rule_script)
- [Loyalsoldier](https://github.com/Loyalsoldier/surge-rules)
- [ACL4SSR](https://github.com/ACL4SSR/ACL4SSR)
- [SKK.moe](https://ruleset.skk.moe)
