# OpenWrt / OpenClash 多机优化交接（Handoff）

日期：2026-11-24  
基准版本：`oc-v1.5.7`（脚本提交 `af16a9e`）

---

## 1. 背景与当前进度

本次对一台运行 ImmortalWrt 24.10.6（`rockchip/armv8`，R2S 单臂旁路由）+ OpenClash `0.48.002` + `UniFOM.yaml`（v1.5.7）的路由器做了全量只读体检，排查出 6 类位于 OpenWrt 系统 / OpenClash 插件侧的隐藏设置问题（**均无需修改 `UniFOM.yaml`**）。

为便于后续推广到多台 OpenWrt（R2S / R4S 等），已将优化逻辑封装为可复用、幂等的 POSIX shell 脚本：

- 脚本路径：[scripts/optimize_openwrt.sh](../scripts/optimize_openwrt.sh)
- 适用范围：OpenWrt / ImmortalWrt + OpenClash（自动识别单臂旁路由与主路由，执行前自动备份配置到 `/tmp/openwrt-opt-backup-<timestamp>/`）

### 当前设备进度

| 设备 | 数量 | 拓扑 / 架构 | 推荐 TUN 栈 | 状态 | 备注 |
|---|---:|---|---|---|---|
| R2S #1（`192.168.30.254`） | 1 | 单臂旁路由 / `rockchip/armv8` | `system` | **路由器侧已优化并核验** | `ipleak.net` 浏览器 DNS 泄漏验收待做 |
| R2S #2、#3 | 2 | 待识别 / `rockchip/armv8` | `system` | **待执行** | 复用 `scripts/optimize_openwrt.sh` |
| R4S | 1 | 待识别 / `rockchip/armv8` | `gVisor`（4GB / ≤500M）或 `mixed`/`system`（1GB / 千兆高并发） | **待执行** | 复用 `scripts/optimize_openwrt.sh` |
| Mac mini + UTM（OpenWrt VM） | 1 | 虚拟机 / Apple Silicon + `virtio-net` | **`gVisor`（最适用）** | **待执行** | 复用 `scripts/optimize_openwrt.sh` |

---

## 2. 排查确认的 6 类问题与设计决策

以下结论经实测验证，后续接手或其他机器执行时请保持一致：

1. **防火墙 Flow Offloading 与 OpenClash TUN 冲突**
   - 关闭 `flow_offloading` 与 `flow_offloading_hw`（防止内核 `flowtable` 快速路径绕过 OpenClash 引流导致断流/卡死；Rockchip ARMv8 本身不支持硬件流卸载）。
   - 若检测到为单臂旁路由（无 `wan` 接口且 `lan.gateway` 已配置），同时关闭 `fullcone`；主路由保留原有 `fullcone` 设置。
2. **OpenClash `sniffer` 静默覆写陷阱（关键实测发现）**
   - OpenClash `0.48.x` 中：
     - `enable_meta_sniffer='1'` 且 `enable_meta_sniffer_custom='0'` 时，插件会用默认模板整段覆写 YAML 的 `sniffer`（导致 `HTTP.override-destination` 变 `false`、`QUIC` 端口缩成 `[443]`、`+.12306.cn/.com` 跳过规则丢失）；
     - 直接设 `enable_meta_sniffer='0'` 会把运行配置强制改成 `sniffer.enable: false`（彻底关闭嗅探）。
   - **正确解法**：开启 `enable_meta_sniffer='1'` + `enable_meta_sniffer_pure_ip='1'` + `enable_meta_sniffer_custom='1'`，并将与 `clash/src/platform/mihomo.yaml` 一致的 `sniffer` 写入 `/etc/openclash/custom/openclash_custom_sniffer.yaml`。
3. **`tun.stack` 策略（按硬件分档，刻意保留单机差异）**
   - **Mac mini + UTM（最适用 `gVisor`）**：Apple Silicon 算力充裕，`gVisor` 跑满千兆无压力，且用户态协议栈能隔离虚拟化网卡（`virtio-net` / 桥接）偶发的 GSO/校验和卸载兼容问题。
   - **R4S（RK3399 双核 A72 + 四核 A53）**：4GB 版或 ≤500M 宽带可用 `gVisor`；若为 1GB 版或经常 500M~1000M 高并发下载，推荐 `mixed`（TCP 走 `system`、UDP 走 `gVisor`）或 `system`。
   - **3 台 R2S（RK3328 全小核 A53 + 1GB RAM）**：不推荐 `gVisor`（高并发下易吃满 CPU 并触发 Go GC 抖动），统一保持 `system`（前提是已关闭 Flow Offloading 与旁路由 ICMP Redirect）。
   - 脚本**不会**修改各设备的 `stack_type`。
4. **旁路由 ICMP Redirect（内核已触发告警）**
   - 单臂旁路由与客户端、主路由同处一个二层子网，开启 `send_redirects=1` 会诱导客户端绕过旁路由直连主路由，引发三角路由丢包。
   - 脚本仅在旁路由模式下将 `all` / `default` / `br-lan` 的 `send_redirects` 和 `accept_redirects` 设为 `0` 并持久化到 `/etc/sysctl.conf`。
5. **`dnsmasq` Fake-IP 缓存风险与 IPv6 半开清理**
   - 移除 `dhcp.@dnsmasq[0]` 的 `min_cache_ttl` 和 `use_stale_cache`（防止恢复缓存后把短 TTL 的 Fake-IP 缓存 1 小时导致断网）。
   - 仅当为旁路由、OpenClash 未启用 IPv6（`ipv6_enable != 1`）且已关闭 LAN IPv4 DHCP（`dhcp.lan.ignore='1'`）时，显式禁用 `dhcp.lan` 的 `ra`/`dhcpv6`/`ndp`，并删除 `network.lan.ip6assign` 与 `network.globals.ula_prefix`。
   - 注：`dnsmasq-full` 2.90 的 init 脚本会无条件在生成配置中写入全局 `enable-ra`；在无对应接口 `dhcp-range` 且 `no-dhcp-interface=br-lan` 时不会实际广播 RA，属正常现象。
6. **`/overlay` 冗余大文件清理与每周定时重启**
   - 仅当 `/etc/openclash/core/clash_meta` 可执行时清理 `meta-backup`；仅当 `enable_geoip_dat != 1` 且 `Country.mmdb` 非空时清理闲置 `GeoIP.dat`（`clash/src/base.yaml` 仅用到 `GEOIP,CN`，用体积更小的 `Country.mmdb` 更优）。
   - 定时重启统一改为每周日 04:00，并加 `touch /etc/banner` 防止无 RTC 设备断网校时失败触发重启循环：
     ```cron
     0 4 * * 0 sleep 60 && touch /etc/banner && reboot
     ```

---

## 3. 首台设备（R2S `192.168.30.254`）核验记录

- 本机 SSH 专用密钥路径：`~/.ssh/openwrt_ed25519`（公钥已写入路由器 Dropbear）
- 执行前自动备份位于路由器 `/tmp/openwrt-opt-backup-*`（重启后释放）
- 核验结果：
  - `nft list flowtables`：为空，`flow add @ft` 已移除，`utun` 双向转发计数正常增长
  - `/etc/openclash/UniFOM.yaml`：`tun.stack=system` 保留；`sniffer.enable=true`、`parse-pure-ip=true`、`HTTP.override-destination=true`、`QUIC=[443, 8443]`、`+.12306.cn/.com` 已恢复
  - `sysctl`：`all`/`default`/`br-lan` 6 项 `send_redirects` & `accept_redirects` 全为 `0`
  - `dnsmasq`：`min-cache-ttl` 已消失，`cache-size=0`，上游仍为 `127.0.0.1#7874`
  - `/overlay`：从 `218.3M / 291.9M`（75%，剩 `73.6M`）降至 `165.4M / 291.9M`（57%，剩 **`126.5M`**，释放 `52.9M`）
  - `crontab -l`：已更新为每周日 04:00 重启，保留 `0 5 * * * /usr/share/openclash/openclash.sh`

---

## 4. 后续其他 OpenWrt 设备复用流程

### Step 1：配置 SSH 公钥（如尚未免密）
将本机 `~/.ssh/openwrt_ed25519.pub` 粘贴到目标路由器的 LuCI「系统 → 管理权 → SSH 密钥」，或执行：

```sh
cat ~/.ssh/openwrt_ed25519.pub | ssh root@<ROUTER_IP> "tee -a /etc/dropbear/authorized_keys && chmod 600 /etc/dropbear/authorized_keys"
```

### Step 2：先 `--dry-run` 预览（不修改路由器）

```sh
ssh -i ~/.ssh/openwrt_ed25519 root@<ROUTER_IP> 'sh -s -- --dry-run' < scripts/optimize_openwrt.sh
```

可选开关：
- `--no-reboot-job`：跳过 `crontab` 定时重启修改
- `--no-clean`：跳过 `meta-backup` 与闲置 `GeoIP.dat` 清理

### Step 3：正式执行并核验

```sh
ssh -i ~/.ssh/openwrt_ed25519 root@<ROUTER_IP> 'sh -s' < scripts/optimize_openwrt.sh
```

执行后核验要点：
1. `nft list flowtables` 为空，OpenClash TUN 转发计数正常；
2. `/etc/openclash/UniFOM.yaml` 中 `sniffer.enable: true` 且包含 UniFOM `skip-domain` / `override-destination: true`；
3. `sysctl` 中 `send_redirects` 与 `accept_redirects` 为 `0`（旁路由）；
4. `df -h /overlay` 空间充足；
5. `crontab -l` 符合预期且 OpenClash / `dnsmasq` 进程存活。

### Step 4：运行时 DNS 泄漏验收
按 [docs/build-validation.md](build-validation.md) 与 `AGENTS.md` 要求，在流量经过目标 OpenWrt 的设备浏览器中打开新标签页访问 `https://ipleak.net`，等待 DNS detection 完成并核对出口与解析器归属。

---

## 5. 待办与观察项

- [ ] **R2S #1（`192.168.30.254`）`https://ipleak.net` DNS 泄漏检查**：当前为 **未验证**，需在目标设备浏览器中完成。
- [ ] **其余 4 台设备（R2S #2/#3、R4S、Mac mini + UTM）**：按第 4 节流程逐台 `--dry-run` → 执行 → 核验 → `ipleak.net` 验收，并按第 2 节硬件分档确认各自 `stack_type`。
- [ ] **R2S 观察项**：
  - `br-lan` 上残留的旧 ULA 地址将在下次重启后彻底消失；
  - `mmcblk0p1`（boot 分区）开机日志曾报 `EXT4-fs warning: mounting unchecked fs`，后续停机/插卡维护时可顺手做一次文件系统检查（参考 [HANDOFF_TF_CARD_2026-10-25.md](HANDOFF_TF_CARD_2026-10-25.md)）；
  - 若确认所有管理终端均已使用 SSH 公钥，可按需关闭 Dropbear 密码登录。

## 6. Codex 只读复核（2026-11-24）

对 R2S #1（`192.168.30.254`）通过 SSH 读取 UCI、运行 YAML、进程与内核状态，未执行优化脚本、未修改配置、未重启服务。

- 系统为 ImmortalWrt 24.10.6 / NanoPi R2S；实际 OpenClash 核心进程及 dnsmasq 存活。
- 软件/硬件 Flow Offloading、旁路由 FullCone 均为 `0`；无活动 flowtable，未发现 `flow add` 引流。
- `stack_type=system`；三项自定义 sniffer 开关为 `1`。运行 YAML 中 `parse-pure-ip=true`、HTTP `override-destination=true`、QUIC 端口 `[443,8443]`、12306 跳过项均存在。
- 六项 IPv4 ICMP Redirect 设置运行值为 `0`，且均已写入 `/etc/sysctl.conf`。
- dnsmasq 实际配置为 `cache-size=0`、上游 `127.0.0.1#7874`，未发现最小缓存 TTL 与 stale cache 配置。
- LAN RA/DHCPv6/NDP 均禁用；`ip6assign` 与 ULA 前缀配置不存在。
- TUN 双向转发规则有非零计数；本轮只取一次快照，不以此证明所有业务均正常。
- `/overlay` 已用 165.4M、可用 126.5M（57%）；冗余备份与闲置 GeoIP.dat 不存在，Country.mmdb 非空。
- 每周日 04:00 的延时重启及每日 05:00 的 OpenClash 任务保留。

结论：首台 R2S 的系统优化项已复核生效，无需重复执行优化。其余四台未在本轮核查；浏览器 DNS 泄漏验收仍未验证。硬件吞吐和协议栈推荐沿用此前交接记录，本轮未重新做性能测试。
