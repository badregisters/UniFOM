#!/bin/sh
# optimize_openwrt.sh - Reusable OpenWrt / ImmortalWrt + OpenClash optimization script
#
# Usage (from macOS/Linux):
#   # Preview changes only (read-only):
#   ssh root@192.168.30.254 'sh -s -- --dry-run' < scripts/optimize_openwrt.sh
#
#   # Apply changes (with automatic backup to /tmp):
#   ssh root@192.168.30.254 'sh -s' < scripts/optimize_openwrt.sh
#
# Options:
#   --dry-run       Show planned changes without modifying the router
#   --no-reboot-job Do not modify or add the weekly reboot cron job
#   --no-clean      Do not delete meta-backup or idle GeoIP.dat

set -eu

DRY_RUN=0
MANAGE_REBOOT_CRON=1
CLEAN_FILES=1

for arg in "$@"; do
  case "$arg" in
    --dry-run)       DRY_RUN=1 ;;
    --no-reboot-job) MANAGE_REBOOT_CRON=0 ;;
    --no-clean)      CLEAN_FILES=0 ;;
    -h|--help)
      sed -n '2,16p' "$0" 2>/dev/null || echo "Usage: sh optimize_openwrt.sh [--dry-run] [--no-reboot-job] [--no-clean]"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

log() {
  printf '[opt] %s\n' "$*"
}

run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

# Detect bypass-gateway (single-arm LAN-only router)
IS_BYPASS_GW=0
WAN_IF=$(uci -q get network.wan.device 2>/dev/null || uci -q get network.wan.ifname 2>/dev/null || true)
LAN_GW=$(uci -q get network.lan.gateway 2>/dev/null || true)
if [ -z "$WAN_IF" ] && [ -n "$LAN_GW" ]; then
  IS_BYPASS_GW=1
fi

log "Host: $(uname -n) | Mode: $([ "$IS_BYPASS_GW" -eq 1 ] && echo 'bypass-gateway' || echo 'main-router') | DryRun: $DRY_RUN"

# 0. Backup configs to /tmp (avoid consuming /overlay)
TS=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/tmp/openwrt-opt-backup-$TS"
if [ "$DRY_RUN" -eq 0 ]; then
  mkdir -p "$BACKUP_DIR"
  for f in /etc/config/firewall /etc/config/openclash /etc/config/dhcp /etc/config/network /etc/sysctl.conf /etc/crontabs/root /etc/openclash/custom/openclash_custom_sniffer.yaml /etc/openclash/custom/openclash_custom_overwrite.sh; do
    [ -f "$f" ] && cp -a "$f" "$BACKUP_DIR/"
  done
  log "Backup saved to $BACKUP_DIR"
else
  log "Would save config backup to $BACKUP_DIR"
fi

FIREWALL_CHANGED=0
OPENCLASH_CHANGED=0
DHCP_CHANGED=0
NETWORK_CHANGED=0
CRON_CHANGED=0

# 1. Firewall: disable Flow Offloading (SW & HW); disable FullCone on bypass gateway
if uci -q get firewall.@defaults[0] >/dev/null 2>&1; then
  if [ "$(uci -q get firewall.@defaults[0].flow_offloading || echo 0)" != "0" ]; then
    log "Firewall: disable software flow_offloading"
    run uci set firewall.@defaults[0].flow_offloading='0'
    FIREWALL_CHANGED=1
  fi
  if [ "$(uci -q get firewall.@defaults[0].flow_offloading_hw || echo 0)" != "0" ]; then
    log "Firewall: disable hardware flow_offloading_hw"
    run uci set firewall.@defaults[0].flow_offloading_hw='0'
    FIREWALL_CHANGED=1
  fi
  if [ "$IS_BYPASS_GW" -eq 1 ] && [ "$(uci -q get firewall.@defaults[0].fullcone || echo 0)" != "0" ]; then
    log "Firewall: disable fullcone on bypass gateway"
    run uci set firewall.@defaults[0].fullcone='0'
    FIREWALL_CHANGED=1
  fi
  if [ "$FIREWALL_CHANGED" -eq 1 ]; then
    run uci commit firewall
  fi
fi

# 2. OpenClash: enable custom sniffer matching UniFOM mihomo.yaml
#    Note: In OpenClash, enable_meta_sniffer=0 forces sniffer.enable=false,
#    while enable_meta_sniffer=1 without custom overwrites YAML sniffer with defaults.
#    Using custom sniffer keeps sniffer enabled with exact UniFOM rules while preserving stack_type.
if uci -q get openclash.config >/dev/null 2>&1; then
  SNIFFER_FILE="/etc/openclash/custom/openclash_custom_sniffer.yaml"
  TMP_SNIFFER="/tmp/openclash_custom_sniffer.yaml.$$"
  cat > "$TMP_SNIFFER" <<'EOF'
sniffer:
  enable: true
  parse-pure-ip: true
  sniff:
    TLS:
      ports: [443, 8443]
    HTTP:
      ports: [80, 8080-8880]
      override-destination: true
    QUIC:
      ports: [443, 8443]
  skip-domain:
    - "Mijia Cloud"
    - "dlg.io.mi.com"
    - "+.push.apple.com"
    - "+.12306.cn"
    - "+.12306.com"
EOF

  if [ "$(uci -q get openclash.config.enable_meta_sniffer || echo 0)" != "1" ]; then
    log "OpenClash: set enable_meta_sniffer=1"
    run uci set openclash.config.enable_meta_sniffer='1'
    OPENCLASH_CHANGED=1
  fi
  if [ "$(uci -q get openclash.config.enable_meta_sniffer_pure_ip || echo 0)" != "1" ]; then
    log "OpenClash: set enable_meta_sniffer_pure_ip=1"
    run uci set openclash.config.enable_meta_sniffer_pure_ip='1'
    OPENCLASH_CHANGED=1
  fi
  if [ "$(uci -q get openclash.config.enable_meta_sniffer_custom || echo 0)" != "1" ]; then
    log "OpenClash: enable custom sniffer override (enable_meta_sniffer_custom=1)"
    run uci set openclash.config.enable_meta_sniffer_custom='1'
    OPENCLASH_CHANGED=1
  fi
  if [ ! -f "$SNIFFER_FILE" ] || [ "$(cat "$SNIFFER_FILE")" != "$(cat "$TMP_SNIFFER")" ]; then
    log "OpenClash: sync UniFOM sniffer rules to $SNIFFER_FILE"
    if [ "$DRY_RUN" -eq 0 ]; then
      mkdir -p /etc/openclash/custom
      mv "$TMP_SNIFFER" "$SNIFFER_FILE"
    else
      rm -f "$TMP_SNIFFER"
    fi
    OPENCLASH_CHANGED=1
  else
    rm -f "$TMP_SNIFFER"
  fi
  HOOK=/etc/openclash/custom/openclash_custom_overwrite.sh
  if ! grep -q '^# UniFOM managed sniffer overwrite$' "$HOOK" 2>/dev/null; then
    log "OpenClash: install final sniffer overwrite for both UniFOM profiles"
    if [ "$DRY_RUN" -eq 0 ]; then
      TMP_HOOK=$(mktemp "${HOOK}.XXXXXX")
      if ! ruby -e '
        path, dest = ARGV
        source = File.exist?(path) ? File.read(path) : "#!/bin/sh\nexit 0\n"
        block = STDIN.read
        abort "Unsupported custom hook ending; original left intact" unless source.sub!(/^exit 0[ \t]*\s*\z/, block)
        File.write(dest, source)
      ' "$HOOK" "$TMP_HOOK" <<'HOOK_EOF'
# UniFOM managed sniffer overwrite
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
exit 0
HOOK_EOF
      then
        rm -f "$TMP_HOOK"
        exit 1
      fi
      sh -n "$TMP_HOOK"
      chmod 755 "$TMP_HOOK"
      mv "$TMP_HOOK" "$HOOK"
    fi
    OPENCLASH_CHANGED=1
  fi
  if [ "$OPENCLASH_CHANGED" -eq 1 ]; then
    run uci commit openclash
  fi
fi

# 3. Sysctl: disable ICMP redirects on bypass gateway
set_sysctl_kv() {
  key="$1"
  val="$2"
  file="/etc/sysctl.conf"
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] sysctl %s=%s (persist in %s)\n' "$key" "$val" "$file"
    return 0
  fi
  touch "$file"
  if grep -q "^${key}[[:space:]]*=" "$file"; then
    sed -i "s|^${key}[[:space:]]*=.*|${key}=${val}|" "$file"
  else
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
  sysctl -w "${key}=${val}" >/dev/null 2>&1 || true
}

if [ "$IS_BYPASS_GW" -eq 1 ]; then
  log "Sysctl: disable IPv4 ICMP send/accept redirects for bypass gateway"
  set_sysctl_kv "net.ipv4.conf.all.send_redirects" "0"
  set_sysctl_kv "net.ipv4.conf.default.send_redirects" "0"
  set_sysctl_kv "net.ipv4.conf.all.accept_redirects" "0"
  set_sysctl_kv "net.ipv4.conf.default.accept_redirects" "0"
  if [ -d /proc/sys/net/ipv4/conf/br-lan ]; then
    set_sysctl_kv "net.ipv4.conf.br-lan.send_redirects" "0"
    set_sysctl_kv "net.ipv4.conf.br-lan.accept_redirects" "0"
  fi
fi

# 4. DHCP & IPv6 RA:
#    4a. Clear min_cache_ttl / use_stale_cache (unsafe with Fake-IP)
if uci -q get dhcp.@dnsmasq[0] >/dev/null 2>&1; then
  if uci -q get dhcp.@dnsmasq[0].min_cache_ttl >/dev/null 2>&1; then
    log "DHCP/dnsmasq: remove min_cache_ttl"
    run uci delete dhcp.@dnsmasq[0].min_cache_ttl
    DHCP_CHANGED=1
  fi
  if uci -q get dhcp.@dnsmasq[0].use_stale_cache >/dev/null 2>&1; then
    log "DHCP/dnsmasq: remove use_stale_cache"
    run uci delete dhcp.@dnsmasq[0].use_stale_cache
    DHCP_CHANGED=1
  fi
fi

#    4b. On bypass gateway with OpenClash IPv6 disabled and DHCPv4 ignored, disable IPv6 RA/ULA
OC_IPV6=$(uci -q get openclash.config.ipv6_enable || echo 0)
LAN_DHCP_IGNORE=$(uci -q get dhcp.lan.ignore || echo 0)
if [ "$IS_BYPASS_GW" -eq 1 ] && [ "$OC_IPV6" != "1" ] && [ "$LAN_DHCP_IGNORE" = "1" ]; then
  if [ "$(uci -q get dhcp.lan.ra || true)" != "disabled" ]; then
    log "DHCP: disable IPv6 RA / DHCPv6 / NDP on lan"
    run uci set dhcp.lan.ra='disabled'
    run uci set dhcp.lan.dhcpv6='disabled'
    run uci set dhcp.lan.ndp='disabled'
    DHCP_CHANGED=1
  fi
  if uci -q get network.lan.ip6assign >/dev/null 2>&1; then
    log "Network: remove lan.ip6assign"
    run uci delete network.lan.ip6assign
    NETWORK_CHANGED=1
  fi
  if uci -q get network.globals.ula_prefix >/dev/null 2>&1; then
    log "Network: remove globals.ula_prefix"
    run uci delete network.globals.ula_prefix
    NETWORK_CHANGED=1
  fi
fi

if [ "$DHCP_CHANGED" -eq 1 ]; then
  run uci commit dhcp
fi
if [ "$NETWORK_CHANGED" -eq 1 ]; then
  run uci commit network
fi

# 5. Clean idle large files in /etc/openclash (safe checks before deletion)
if [ "$CLEAN_FILES" -eq 1 ]; then
  if [ -d /etc/openclash/core/meta-backup ] && [ -x /etc/openclash/core/clash_meta ]; then
    log "Cleanup: remove /etc/openclash/core/meta-backup"
    run rm -rf /etc/openclash/core/meta-backup
  fi
  GEOIP_DAT_EN=$(uci -q get openclash.config.enable_geoip_dat || echo 0)
  if [ "$GEOIP_DAT_EN" != "1" ] && [ -s /etc/openclash/Country.mmdb ] && [ -f /etc/openclash/GeoIP.dat ]; then
    log "Cleanup: remove idle /etc/openclash/GeoIP.dat (Country.mmdb is active)"
    run rm -f /etc/openclash/GeoIP.dat
  fi
fi

# 6. Cron: set weekly reboot on Sunday 04:00 (with /etc/banner touch guard against RTC boot loops)
if [ "$MANAGE_REBOOT_CRON" -eq 1 ]; then
  CRON_FILE="/etc/crontabs/root"
  NEW_REBOOT_LINE="0 4 * * 0 sleep 60 && touch /etc/banner && reboot"
  if [ "$DRY_RUN" -eq 1 ]; then
    log "Cron: would replace any reboot line with: $NEW_REBOOT_LINE"
  else
    mkdir -p /etc/crontabs
    touch "$CRON_FILE"
    TMP_CRON="/tmp/root.cron.$$"
    grep -v 'reboot' "$CRON_FILE" > "$TMP_CRON" || true
    printf '%s\n' "$NEW_REBOOT_LINE" >> "$TMP_CRON"
    if [ "$(cat "$CRON_FILE")" != "$(cat "$TMP_CRON")" ]; then
      mv "$TMP_CRON" "$CRON_FILE"
      CRON_CHANGED=1
      log "Cron: updated weekly reboot job (Sunday 04:00)"
    else
      rm -f "$TMP_CRON"
    fi
  fi
fi

# 7. Reload affected services
if [ "$DRY_RUN" -eq 0 ]; then
  if [ "$NETWORK_CHANGED" -eq 1 ]; then
    log "Reloading network..."
    ubus call network reload >/dev/null 2>&1 || /etc/init.d/network reload
  fi
  if [ "$DHCP_CHANGED" -eq 1 ]; then
    log "Restarting dnsmasq..."
    /etc/init.d/dnsmasq restart
  fi
  if [ "$FIREWALL_CHANGED" -eq 1 ]; then
    log "Reloading firewall..."
    /etc/init.d/firewall reload
  fi
  if [ "$CRON_CHANGED" -eq 1 ]; then
    log "Restarting cron..."
    /etc/init.d/cron restart
  fi
  if [ "$OPENCLASH_CHANGED" -eq 1 ] || [ "$FIREWALL_CHANGED" -eq 1 ]; then
    log "Restarting OpenClash..."
    /etc/init.d/openclash restart
  fi
  case "$(uci -q get openclash.config.config_path || true)" in
    */UniFOM.yaml|*/UniFOM-shared.yaml)
      PROFILE=$(uci -q get openclash.config.config_path)
      RUNTIME="/etc/openclash/${PROFILE##*/}"
      tries=0
      until ps w | grep '[c]lash -d' | grep -F -- "-f $RUNTIME" >/dev/null &&
        ruby -ryaml -e 'abort unless ARGV.map { |p| YAML.load_file(p).fetch("sniffer") }.uniq.size == 1' \
          "$RUNTIME" "$SNIFFER_FILE" 2>/dev/null; do
        tries=$((tries + 1))
        if [ "$tries" -ge 30 ]; then
          log "ERROR: active runtime sniffer does not match the template; backup: $BACKUP_DIR"
          exit 1
        fi
        sleep 2
      done
      log "Verified active UniFOM runtime sniffer"
      ;;
  esac
  log "Optimization completed."
else
  log "Dry-run completed. No changes were made."
fi
