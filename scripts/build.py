#!/usr/bin/env python3
# build.py - 从源模板和密钥生成 dist 文件
#
# 用法:
#   python3 scripts/build.py
#
# 输入:
#   openclash/src/base.yaml    - 含占位符的模板 (已纳入 git)
#   openclash/src/secrets.yaml - 真实订阅链接 (gitignore，仅本地)
#   shadowrocket/src/base.conf - SR 配置 (无敏感信息)
#
# 输出:
#   openclash/dist/UniFOM.yaml    - 可部署的 OC 配置 (gitignore，仅本地)
#   shadowrocket/dist/UniFOM.conf - 可部署的 SR 配置 (已纳入 git)

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

def build_oc():
    secrets_path = ROOT / "openclash/src/secrets.yaml"
    template_path = ROOT / "openclash/src/base.yaml"
    output_path   = ROOT / "openclash/dist/UniFOM.yaml"

    if not secrets_path.exists():
        print(f"✗ Missing: {secrets_path}")
        print("  Create openclash/src/secrets.yaml with your subscription URLs.")
        return False

    secrets = load_secrets(secrets_path)

    with open(template_path) as f:
        content = f.read()

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

    print(f"✓ OC built: {output_path}")
    return True

def build_sr():
    src_path    = ROOT / "shadowrocket/src/base.conf"
    output_path = ROOT / "shadowrocket/dist/UniFOM.conf"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, output_path)

    print(f"✓ SR built: {output_path}")
    return True

if __name__ == "__main__":
    ok_oc = build_oc()
    ok_sr = build_sr()
    sys.exit(0 if (ok_oc and ok_sr) else 1)
