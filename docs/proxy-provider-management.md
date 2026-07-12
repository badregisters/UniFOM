# Proxy Provider Management / 机场管理指南

## Add a Provider / 新增机场

Edit **`clash/src/secrets.yaml`** only, then rebuild. No other files need to be touched.

仅编辑 **`clash/src/secrets.yaml`**，rebuild 即可，无需改其他文件。

---

### Entry formats / 条目格式

**Simple** — regional + manual groups, no secondary CDN:
```yaml
NewProvider: "https://subscription-url"
```

**Extended** — all fields optional except `url`:
```yaml
NewProvider:
  url: "https://subscription-url"
  groups: manual,economy            # default: regional,manual
  shared_groups: manual,premium     # optional: oc-shared-only override of `groups`
  provider_filter: '(?i)(...)'      # optional: per-provider override of the fetch-time filter
  shared: true                      # include in oc-shared build; default: false
  full: true                        # include in personal oc/stash/sr build; default: true
  extra_domains: [cdn.example.com]  # secondary CDN not derivable from URL
```

**`groups`** controls which proxy groups the provider feeds. Multiple tags may be combined (comma-separated or YAML list):

| Tag | Feeds |
|---|---|
| `regional` | 📡 自动测速 |
| `manual` | 🎛️ 手动切换 |
| `economy` | 🎬 影音节点 |
| `premium` | 「优选」层 of every fallback region group (🇭🇰/🇹🇼/🇯🇵/🇰🇷/🇸🇬/🇺🇸/🇬🇧/🇲🇾) |
| `standard` | 「标准」层 of every fallback region group — auto-degrade target when 优选 health check fails |

Default when `groups` is omitted: `regional,manual`. Tiering (`premium`/`standard`) is a static declaration in `secrets.yaml`, not a real-time quality measurement — health checks only decide *when* to fall back, not *which* provider is trustworthy.

**`shared_groups`** — optional override of `groups` that applies **only** when building `oc-shared` (personal `oc`/`stash`/`sr` builds ignore it). Typical use: a provider sits in `standard` for the personal build but is the *only* `premium` provider for the shared build, e.g. when the personal `premium` provider has `shared: false` and would otherwise leave `oc-shared`'s premium tier empty.

**`provider_filter`** — optional override of the default region-tag filter (`PROVIDER_FILTER` in `build.py`) applied when fetching that provider's remote node list. Falls back to the shared default when omitted. Use when a provider's catalog needs an additional keyword match beyond plain region tagging (e.g. requiring a protocol-label substring alongside the region tag, so only a subset of that provider's nodes ever enters the local cache).

**`shared`** — include this provider in the `oc-shared` build. Default `false` (personal-only).

**`full`** — include this provider in the personal `oc`/`stash`/`sr` builds. Default `true`. Combine `full: false` + `shared: true` for a provider that should exist only in the shared distribution.

**`extra_domains`** — secondary CDN hostnames embedded in query strings or referenced during subscription fetch, not derivable from the URL hostname itself. Generates `DOMAIN-SUFFIX` direct rules in both Clash and SR configs.

---

### Rebuild / 重新构建

```bash
python3 scripts/build.py
```

---

## Remove a Provider / 删除机场

Delete the entry from `clash/src/secrets.yaml` and rebuild.

从 `clash/src/secrets.yaml` 删除对应条目，rebuild 即可。

---

## How it works / 工作原理

`build.py` reads `clash/src/secrets.yaml` and injects content into templates at build time.

### Clash (OC + Stash) — markers in `clash/src/base.yaml`

| Marker | Generated content |
|---|---|
| `# [GENERATED: proxy-providers]` | Full `proxy-providers:` block with URLs, per-provider filter, health-check |
| `[__USE_regional__]` | Provider names with `regional` in groups |
| `[__USE_manual__]` | Provider names with `manual` in groups |
| `[__USE_economy__]` | Provider names with `economy` in groups |
| `[__USE_premium__]` | Provider names with `premium` in groups |
| `[__USE_standard__]` | Provider names with `standard` in groups |
| `# [GENERATED: direct-domains]` | `DOMAIN-SUFFIX` direct rules — URL hostnames + `extra_domains` |

All `__USE_*__` markers resolve per-build: `oc-shared` uses a provider's `shared_groups` when set, otherwise falls back to `groups` — every other target (`oc`, `stash`, `sr`) always uses `groups` directly.

### Shadowrocket — markers in `shadowrocket/src/base.conf`

| Marker block | Generated content |
|---|---|
| `# [proxy-provider-direct-domains start] … end` | `DOMAIN-SUFFIX` direct rules — same hostnames as Clash |

SR subscription URLs are not written into the conf (managed in the SR app). Only the CDN hostnames needed for cold-start are injected.

---

## Notes / 注意事项

- `clash/src/secrets.yaml` — real subscription URLs; **never commit to git** (gitignored)
- `clash/openclash/dist/UniFOM.yaml`, `clash/stash/dist/UniFOM.yaml` — build output; **never commit to git** (gitignored)
- `shadowrocket/dist/UniFOM.conf` — contains no secrets; committed to git normally
- OC and Stash share `clash/src/base.yaml` — edit once, both platforms updated on next build
- Stash requires v3.0+ for AND/OR/NOT logical rules used in the shared base
