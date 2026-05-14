# MSS
Unified repository for multi-client config projects.

## Structure
```
shadowrocket/
  src/base.conf          - SR source of truth (in git)
  dist/UniFOM.conf       - SR deployable output (in git)

openclash/
  src/base.yaml          - OC template with placeholders (in git)
  src/secrets.yaml       - subscription URLs, gitignored, local only
  dist/UniFOM.yaml       - OC deployable output, gitignored, local only

stash/
  src/base.yaml          - Stash template with placeholders (in git)
  dist/UniFOM.yaml       - Stash deployable output, gitignored, local only

scripts/
  build.py               - merges base.yaml + secrets.yaml -> dist/UniFOM.yaml
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
