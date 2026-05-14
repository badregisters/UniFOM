#!/usr/bin/env python3
# build.py - Generate dist files from src templates and secrets
#
# Usage:
#   python3 scripts/build.py
#
# Inputs:
#   clash/src/platform/mihomo.yaml - Mihomo-specific header (port, tun, geo, sniffer, dns)
#   clash/src/platform/stash.yaml  - Stash-specific header
#   clash/src/base.yaml            - shared body (proxy-providers, groups, rules)
#   openclash/src/secrets.yaml     - real subscription URLs (gitignored, local only)
#   shadowrocket/src/base.conf     - SR config (no secrets)
#
# Outputs:
#   openclash/dist/UniFOM.yaml    - deployable OC config (gitignored, local only)
#   stash/dist/UniFOM.yaml        - deployable Stash config (gitignored, local only)
#   shadowrocket/dist/UniFOM.conf - deployable SR config (in git)

import re
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent

def load_secrets(path):
    secrets = {}
    with open(path) as f:
        for line in f:
            m = re.match(r'^(\S+):\s*"(.+)"', line.strip())
            if m:
                secrets[m.group(1)] = m.group(2)
    return secrets

def build_clash(platform):
    secrets_path  = ROOT / "openclash/src/secrets.yaml"
    platform_path = ROOT / f"clash/src/platform/{platform}.yaml"
    base_path     = ROOT / "clash/src/base.yaml"

    if platform == "mihomo":
        output_path = ROOT / "openclash/dist/UniFOM.yaml"
        label = "OC"
    elif platform == "stash":
        output_path = ROOT / "stash/dist/UniFOM.yaml"
        label = "Stash"
    else:
        print(f"✗ Unknown platform: {platform}")
        return False

    if not secrets_path.exists():
        print(f"✗ Missing: {secrets_path}")
        print("  Create openclash/src/secrets.yaml with your subscription URLs.")
        return False

    secrets = load_secrets(secrets_path)

    with open(platform_path) as f:
        content = f.read()
    with open(base_path) as f:
        content += "\n" + f.read()

    replacements = {
        "YOUR_FLOWERCLOUD_URL": secrets.get("FlowerCloud", ""),
        "YOUR_OIXCLOUD_URL":    secrets.get("oixCloud", ""),
        "YOUR_MAYING_URL":      secrets.get("Maying", ""),
        "YOUR_NEXITALLY_URL":   secrets.get("Nexitally", ""),
        "YOUR_LIANGXIN_URL":    secrets.get("LiangXin", ""),
    }

    for placeholder, value in replacements.items():
        content = content.replace(f'"{placeholder}"', f'"{value}"')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)

    print(f"✓ {label} built: {output_path}")
    return True

def build_sr():
    src_path    = ROOT / "shadowrocket/src/base.conf"
    output_path = ROOT / "shadowrocket/dist/UniFOM.conf"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, output_path)

    print(f"✓ SR built: {output_path}")
    return True

if __name__ == "__main__":
    ok_oc    = build_clash("mihomo")
    ok_stash = build_clash("stash")
    ok_sr    = build_sr()
    sys.exit(0 if (ok_oc and ok_stash and ok_sr) else 1)
