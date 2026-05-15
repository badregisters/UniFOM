# UniFOM — Universal FlowerCloud + oixCloud + Maying

> 原项目名 MSS（Mihomo + Shadowrocket + Stash/Surge）

多客户端代理配置统一仓库，支持 Shadowrocket（SR）、OpenClash（OC）和 Stash。

## 目录结构

```
shadowrocket/
  src/base.conf              - SR 配置源文件（纳入 git）
  dist/UniFOM.conf           - SR 可部署输出（纳入 git）

openclash/
  src/base.yaml              - OC 模板，含订阅占位符（纳入 git）

clash/
  src/secrets.yaml           - 所有机场真实订阅链接，gitignore，仅本地
  openclash/dist/UniFOM.yaml - OC 可部署输出，gitignore，仅本地
  stash/dist/UniFOM.yaml     - Stash 可部署输出，gitignore，仅本地

scripts/
  build.py                   - 合并 base.yaml + secrets.yaml → OC dist
                               同时将 SR src 复制到 SR dist

docs/
  commit-convention.md       - git commit 规范
  proxy-provider-management.md - 机场增删操作指南
```

## 构建

```bash
python3 scripts/build.py
```

## 分支策略

- `main`           : 当前发布版本（正式版或最新 RC），SR 订阅链接始终指向此分支
- `feat/stash-port`: Stash 适配，开发中；因 Stash geosite CDN 故障暂停验证，待恢复后合并 main
- `feat/*`         : 其他功能开发
- `release/*`      : 发布与 RC 稳定化

## 标签规范

- Shadowrocket : `sr-vX.Y.Z` / `sr-vX.Y.Z-rc.N`
- OpenClash    : `oc-vX.Y.Z` / `oc-vX.Y.Z-rc.N`
- Stash        : `stash-vX.Y.Z` / `stash-vX.Y.Z-rc.N`

## SR 订阅链接

**最新版（始终跟随 main 分支）**

```
https://raw.githubusercontent.com/badregisters/UniFOM/main/shadowrocket/dist/UniFOM.conf
```

注意：raw.githubusercontent.com 有 5 分钟 CDN 缓存（max-age=300），push 后稍等即可更新。

**历史版本下载**

各版本独立附件见 [Releases](https://github.com/badregisters/UniFOM/releases) 页面，正式版与 RC 版均单独存档。

---

# UniFOM — Universal FlowerCloud + oixCloud + Maying

> Previously known as MSS (Mihomo + Shadowrocket + Stash/Surge)

Unified repository for multi-client proxy configurations, supporting Shadowrocket (SR), OpenClash (OC), and Stash.

## Structure

```
shadowrocket/
  src/base.conf              - SR source of truth (in git)
  dist/UniFOM.conf           - SR deployable output (in git)

openclash/
  src/base.yaml              - OC template with placeholders (in git)

clash/
  src/secrets.yaml           - real subscription URLs for all providers, gitignored, local only
  openclash/dist/UniFOM.yaml - OC deployable output, gitignored, local only
  stash/dist/UniFOM.yaml     - Stash deployable output, gitignored, local only

scripts/
  build.py                   - merges base.yaml + secrets.yaml -> OC dist
                               also copies SR src -> SR dist

docs/
  commit-convention.md       - git commit style guide
  proxy-provider-management.md - instructions for adding/removing providers
```

## Build

```bash
python3 scripts/build.py
```

## Branching

- `main`           : current release (stable or latest RC); SR subscription URL always points here
- `feat/stash-port`: Stash port, in progress; validation paused due to Stash geosite CDN outage, pending merge to main
- `feat/*`         : other feature development
- `release/*`      : release and RC stabilization

## Tags

- Shadowrocket : `sr-vX.Y.Z` / `sr-vX.Y.Z-rc.N`
- OpenClash    : `oc-vX.Y.Z` / `oc-vX.Y.Z-rc.N`
- Stash        : `stash-vX.Y.Z` / `stash-vX.Y.Z-rc.N`

## SR Subscription URL

**Latest (always follows main branch)**

```
https://raw.githubusercontent.com/badregisters/UniFOM/main/shadowrocket/dist/UniFOM.conf
```

Note: raw.githubusercontent.com has a 5-minute CDN cache (max-age=300). Allow a short wait after pushing.

**Versioned downloads**

Individual release attachments (stable and RC) are available on the [Releases](https://github.com/badregisters/UniFOM/releases) page.
