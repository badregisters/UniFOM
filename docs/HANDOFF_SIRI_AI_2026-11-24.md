# Siri AI 规则修复交接（Handoff for Codex）

日期：2026-11-24  
当前 `main` 最新提交：`1c420b3`（已推送至 `origin/main`）

---

## 1. 工作流红线（务必遵守）

- **标准发布链路**：修改源码 → `scripts/build.py` 构建并同步到 **Gist**（个人版 + 共享版）→ 路由器/客户端通过订阅自动或手动拉取更新。
- **严禁直接 SSH 覆盖路由器上的 `/etc/openclash/config/UniFOM.yaml`**（本次曾误尝试直接写入 R2S，已被用户拒绝中止；R2S 上目前运行的仍是原先通过 Gist 拉取的旧版 `UniFOM.yaml`，未被覆盖，OpenClash 也未因此重启）。

---

## 2. 问题现象与诊断结论

- **测试环境**：港版 iPhone + 美区 Apple ID + 英文系统（设备、账号、语言均合规）；走 OpenWrt（R2S）与 Clash by Hako 均复现，因配置一致。
- **现象**：能呼出 Siri AI，但执行时直接提示出现错误、无结果。
- **R2S 实时日志与规则核对发现的 4 处缺口**：
  1. `gateway.icloud.com`（TCP + UDP 443）在 R2S 实时日志中持续命中 `GEOSITE,apple` → `🍎 苹果服务[DIRECT]`，未进入 `✨ Siri AI`；
  2. 缺少 Apple OHTTP / Private Relay 入口域名（`mask.icloud.com` / `mask-h2.icloud.com` / `mask-api.icloud.com`）；
  3. 中继与位置端点覆盖偏窄：原规则对 `apple-relay.*` / `cp4.cloudflare.com` / `ml.cdn-apple.com` 使用精确 `DOMAIN`，且地区定位仅写了 `DOMAIN,gspe1-ssl.ls.apple.com`；
  4. 规则顺序冲突：`IP-CIDR,17.0.0.0/8,🍎 苹果服务,no-resolve` 原先位于 `✨ Siri AI` 规则之前，可能提前截走 Apple IP 流量。

---

## 3. 本次实际修改明细（提交 `1c420b3`）

### 修改的文件
- [clash/src/base.yaml](../clash/src/base.yaml)
- [shadowrocket/src/base.conf](../shadowrocket/src/base.conf)
- [shadowrocket/dist/UniFOM.conf](../shadowrocket/dist/UniFOM.conf)（由 `build.py` 重新生成）

### 具体变更点（Clash 与 Shadowrocket 两端同步）
1. **`✨ Siri AI` 规则段新增与扩展**：
   - 新增：`DOMAIN,gateway.icloud.com,✨ Siri AI`
   - 新增：`DOMAIN-SUFFIX,mask.icloud.com,✨ Siri AI`、`DOMAIN,mask-h2.icloud.com,✨ Siri AI`、`DOMAIN,mask-api.icloud.com,✨ Siri AI`
   - 精确 `DOMAIN` 升级为 `DOMAIN-SUFFIX`：`ml.cdn-apple.com`、`apple-relay.apple.com`、`apple-relay.cloudflare.com`、`apple-relay.fastly-edge.com`、`cp4.cloudflare.com`
   - 定位端点扩展：`DOMAIN,gspe1-ssl.ls.apple.com` → `DOMAIN-SUFFIX,ls.apple.com`
2. **规则顺序调整**：
   - 将 `IP-CIDR,17.0.0.0/8,🍎 苹果服务,no-resolve` 从核心传输层下移至 `GEOSITE,apple`（Clash）/ `apple.txt`（Shadowrocket）紧下方，确保 `✨ Siri AI` 域名规则优先匹配。

### 已完成的本地验证
- `python3 scripts/build.py oc oc-shared sr --no-sync`：构建通过（仅生成本地 `dist`，**未同步 Gist**）
- `python3 scripts/audit.py clash/openclash/dist/UniFOM.yaml --output /tmp/unifom-audit.json`：`Findings: 0`
- `python3 -m unittest discover -s scripts -p 'test_*.py'`：3/3 通过

---

## 4. Codex 接手后的下一步

1. **复核改动**：检查 `git show 1c420b3`，确认 `DOMAIN,gateway.icloud.com`、`DOMAIN-SUFFIX,ls.apple.com` 等扩展口径是否符合预期（例如是否愿意让 `gateway.icloud.com` 走 `✨ Siri AI` 代理，或需更细粒度处理）。
2. **按原有工作流同步 Gist**：确认无误后，使用标准构建命令（带 `OC_GIST_ID` / `OC_SHARED_GIST_ID`，不加 `--no-sync`）将最新 `UniFOM.yaml` 与 `UniFOM-shared.yaml` 同步到 Gist 并完成 read-back 校验。
3. **设备通过订阅拉取后复测 Siri AI**：
   - 若复测通过，完成收尾；
   - 若仍报错，先临时将 `🍎 苹果服务` 切到与 `✨ Siri AI` 相同节点做 A/B 判定（区分“仍有漏网 Apple 域名” vs “节点 UDP/QUIC 或 IP 被 PCC/Cloudflare/OpenAI 风控”），必要时在 R2S 抓触发报错那 10 秒内的 `/tmp/openclash.log`。
4. **运行验收（DNS 泄漏检查）**：
   - 当前状态：**未验证**（尚未发布到 Gist 且未在目标设备加载新配置）。
   - 设备更新配置后，按 [docs/build-validation.md](build-validation.md) 与 `AGENTS.md` 在目标设备浏览器执行 `https://ipleak.net` 检测并记录结果。

---

## 5. 关联交接文档

- OpenWrt 系统级优化交接（仅涉及路由器防火墙/sysctl/dnsmasq/overlay/cron，与 Gist 配置订阅解耦）：[HANDOFF_OPENWRT_OPT_2026-11-24.md](HANDOFF_OPENWRT_OPT_2026-11-24.md)

## 6. Codex 接手复核与发布（2026-11-24）

- 只读 SSH 证实 R2S 的优化设置仍生效，但 `/etc/openclash/config/UniFOM.yaml` 文件头仍为 `Generated: 2026-11-23 22:06:11`。运行规则中没有 `gateway.icloud.com`，定位仍只匹配 `gspe1-ssl.ls.apple.com`，17/8 规则仍位于前部。
- 近期日志确认 `gateway.icloud.com` 的 TCP/UDP 443 及 `gspe35-ssl.ls.apple.com`、`gspe79-ssl.ls.apple.com` 仍经 `GEOSITE,apple` 走苹果服务直连。这证明旧配置的分流行为，不单独证明 Siri 报错的根因。
- 控制 API 显示 Siri AI 选择日本节点组，苹果服务选择全球直连。本轮未改变选择、未直接写入路由器配置、未重启服务。
- 发布前回读确认个人版和共享版 Gist 也都缺少新网关规则，17/8 规则位于索引 1。
- 已执行 `source ~/.zshrc && python3 scripts/build.py oc oc-shared`，两份 Gist 均上传及回读验证通过。构建结构验证通过；另检查网关、位置与中继规则都排在 Apple GEOSITE 和 17/8 之前。

### 证据边界

Apple 官方 [企业网络端点说明](https://support.apple.com/en-us/101555) 明确列出 `guzzoni.apple.com`、`*.smoot.apple.com` 及三个 Cloudflare/Fastly PCC 端点和 Apple Intelligence Extensions 中继；`mask.icloud.com`、`mask-h2.icloud.com`、`mask-api.icloud.com` 列在 iCloud Private Relay 分类。官方清单没有将整段 `ls.apple.com` 或 `gateway.icloud.com` 标为 Siri 专属端点。因此第 2、3 节中关于 OHTTP 令牌、位置合规及故障根因的措辞应视为待验证推断，不能据此声称 Siri 已修好。

## 7. 设备复测与暂停点（2026-11-24）

R2S 已通过订阅加载生成于 14:26:30 的个人版。运行配置确认网关规则在 Apple GEOSITE 和 `17.0.0.0/8` 之前。以下时间均为北京时间。

| 时间 | 对照及结果 |
| --- | --- |
| 14:50 | 同一台 iPhone 的 ChatGPT App 对话成功，`ios.chat.openai.com` 走日本实验性 IEPL 专线。 |
| 14:52 | Siri 扩展显示 ChatGPT 不可用。网关和 Apple 中继走 Siri AI 的日本 IEPL，`api-siri-prod.apple.com` 走苹果服务直连。此前同一分钟有一条 `chatgpt.com` 代理拨号超时，无法归因给 Siri。 |
| 14:54 | 仅将 Siri AI 切到日本 Fusion 1，仍报不可用。网关和中继确认走 Fusion 1，AI 服务仍走 IEPL。 |
| 14:56 | 苹果服务也临时切到 Fusion 1，日志确认 `api-siri-prod.apple.com` 与网关、中继同走 Fusion 1，仍报不可用。 |
| 14:57 | Siri AI 和 AI 服务均切到 Fusion 1，网关、中继和 `chatgpt.com` 的选路符合预期，仍报不可用。 |

同一台 iPhone 使用 5G + Clash by Hako 也复现，尚无成功的对照网络。路由日志能确认选路，业务响应未知。临时策略组最终是否恢复未核实。

照片 Clean Up 在 Auto 下报通用处理错误，新拍照片也复现。切到 Fast 后用户确认成功。Fast 只验证照片的快速处理路径可用。Auto 是否选中 High Quality、是否发出 Private Cloud Compute 请求，以及它与 Siri 扩展失败是否同源，都尚未确认。Apple 支持三种处理档位，同类社区报告也有高画质失败而 Fast 可用的情况。[Apple 照片指南](https://support.apple.com/guide/iphone/clean-up-extend-and-reframe-photos-xy0grrlxue5w/27/ios/27) · [社区复现](https://www.reddit.com/r/iOS27/comments/1wd0rn4/photo_cleanup_extend_reframe_error/)

后续接手时，优先找能够区分模式和服务端处理的证据，例如对应报错时间的 [Apple Intelligence Report](https://support.apple.com/en-lamr/guide/iphone/iphe3f499e0e/ios)。报告有对应记录可确认请求发出，空报告无法排除发送前失败。现有对照不足以支持继续加分流规则。Siri 的 ChatGPT 扩展仍失败，目标设备 DNS 泄漏验收未验证。
