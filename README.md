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
- **Clash Universal YAML**：内置机场订阅链接，生成单一 YAML 文件即可直接导入，无需在客户端 GUI 做任何额外配置

A fine-grained traffic-splitting config for long-term users. Core goals:

- **DNS security**: DoH end-to-end, strict CN/non-CN resolution separation, prevents DNS leaks and ISP hijacking
- **Fine-grained splitting**: dedicated policy groups for finance, payments, crypto, streaming, VoWiFi, etc.
- **Node debounce**: 50 ms tolerance for auto-select, 75 ms for regional groups, 100 ms for AI (Non-HK)
- **Cold-start resilience**: multi-tier DNS fallback (nameserver-policy → fallback) for survival on weak networks
- **Industrial rule sets**: GEOSITE/GEOIP first, supplemented by Blackmatrix7 / Loyalsoldier remote rule sets
- **Unified multi-platform**: Shadowrocket, OpenClash (Mihomo), and Stash share one rule body; differences confined to platform headers
- **Clash Universal YAML**: subscription URLs are baked in at build time — the output is a single self-contained YAML ready to import, no client-side GUI setup required

---

## 下载 / Download

Clash 系 YAML 配置提供在线生成器，填写机场订阅链接后直接在浏览器内生成，订阅链接不经过任何服务器：  
Clash YAML configs are generated client-side via the online tool — subscription URLs never leave your browser:

**[→ 在线生成 Clash 配置 / Generate Clash Config](https://badregisters.github.io/UniFOM/)**

---

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

---

## 致谢 / Acknowledgment


本项目的设计理念和核心配置方案得到了 [a-nomad](https://github.com/colin-chang/YouTubeResources) 项目的深刻启发。a-nomad 项目在 Shadowrocket 配置优化、DNS 泄露防护和分流策略等方面的创新思路，为本项目提供了重要的参考价值。

在充分学习和理解 a-nomad 项目优秀实践的基础之上，根据自身的具体使用习惯、运行环境特点和实际需求，对配置方案进行了深度的定制化修改和优化迭代。这些改进不仅保留了原项目的核心优势，更加入了符合个性化场景的功能增强。

在此，特别对 a-nomad 项目及其维护者表示诚挚的感谢，感谢其为开源社区贡献的宝贵资源和灵感。


This project draws profound inspiration from the [a-nomad](https://github.com/colin-chang/YouTubeResources) project. The innovative approaches pioneered by a-nomad in Shadowrocket configuration optimization, DNS leak prevention, and fine-grained traffic splitting have provided invaluable reference for this project.

Building upon a thorough understanding of the excellent practices demonstrated by a-nomad, this project conducts in-depth customization and iterative optimization of the configuration scheme based on specific usage habits, runtime environment characteristics, and practical requirements. These improvements not only preserve the core advantages of the original project but also integrate functionality enhancements tailored to personalized scenarios.

We hereby express our sincere gratitude to the a-nomad project and its maintainers for their outstanding contributions and inspiration to the open-source community.
