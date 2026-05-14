# Proxy Provider Management

## Add / Remove a Proxy Provider

Edit **`clash/src/secrets.yaml`** only, then rebuild.

### Simple entry (regional + manual groups)
```yaml
NewProvider: "https://subscription-url"
```

### Extended entry (manual-only groups, e.g. SSR providers)
```yaml
NewProvider:
  url: "https://subscription-url"
  groups: manual
```

Then rebuild:
```bash
python3 scripts/build.py
```

That's it. `base.yaml` and `build.py` do not need to be touched.

---

## How it works

`build.py` reads `clash/src/secrets.yaml` and injects three sections into `clash/src/base.yaml` at build time:

| Marker in base.yaml | Generated content |
|---|---|
| `# [GENERATED: proxy-providers]` | Full `proxy-providers:` block with URLs from secrets |
| `[__USE_regional__]` | Provider names with `regional` in groups |
| `[__USE_manual__]` | Provider names with `manual` in groups |
| `# [GENERATED: direct-domains]` | `DOMAIN-SUFFIX` direct rules for each provider's subscription hostname |

**Default groups** (when not specified): `regional, manual` — provider appears in all regional node groups and the manual-select group.

**`groups: manual`** — provider appears only in 🎛️ 手动切换 and 💰 省流节点. Use for SSR or other protocols incompatible with regional auto-select.

---

## Secondary CDN domains

Some subscription URLs proxy through a CDN whose hostname is embedded in the query string (e.g. FlowerCloud → `xmancdn.com`). These cannot be auto-derived from the URL and are kept as static rules in `base.yaml`:

```yaml
  - DOMAIN-SUFFIX,xmancdn.com,🎯 全球直连
  - DOMAIN-SUFFIX,nxonearth.com,🎯 全球直连
```

If a new provider has a secondary CDN domain, add it manually to that static block.

---

## Notes

- `clash/src/secrets.yaml` contains real subscription URLs, local only, never commit to git
- `clash/openclash/dist/UniFOM.yaml` and `clash/stash/dist/UniFOM.yaml` are build output, local only, never commit to git
- `shadowrocket/dist/UniFOM.conf` contains no secrets, committed to git normally
- SR subscription domains are managed separately in `shadowrocket/src/base.conf`
- OC and Stash share `clash/src/base.yaml` — edit once, both platforms updated on next build
- Stash requires v3.0+ for AND/OR/NOT logical rules used in the shared base
