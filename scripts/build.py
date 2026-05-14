#!/usr/bin/env python3
# build.py - Generate dist files from src templates and secrets
#
# Usage:
#   python3 scripts/build.py
#
# Inputs:
#   clash/src/platform/mihomo.yaml - Mihomo-specific header (port, tun, geo, sniffer, dns)
#   clash/src/platform/stash.yaml  - Stash-specific header
#   clash/src/base.yaml            - shared body with injection markers
#   clash/src/secrets.yaml         - provider list with URLs (gitignored, local only)
#   shadowrocket/src/base.conf     - SR config (no secrets)
#
# Outputs:
#   clash/openclash/dist/UniFOM.yaml - deployable OC config (gitignored, local only)
#   clash/stash/dist/UniFOM.yaml     - deployable Stash config (gitignored, local only)
#   shadowrocket/dist/UniFOM.conf    - deployable SR config (in git)
#
# secrets.yaml format:
#   Simple entry (defaults to regional + manual groups):
#     FlowerCloud: "https://..."
#
#   Extended entry (override groups):
#     Maying:
#       url: "https://..."
#       groups: manual          # comma-separated string or YAML list

import re
import sys
import shutil
import yaml
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent

# Default filter applied to all proxy providers
PROVIDER_FILTER = (
    '(?i)(香港|🇭🇰|HK|美国|🇺🇸|US|日本|🇯🇵|JP|韩国|🇰🇷|KR|'
    '台湾|🇹🇼|TW|Taiwan|新加坡|狮城|🇸🇬|SG|英国|🇬🇧|UK|马来|🇲🇾|MY|'
    '喀麦隆|冰岛|土耳其|阿根廷)'
)

def load_providers(path):
    """Parse secrets.yaml into an ordered dict of name -> {url, groups}.

    Simple entry:   FlowerCloud: "https://..."
    Extended entry: Maying:
                      url: "https://..."
                      groups: manual   # or [manual, budget]

    Default groups when not specified: [regional, manual]
    """
    with open(path) as f:
        raw = yaml.safe_load(f)

    providers = {}
    for name, value in raw.items():
        if isinstance(value, str):
            providers[name] = {'url': value, 'groups': ['regional', 'manual']}
        elif isinstance(value, dict):
            groups_raw = value.get('groups', 'regional,manual')
            if isinstance(groups_raw, str):
                groups = [g.strip() for g in groups_raw.split(',')]
            elif isinstance(groups_raw, list):
                groups = [str(g) for g in groups_raw]
            else:
                groups = ['regional', 'manual']
            providers[name] = {'url': value['url'], 'groups': groups}
    return providers

def gen_proxy_providers(providers):
    """Generate the full proxy-providers: YAML block."""
    lines = ['proxy-providers:']
    for name, info in providers.items():
        lines += [
            f'  {name}:',
            f'    type: http',
            f'    url: "{info["url"]}"',
            f'    interval: 14400',
            f'    path: ./proxy_provider/{name}.yaml',
            f'    filter: "{PROVIDER_FILTER}"',
            f'    health-check: {{enable: true, interval: 600, url: http://www.gstatic.com/generate_204}}',
            '',
        ]
    return '\n'.join(lines)

def gen_direct_domains(providers):
    """Generate DOMAIN-SUFFIX direct rules from each provider's subscription hostname."""
    lines = []
    seen = set()
    for name, info in providers.items():
        host = urlparse(info['url']).hostname
        if host and host not in seen:
            seen.add(host)
            lines.append(f'  - DOMAIN-SUFFIX,{host},🎯 全球直连')
    return '\n'.join(lines)

def use_list(providers, group):
    """Return comma-separated provider names belonging to the given group."""
    return ', '.join(n for n, i in providers.items() if group in i['groups'])

def inject(content, providers):
    """Replace all generation markers in base.yaml content."""
    content = content.replace(
        '# [GENERATED: proxy-providers]',
        gen_proxy_providers(providers)
    )
    content = content.replace(
        '  # [GENERATED: direct-domains]',
        gen_direct_domains(providers)
    )
    content = content.replace('[__USE_regional__]', f'[{use_list(providers, "regional")}]')
    content = content.replace('[__USE_manual__]',   f'[{use_list(providers, "manual")}]')
    return content

def build_clash(platform, providers):
    platform_path = ROOT / f'clash/src/platform/{platform}.yaml'
    base_path     = ROOT / 'clash/src/base.yaml'

    if platform == 'mihomo':
        output_path = ROOT / 'clash/openclash/dist/UniFOM.yaml'
        label = 'OC'
    elif platform == 'stash':
        output_path = ROOT / 'clash/stash/dist/UniFOM.yaml'
        label = 'Stash'
    else:
        print(f'✗ Unknown platform: {platform}')
        return False

    with open(platform_path) as f:
        content = f.read()
    with open(base_path) as f:
        base = f.read()

    # Strip Mihomo-only lines from Stash build.
    # Lines tagged with trailing "# [Mihomo]" use Mihomo-exclusive syntax
    # and must be dropped; Stash will reject them at parse time.
    if platform == 'stash':
        base = '\n'.join(
            line for line in base.splitlines()
            if not line.rstrip().endswith('# [Mihomo]')
        ) + '\n'

    content += '\n' + base
    content = inject(content, providers)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(content)

    print(f'✓ {label} built: {output_path}')
    return True

def build_sr():
    src_path    = ROOT / 'shadowrocket/src/base.conf'
    output_path = ROOT / 'shadowrocket/dist/UniFOM.conf'

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, output_path)

    print(f'✓ SR built: {output_path}')
    return True

if __name__ == '__main__':
    secrets_path = ROOT / 'clash/src/secrets.yaml'

    if not secrets_path.exists():
        print(f'✗ Missing: {secrets_path}')
        print('  Create clash/src/secrets.yaml with your subscription URLs.')
        sys.exit(1)

    providers = load_providers(secrets_path)

    ok_oc    = build_clash('mihomo', providers)
    ok_stash = build_clash('stash', providers)
    ok_sr    = build_sr()
    sys.exit(0 if (ok_oc and ok_stash and ok_sr) else 1)
