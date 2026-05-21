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
#   shadowrocket/src/base.conf     - SR config template
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
#   Extended entry (all fields optional except url):
#     FlowerCloud:
#       url: "https://..."
#       groups: manual          # comma-separated string or YAML list; default: regional,manual
#       extra_domains: [xmancdn.com]  # secondary CDN domains not derivable from URL

import re
import sys
import yaml
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

ROOT = Path(__file__).parent.parent
PROJECT_URL = 'https://github.com/badregisters/UniFOM'

# Default filter applied to all proxy providers
PROVIDER_FILTER = (
    r'(?i)(香港|🇭🇰|HK|美国|🇺🇸|\bUS\b|日本|🇯🇵|JP|韩国|🇰🇷|KR|'
    r'台湾|🇹🇼|TW|Taiwan|新加坡|狮城|🇸🇬|SG|英国|🇬🇧|UK|马来|🇲🇾|MY|'
    r'喀麦隆|冰岛|土耳其|阿根廷|印度|🇮🇳|India)'
)

def parse_meta(text):
    meta = {}
    for line in text.splitlines():
        m = re.match(r'^#\s+(platform|version|updated):\s*(.+)', line)
        if m:
            meta[m.group(1)] = m.group(2).strip()
        elif line.strip() and not line.startswith('#'):
            break
    return meta

def make_header(meta):
    platform = meta.get('platform', 'Unknown')
    version  = meta.get('version',  'unknown')
    updated  = meta.get('updated',  'unknown')
    return f'# {platform} | {version} | {updated} | {PROJECT_URL}\n\n'

def strip_comments_and_collapse(content):
    result = []
    prev_blank = False
    for line in content.splitlines(keepends=True):
        if line.lstrip().startswith('#'):
            continue
        is_blank = line.strip() == ''
        if is_blank and prev_blank:
            continue
        result.append(line)
        prev_blank = is_blank
    while result and result[0].strip() == '':
        result.pop(0)
    return ''.join(result)

def load_providers(path):
    """Parse secrets.yaml into an ordered dict of name -> {url, groups, extra_domains}.

    Simple entry:   FlowerCloud: "https://..."
    Extended entry: FlowerCloud:
                      url: "https://..."
                      groups: manual          # or [manual, budget]
                      extra_domains: [xmancdn.com]

    Default groups when not specified: [regional, manual]
    """
    with open(path) as f:
        raw = yaml.safe_load(f)

    providers = {}
    for name, value in raw.items():
        if isinstance(value, str):
            providers[name] = {'url': value, 'groups': ['regional', 'manual'], 'extra_domains': []}
        elif isinstance(value, dict):
            groups_raw = value.get('groups', 'regional,manual')
            if isinstance(groups_raw, str):
                groups = [g.strip() for g in groups_raw.split(',')]
            elif isinstance(groups_raw, list):
                groups = [str(g) for g in groups_raw]
            else:
                groups = ['regional', 'manual']
            extra = value.get('extra_domains', [])
            if isinstance(extra, str):
                extra = [extra]
            providers[name] = {'url': value['url'], 'groups': groups, 'extra_domains': list(extra)}
    return providers

def gen_proxy_providers(providers):
    """Generate the full proxy-providers: YAML block."""
    lines = ['proxy-providers:']
    for name, info in providers.items():
        lines += [
            f'  {name}:',
            f'    type: http',
            f'    url: "{info["url"]}"',
            f'    interval: 86400',
            f'    path: ./proxy_provider/{name}.yaml',
            f"    filter: '{PROVIDER_FILTER}'",
            f'    health-check: {{enable: true, interval: 600, url: http://www.gstatic.com/generate_204}}',
            '',
        ]
    return '\n'.join(lines)

def _hosts_from_url(url):
    """Extract all hostnames from a URL, including those embedded in query param values."""
    hosts = []
    parsed = urlparse(url)
    if parsed.hostname:
        hosts.append(parsed.hostname)
    for values in parse_qs(parsed.query, keep_blank_values=True).values():
        for v in values:
            try:
                sub = urlparse(unquote(v))
                if sub.scheme in ('http', 'https') and sub.hostname:
                    hosts.append(sub.hostname)
            except Exception:
                pass
    return hosts

def _all_direct_hosts(providers):
    """Yield hostnames for all direct-connect domains, deduped."""
    seen = set()
    for info in providers.values():
        for host in _hosts_from_url(info['url']):
            if host not in seen:
                seen.add(host)
                yield host
        for extra in info['extra_domains']:
            if extra and extra not in seen:
                seen.add(extra)
                yield extra

def gen_direct_domains_clash(providers):
    """Generate Clash-format DOMAIN-SUFFIX direct rules (YAML list items)."""
    return '\n'.join(f'  - DOMAIN-SUFFIX,{h},🎯 全球直连' for h in _all_direct_hosts(providers))


def gen_direct_domains_sr(providers):
    """Generate SR-format DOMAIN-SUFFIX direct rules (plain text)."""
    return '\n'.join(f'DOMAIN-SUFFIX,{h},🎯 全球直连' for h in _all_direct_hosts(providers))

def inject_sr(content, providers):
    """Replace the direct-domains marker block in base.conf content."""
    start_marker = '# [proxy-provider-direct-domains start]'
    end_marker   = '# [proxy-provider-direct-domains end]'
    generated    = gen_direct_domains_sr(providers)
    replacement  = f'{start_marker}\n{generated}\n{end_marker}'
    pattern = re.compile(
        re.escape(start_marker) + r'.*?' + re.escape(end_marker),
        re.DOTALL,
    )
    return pattern.sub(replacement, content)

def use_list(providers, group):
    """Return comma-separated provider names belonging to the given group."""
    return ', '.join(n for n, i in providers.items() if group in i['groups'])

def inject_clash(content, providers):
    """Replace all generation markers in base.yaml content."""
    content = content.replace(
        '# [GENERATED: proxy-providers]',
        gen_proxy_providers(providers)
    )
    content = content.replace(
        '  # [GENERATED: direct-domains]',
        gen_direct_domains_clash(providers)
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
        platform_content = f.read()
    with open(base_path) as f:
        base = f.read()

    meta   = parse_meta(platform_content)
    header = make_header(meta)

    if platform == 'stash':
        base = '\n'.join(
            line for line in base.splitlines()
            if not line.rstrip().endswith('# [Mihomo]')
        ) + '\n'

    combined = platform_content + '\n' + base
    combined = inject_clash(combined, providers)
    combined = strip_comments_and_collapse(combined)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(header)
        f.write(combined)

    print(f'✓ {label} built: {output_path}')
    return True

def build_sr(providers):
    src_path    = ROOT / 'shadowrocket/src/base.conf'
    output_path = ROOT / 'shadowrocket/dist/UniFOM.conf'

    with open(src_path) as f:
        content = f.read()

    meta    = parse_meta(content)
    header  = make_header(meta)
    content = inject_sr(content, providers)
    content = strip_comments_and_collapse(content)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(header)
        f.write(content)

    print(f'✓ SR built: {output_path}')
    return True

TARGETS = {
    'oc':    lambda p: build_clash('mihomo', p),
    'stash': lambda p: build_clash('stash', p),
    'sr':    lambda p: build_sr(p),
}

if __name__ == '__main__':
    secrets_path = ROOT / 'clash/src/secrets.yaml'

    if not secrets_path.exists():
        print(f'✗ Missing: {secrets_path}')
        print('  Create clash/src/secrets.yaml with your subscription URLs.')
        sys.exit(1)

    args = sys.argv[1:]
    if args:
        unknown = [a for a in args if a not in TARGETS]
        if unknown:
            print(f'✗ Unknown targets: {", ".join(unknown)}')
            print(f'  Valid targets: {", ".join(TARGETS)}')
            sys.exit(1)
        selected = args
    else:
        selected = list(TARGETS)

    providers = load_providers(secrets_path)
    results = [TARGETS[t](providers) for t in selected]
    sys.exit(0 if all(results) else 1)
