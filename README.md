# UniFOM

多平台代理客户端配置统一仓库。  
Unified repository for multi-client proxy configurations.

---

面向长期使用者的精细化分流方案，核心目标：

- **DNS 安全**：DoH 全程加密，严格隔离境内/境外解析路径，防止 DNS 泄漏与运营商劫持
- **精细化分流**：金融、支付、加密货币、流媒体、VoWiFi 等场景独立策略组，减少误判
- **节点防抖**：自动测速 50ms 容差，地区组 75ms，AI 专用 Non-HK 组 100ms 高容差
- **冷启动生存**：多级 DNS 兜底（nameserver-policy → fallback），弱网下维持基础可用性
- **规则集工业化**：优先采用 GEOSITE/GEOIP，按需混用 Blackmatrix7 / Loyalsoldier 远程规则集
- **多平台统一**：Shadowrocket、OpenClash (Mihomo)、Stash 共享规则体系，差异仅在平台头部

A fine-grained traffic-splitting config for long-term users. Core goals:

- **DNS security**: DoH end-to-end, strict CN/non-CN resolution separation, prevents DNS leaks and ISP hijacking
- **Fine-grained splitting**: dedicated policy groups for finance, payments, crypto, streaming, VoWiFi, etc.
- **Node debounce**: 50 ms tolerance for auto-select, 75 ms for regional groups, 100 ms for AI (Non-HK)
- **Cold-start resilience**: multi-tier DNS fallback (nameserver-policy → fallback) for survival on weak networks
- **Industrial rule sets**: GEOSITE/GEOIP first, supplemented by Blackmatrix7 / Loyalsoldier remote rule sets
- **Unified multi-platform**: Shadowrocket, OpenClash (Mihomo), and Stash share one rule body; differences confined to platform headers

---

## 下载 / Download

由于 Clash 系 YAML 配置中硬编码了机场订阅链接，属于高敏资产，目前不提供成品下载。YAML 脱敏方案尚未确定，如有需要请下载源码自行取用。

Clash YAML configs embed subscription URLs directly and are treated as sensitive assets — no pre-built download is provided. Desensitization is not yet finalized; clone the repo and build locally as needed.

Shadowrocket 配置不含订阅信息，提供成品直接下载：  
The Shadowrocket config contains no subscription data and is available for direct download:

**[UniFOM.conf](https://raw.githubusercontent.com/badregisters/UniFOM/main/shadowrocket/dist/UniFOM.conf)**

---

## 目录结构 / Structure

```
clash/
  src/
    base.yaml              - 共享规则集 / 代理提供商 / 策略组 (所有 Clash 平台通用)
                             shared rules / providers / groups (all Clash platforms)
    secrets.yaml           - 订阅链接，已 gitignore，仅本地使用
                             subscription URLs, gitignored, local only
    platform/
      mihomo.yaml          - Mihomo (OpenClash) 专属头部: 端口、TUN、Geo、嗅探、DNS
                             Mihomo (OpenClash) header: port, tun, geo, sniffer, dns
      stash.yaml           - Stash (Clash Premium) 专属头部: 端口、TUN、嗅探、DNS
                             Stash (Clash Premium) header: port, tun, sniffer, dns
  openclash/
    dist/UniFOM.yaml       - OC 可部署输出，已 gitignore，仅本地使用
                             OC deployable output, gitignored, local only
  stash/
    dist/UniFOM.yaml       - Stash 可部署输出，已 gitignore，仅本地使用
                             Stash deployable output, gitignored, local only

shadowrocket/
  src/base.conf            - SR 配置源文件 (纳入 git 管理)
                             SR source of truth (in git)
  dist/UniFOM.conf         - SR 可部署输出 (纳入 git 管理)
                             SR deployable output (in git)

scripts/
  build.py                 - 拼接平台头部 + base.yaml，注入订阅信息；同步生成 SR dist
                             concatenates platform header + base.yaml, injects secrets;
                             also generates SR dist
```

## 构建 / Build

```bash
python3 scripts/build.py
```

## 分支策略 / Branching

- `main`      : 稳定版 / stable
- `feat/*`    : 功能开发 / feature development
- `release/*` : 发布与 RC 稳定化 / release and RC stabilization

## 版本标签 / Tags

- Shadowrocket : `sr-vX.Y.Z` / `sr-vX.Y.Z-rc.N`
- OpenClash    : `oc-vX.Y.Z` / `oc-vX.Y.Z-rc.N`
- Stash        : `stash-vX.Y.Z` / `stash-vX.Y.Z-rc.N`
