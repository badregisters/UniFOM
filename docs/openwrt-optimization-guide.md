# OpenWrt / OpenClash 人工优化指南

适用于运行 UniFOM 个人版或共享版的 OpenWrt / ImmortalWrt。以 R2S 和 Mac mini 上的 UTM 旁路由为例。整个过程不改订阅源 YAML；一次只做一台，保留可用的 LuCI 或本机控制台。重载服务时代理和 DNS 可能短暂中断。

## 1. 确认设备并备份

用 SSH 登录目标路由器，以下命令都在路由器上以 root 执行。先读设备型号和当前配置，不要只凭 IP 判断：R2S 与 UTM 可能轮流使用同一个地址。

```sh
ubus call system board
uci -q get network.lan.gateway
uci -q show network.wan
uci -q get openclash.config.config_path
uci -q get openclash.config.stack_type
crontab -l
```

确认是否是单臂旁路由：客户端和主路由在同一个 LAN，设备通过 LAN 上游网关联网。看不准就不要做下文标记「仅旁路由」的步骤。

在 LuCI「系统 → 备份/升级」下载配置备份。另将下列文件中存在的项通过 SCP 导出到自己的电脑；不要假定 LuCI 备份一定覆盖它们：

- `/etc/config/firewall`、`/etc/config/dhcp`、`/etc/config/network`、`/etc/config/openclash`
- `/etc/sysctl.conf`、`/etc/crontabs/root`
- `/etc/openclash/custom/openclash_custom_sniffer.yaml`、`/etc/openclash/custom/openclash_custom_overwrite.sh`

记录哪些文件本来不存在。备份可能含订阅或凭据，不要上传到公开位置；只放路由器 `/tmp` 的备份会在重启时丢失。

## 2. 防火墙：关闭流量卸载

LuCI「网络 → 防火墙 → 常规设置」关闭软件和硬件流量卸载，保存并应用。**仅旁路由**同时关闭 FullCone。界面没有对应开关时用 SSH：

```sh
uci set 'firewall.@defaults[0].flow_offloading=0'
uci set 'firewall.@defaults[0].flow_offloading_hw=0'
# 仅旁路由执行下一行
uci set 'firewall.@defaults[0].fullcone=0'
uci commit firewall
/etc/init.d/firewall reload
nft list flowtables
```

验收：UCI 中相应值为 `0`，且不再有活动的 `flowtable ft`。主路由跳过 FullCone 那一行。

## 3. 仅旁路由：关闭 IPv4 ICMP Redirect

用 `vi /etc/sysctl.conf` 编辑配置。已有同名项就改值，不要追加重复定义：

```ini
net.ipv4.conf.all.send_redirects=0
net.ipv4.conf.all.accept_redirects=0
net.ipv4.conf.default.send_redirects=0
net.ipv4.conf.default.accept_redirects=0
net.ipv4.conf.br-lan.send_redirects=0
net.ipv4.conf.br-lan.accept_redirects=0
```

如果 LAN 网桥不叫 `br-lan`，先从 `ip link` 确认实际接口名，再替换。保存后执行：

```sh
sysctl -p /etc/sysctl.conf
for i in all default br-lan; do
  sysctl "net.ipv4.conf.$i.send_redirects" "net.ipv4.conf.$i.accept_redirects"
done
```

验收：六项运行值都为 `0`。

## 4. DNS 缓存与 LAN IPv6

```sh
uci -q delete 'dhcp.@dnsmasq[0].min_cache_ttl'
uci -q delete 'dhcp.@dnsmasq[0].use_stale_cache'
uci commit dhcp
/etc/init.d/dnsmasq restart
grep -Eh '^(cache-size|min-cache-ttl|use-stale-cache|server=127)' /var/etc/dnsmasq.conf.*
```

验收：不再出现最小 TTL 或 stale cache；已有 OpenClash DNS 上游不应因这次修改而改变。

**只有同时满足这三条才继续**：单臂旁路由、OpenClash IPv6 未启用、LAN IPv4 DHCP 已关闭（`uci -q get dhcp.lan.ignore` 返回 `1`）。若还依赖 LAN IPv6 或其他接口使用此 ULA 前缀，跳过。

```sh
uci set dhcp.lan.ra=disabled
uci set dhcp.lan.dhcpv6=disabled
uci set dhcp.lan.ndp=disabled
uci -q delete network.lan.ip6assign
uci -q delete network.globals.ula_prefix
uci commit dhcp
uci commit network
ubus call network reload
/etc/init.d/odhcpd reload
ip -6 addr show dev br-lan
```

验收：用 `uci show dhcp.lan` 确认三项均为 `disabled`，用 `uci -q get` 核对两项已删除。旧 ULA 可能先变为 `deprecated`，等有效期结束再查；`fe80::` 链路本地地址不需要删。

## 5. 修复 OpenClash 嗅探

1. 在路由器上打开 `/etc/openclash/custom/openclash_custom_sniffer.yaml`，用仓库 `clash/src/platform/mihomo.yaml` 的整个 `sniffer:` 段替换文件内容，不要带后面的 `dns:` 段。
2. 启用下列三项。不要改 TUN 栈：R2S 已用 `system` 就保留；UTM 已稳定使用 `gvisor` 也不必切换。

```sh
uci set openclash.config.enable_meta_sniffer=1
uci set openclash.config.enable_meta_sniffer_pure_ip=1
uci set openclash.config.enable_meta_sniffer_custom=1
uci commit openclash
```

3. 编辑 `/etc/openclash/custom/openclash_custom_overwrite.sh`，把下面一段加在末尾的 `exit 0` **之前**。保留已有自定义逻辑；如果已有同用途的 UniFOM 覆写，只保留一份。若原脚本流程不清楚，不要整份覆盖。

```sh
case "$(uci -q get openclash.config.config_path)" in
  */UniFOM.yaml|*/UniFOM-shared.yaml)
    ruby -ryaml -e '
      path, template = ARGV
      config = YAML.load_file(path)
      config["sniffer"] = YAML.load_file(template).fetch("sniffer")
      File.write(path, YAML.dump(config))
    ' "$1" /etc/openclash/custom/openclash_custom_sniffer.yaml || exit 1
    ;;
esac
```

4. 用 `sh -n /etc/openclash/custom/openclash_custom_overwrite.sh` 检查语法，通过后执行 `/etc/init.d/openclash restart`。不要直接编辑生成好的运行 YAML。
5. 待核心进程启动后，用 `ps w | grep '[c]lash -d'` 找到 `-f` 后面的实际运行文件。检查其中 HTTP `override-destination: true`、QUIC 端口 `443` 和 `8443`、`+.12306.cn` 与 `+.12306.com`，以及 TUN 栈没变。只看到 UCI 开关或模板文件正确，不算生效。需要两版都验收时，在维护时段分别加载、回读，再切回原配置。

## 6. 定时任务和空间：按需处理

- 要每周日 04:00 **只重启 OpenClash**，先在 OpenClash 的定时重启设置选周日、04:00，保存应用；再用 `crontab -l` 确认是 `0 4 * * 0 /etc/init.d/openclash restart #openclash-cron-task`。若用 SSH，应修改插件的 `auto_restart_week_time=0` 和 `auto_restart_day_time=4` 并提交 UCI，同时更新已有 cron 行；只改 cron 可能在插件重建任务时被覆盖。
- 保留原有 05:00 配置订阅更新。不要把整机 `reboot` 当成 OpenClash 重启；行首有 `#` 的任务不会执行。
- 用 `df -h /overlay` 查看空间。没有空间压力就不删文件；也不要为这轮优化删除可用的核心备份或仍在使用的地理数据库。

## 7. 最终验收与回退

1. 从实际经过这台路由器的设备测试直连和代理业务，确认 OpenClash 与 dnsmasq 正常。
2. 在同一设备打开 [ipleak.net](https://ipleak.net/)，等 DNS detection 完成，记录出口、解析器归属、浏览器安全 DNS 和所选节点。按预期解析路径判断；DNS、IPv6、WebRTC 分开记录。没在目标设备测就标未验证。
3. 出问题时优先还原最后改动的文件，然后重载对应服务。若无法远程连入，用本机控制台；若需全部回退，恢复第 1 步的配置及自定义文件（本来不存在的新增文件才移除）。整机重启是否仍生效需另行实测。

仓库也有 [自动化脚本](../scripts/optimize_openwrt.sh)。只想预览时用 `--dry-run --no-clean --no-reboot-job`；不希望脚本清文件或安排**整机**定时重启，正式运行时也保留后两个选项。
