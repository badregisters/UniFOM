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
  groups: manual                    # default: regional,manual
  extra_domains: [cdn.example.com]  # secondary CDN not derivable from URL
```

**`groups`** controls which proxy groups the provider feeds:

| Value | Groups |
|---|---|
| `regional, manual` (default) | All regional url-test groups + 🎛️ 手动切换 + 💰 省流节点 |
| `manual` | 🎛️ 手动切换 + 💰 省流节点 only — use for SSR or protocols incompatible with regional auto-select |

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
| `# [GENERATED: proxy-providers]` | Full `proxy-providers:` block with URLs, filters, health-check |
| `[__USE_regional__]` | Provider names with `regional` in groups |
| `[__USE_manual__]` | Provider names with `manual` in groups |
| `# [GENERATED: direct-domains]` | `DOMAIN-SUFFIX` direct rules — URL hostnames + `extra_domains` |

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
