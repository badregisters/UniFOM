# UniFOM
Unified repository for multi-client config projects.

## Structure
```
clash/
  src/
    base.yaml              - shared rules / providers / groups (all Clash platforms)
    secrets.yaml           - subscription URLs, gitignored, local only
    platform/
      mihomo.yaml          - Mihomo (OpenClash) header: port, tun, geo, sniffer, dns
      stash.yaml           - Stash (Clash Premium) header: port, tun, sniffer, dns
  openclash/
    dist/UniFOM.yaml       - OC deployable output, gitignored, local only
  stash/
    dist/UniFOM.yaml       - Stash deployable output, gitignored, local only

shadowrocket/
  src/base.conf            - SR source of truth (in git)
  dist/UniFOM.conf         - SR deployable output (in git)

scripts/
  build.py                 - concatenates platform header + base.yaml, injects secrets
                             also copies SR src -> dist
```

## Build
```bash
python3 scripts/build.py
```

## Branching
- main      : stable
- feat/*    : feature development
- release/* : release and RC stabilization

## Tags
- Shadowrocket : sr-vX.Y.Z / sr-vX.Y.Z-rc.N
- OpenClash    : oc-vX.Y.Z / oc-vX.Y.Z-rc.N
- Stash        : stash-vX.Y.Z / stash-vX.Y.Z-rc.N
