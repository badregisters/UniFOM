# MSS

多客户端代理配置统一仓库，支持 Shadowrocket 和 OpenClash。

## 目录结构

```
shadowrocket/
  src/base.conf          - SR 配置源文件（纳入 git）
  dist/UniFOM.conf       - SR 可部署输出（纳入 git）

openclash/
  src/base.yaml          - OC 模板，含订阅占位符（纳入 git）
  src/secrets.yaml       - 真实订阅链接，gitignore，仅本地
  dist/UniFOM.yaml       - OC 可部署输出，gitignore，仅本地

clash/
  src/platform/stash.yaml - Stash 配置源文件（纳入 git，feat/stash-port 分支）
  stash/dist/UniFOM.yaml  - Stash 可部署输出，gitignore，仅本地

scripts/
  build.py               - 合并 base.yaml + secrets.yaml → dist/UniFOM.yaml
                           同时将 SR src 复制到 dist
```

## 构建

```bash
python3 scripts/build.py
```

## 分支策略

- `main`           : 稳定版本，包含 SR 和 OC
- `feat/stash-port`: Stash 适配，开发中；因 Stash geosite CDN 故障暂停验证，待恢复后合并 main
- `feat/*`         : 其他功能开发
- `release/*`      : 发布与 RC 稳定化

## 标签规范

- Shadowrocket : `sr-vX.Y.Z` / `sr-vX.Y.Z-rc.N`
- OpenClash    : `oc-vX.Y.Z` / `oc-vX.Y.Z-rc.N`
- Stash        : `stash-vX.Y.Z` / `stash-vX.Y.Z-rc.N`

## SR 订阅链接

```
https://raw.githubusercontent.com/badregisters/MSS/main/shadowrocket/dist/UniFOM.conf
```

注意：raw.githubusercontent.com 有 5 分钟 CDN 缓存（max-age=300），push 后稍等即可更新。

---

# MSS

Unified repository for multi-client proxy configurations, supporting Shadowrocket and OpenClash.

## Structure

```
shadowrocket/
  src/base.conf          - SR source of truth (in git)
  dist/UniFOM.conf       - SR deployable output (in git)

openclash/
  src/base.yaml          - OC template with placeholders (in git)
  src/secrets.yaml       - real subscription URLs, gitignored, local only
  dist/UniFOM.yaml       - OC deployable output, gitignored, local only

clash/
  src/platform/stash.yaml - Stash config source (in git, feat/stash-port branch)
  stash/dist/UniFOM.yaml  - Stash deployable output, gitignored, local only

scripts/
  build.py               - merges base.yaml + secrets.yaml -> dist/UniFOM.yaml
                           also copies SR src -> dist
```

## Build

```bash
python3 scripts/build.py
```

## Branching

- `main`           : stable, contains SR and OC
- `feat/stash-port`: Stash port, in progress; validation paused due to Stash geosite CDN outage, pending merge to main
- `feat/*`         : other feature development
- `release/*`      : release and RC stabilization

## Tags

- Shadowrocket : `sr-vX.Y.Z` / `sr-vX.Y.Z-rc.N`
- OpenClash    : `oc-vX.Y.Z` / `oc-vX.Y.Z-rc.N`
- Stash        : `stash-vX.Y.Z` / `stash-vX.Y.Z-rc.N`

## SR Subscription URL

```
https://raw.githubusercontent.com/badregisters/MSS/main/shadowrocket/dist/UniFOM.conf
```

Note: raw.githubusercontent.com has a 5-minute CDN cache (max-age=300). Allow a short wait after pushing.
