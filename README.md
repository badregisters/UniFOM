# UniFOM

多平台代理客户端配置统一仓库。  
Unified repository for multi-client proxy configurations.

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
