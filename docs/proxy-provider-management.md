# 机场管理

## 删除机场

以删除魅影为例，需更新 6 处：

| 文件 | 位置 | 操作 |
|------|------|------|
| `openclash/src/secrets.yaml` | 找到对应条目 | 删除整行 |
| `openclash/src/base.yaml` | `[proxy-provider-subscriptions]` | 删除整个 provider 块 |
| `openclash/src/base.yaml` | `[proxy-provider-direct-domains]` | 删除订阅域名直连规则 |
| `openclash/src/base.yaml` | `[proxy-provider-groups]` | 从所有 `use:` 列表中移除 |
| `shadowrocket/src/base.conf` | `[subscription-direct-domains]` | 删除订阅域名直连规则 |
| `scripts/build.py` | `replacements` 字典 | 删除对应占位符行 |

完成后重新构建：

```bash
python3 scripts/build.py
```

---

## 新增机场

以新增 NewProvider 为例，同样 6 处：

| 文件 | 位置 | 操作 |
|------|------|------|
| `openclash/src/secrets.yaml` | 末尾追加 | 添加 `NewProvider: "https://actual-url"` |
| `openclash/src/base.yaml` | `[proxy-provider-subscriptions]` | 添加含 `YOUR_NEWPROVIDER_URL` 占位符的 provider 块 |
| `openclash/src/base.yaml` | `[proxy-provider-direct-domains]` | 添加订阅域名直连规则 |
| `openclash/src/base.yaml` | `[proxy-provider-groups]` | 添加到所有地区 `use:` 列表 |
| `shadowrocket/src/base.conf` | `[subscription-direct-domains]` | 添加订阅域名直连规则 |
| `scripts/build.py` | `replacements` 字典 | 添加 `"YOUR_NEWPROVIDER_URL": secrets.get("NewProvider", "")` |

完成后重新构建：

```bash
python3 scripts/build.py
```

---

## 注意事项

- `secrets.yaml` 包含真实订阅链接，仅本地保存，禁止提交到 git
- `openclash/dist/UniFOM.yaml` 为构建产物，仅本地保存，禁止提交到 git
- `shadowrocket/dist/UniFOM.conf` 不含敏感信息，正常提交到 git
- 魅影为 SSR 协议，仅出现在手动切换和省流节点组，不加入地区节点组

---

# Proxy Provider Management

## Remove a Proxy Provider

Example: removing Maying. 6 files to update:

| File | Location | Action |
|------|----------|--------|
| `openclash/src/secrets.yaml` | find the entry | delete line |
| `openclash/src/base.yaml` | `[proxy-provider-subscriptions]` | delete entire provider block |
| `openclash/src/base.yaml` | `[proxy-provider-direct-domains]` | delete subscription domain direct rule |
| `openclash/src/base.yaml` | `[proxy-provider-groups]` | remove from all `use:` lists |
| `shadowrocket/src/base.conf` | `[subscription-direct-domains]` | delete subscription domain direct rule |
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
| `openclash/src/base.yaml` | `[proxy-provider-subscriptions]` | add provider block with `YOUR_NEWPROVIDER_URL` placeholder |
| `openclash/src/base.yaml` | `[proxy-provider-direct-domains]` | add subscription domain direct rule |
| `openclash/src/base.yaml` | `[proxy-provider-groups]` | add to all regional `use:` lists |
| `shadowrocket/src/base.conf` | `[subscription-direct-domains]` | add subscription domain direct rule |
| `scripts/build.py` | `replacements` dict | add `"YOUR_NEWPROVIDER_URL": secrets.get("NewProvider", "")` |

Then rebuild:

```bash
python3 scripts/build.py
```

---

## Notes

- `secrets.yaml` contains real subscription URLs, local only, never commit to git
- `openclash/dist/UniFOM.yaml` is build output, local only, never commit to git
- `shadowrocket/dist/UniFOM.conf` contains no secrets, committed to git normally
- Maying is SSR protocol, appears only in manual-select and budget-node groups, not in regional groups
