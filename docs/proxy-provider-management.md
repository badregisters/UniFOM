# Proxy Provider Management

## Remove a Proxy Provider

Example: removing Maying. 5 files to update:

| File | Location | Action |
|------|----------|--------|
| `openclash/src/secrets.yaml` | find the entry | delete line |
| `clash/src/base.yaml` | `[proxy-provider-subscriptions]` | delete entire provider block |
| `clash/src/base.yaml` | `[proxy-provider-direct-domains]` | delete subscription domain rule |
| `clash/src/base.yaml` | `[proxy-provider-groups]` | remove from all `use:` lists |
| `shadowrocket/src/base.conf` | `[proxy-provider-direct-domains]` | delete subscription domain rule |
| `scripts/build.py` | `replacements` dict | delete corresponding placeholder line |

Then rebuild:
```bash
python3 scripts/build.py
```

---

## Add a Proxy Provider

Example: adding NewProvider. Same 6 files:

| File | Location | Action |
|------|----------|--------|
| `openclash/src/secrets.yaml` | append | add `NewProvider: "https://actual-url"` |
| `clash/src/base.yaml` | `[proxy-provider-subscriptions]` | add provider block with `YOUR_NEWPROVIDER_URL` placeholder |
| `clash/src/base.yaml` | `[proxy-provider-direct-domains]` | add subscription domain direct rule |
| `clash/src/base.yaml` | `[proxy-provider-groups]` | add to all regional `use:` lists |
| `shadowrocket/src/base.conf` | `[proxy-provider-direct-domains]` | add subscription domain direct rule |
| `scripts/build.py` | `replacements` dict | add `"YOUR_NEWPROVIDER_URL": secrets.get("NewProvider", "")` |

Then rebuild:
```bash
python3 scripts/build.py
```

---

## Notes

- `secrets.yaml` contains real subscription URLs, local only, never commit to git
- `openclash/dist/UniFOM.yaml` and `stash/dist/UniFOM.yaml` are build output, local only, never commit to git
- `shadowrocket/dist/UniFOM.conf` contains no secrets, committed to git normally
- Maying is SSR protocol, appears only in manual-select and budget-node groups, not in regional groups
- OC and Stash share `clash/src/base.yaml` — edit once, both platforms updated on next build
- Stash requires v3.0+ for AND/OR/NOT logical rules used in the shared base
