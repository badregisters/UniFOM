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
#   clash/openclash/dist/UniFOM.yaml        - deployable OC config, all providers (gitignored, local only)
#   clash/openclash/dist/UniFOM-shared.yaml - deployable OC config, shared providers only (gitignored, local only)
#   clash/stash/dist/UniFOM.yaml            - deployable Stash config (gitignored, local only)
#   shadowrocket/dist/UniFOM.conf           - deployable SR config (in git)
#
# secrets.yaml format:
#   Simple entry (defaults to regional + manual groups, not shared):
#     FlowerCloud: "https://..."
#
#   Extended entry (all fields optional except url):
#     FlowerCloud:
#       url: "https://..."
#       groups: manual          # comma-separated string or YAML list; default: regional,manual
#       extra_domains: [xmancdn.com]  # secondary CDN domains not derivable from URL
#       shared: true            # include in oc-shared build; default: false

import os
import re
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

ROOT = Path(__file__).parent.parent
PROJECT_URL = 'https://github.com/badregisters/UniFOM'

# Default filter applied to all proxy providers
PROVIDER_FILTER = (
    r'(?i)(香港|🇭🇰|HK|美国|🇺🇸|\bUS\b|日本|🇯🇵|JP|'
    r'台湾|🇹🇼|TW|Taiwan|新加坡|狮城|🇸🇬|SG|英国|🇬🇧|UK|'
    r'喀麦隆|冰岛|土耳其|阿根廷|印度|🇮🇳|India)'
)

# Subscription metadata disguised as proxies. Keep this anchored and specific so
# legitimate nodes containing generic words such as "traffic" are not removed.
PROVIDER_EXCLUDE_FILTER = (
    r'(?i)^(Test latency|Traffic *[:：]|Expire *[:：]|'
    r'应急续费节点(-[0-9]+X)?|剩余流量 *[:：]|'
    r'距离下次重置(剩余)? *[:：]|套餐到期 *[:：])'
)

SHARED_PROVIDER_GROUPS = '''  # [proxy-provider-groups start]
  - {name: 🇭🇰 香港节点, type: url-test, tolerance: 20, filter: "(?i)(🇭🇰|港|Hong|HK)", use: [__USE_shared__]}
  - {name: 🇹🇼 台湾节点, type: url-test, tolerance: 20, filter: "(?i)(🇹🇼|台|Tai|TW)", use: [__USE_shared__]}
  - {name: 🇯🇵 日本节点, type: url-test, tolerance: 20, filter: "(?i)(🇯🇵|日|Japan|JP)", use: [__USE_shared__]}
  - {name: 🇸🇬 狮城节点, type: url-test, tolerance: 20, filter: "(?i)(🇸🇬|新|Singapore|SG)", use: [__USE_shared__]}
  - {name: 🇺🇸 美国节点, type: url-test, tolerance: 50, filter: '(?i)(🇺🇸|美|States|\\bUS\\b)', use: [__USE_shared__]}
  - {name: 🇬🇧 英国节点, type: url-test, tolerance: 50, filter: "(?i)(🇬🇧|英|Kingdom|UK)", use: [__USE_shared__]}
  - {name: 🇺🇳 小众节点, type: select, filter: "(?i)(喀麦隆|冰岛|土耳其|阿根廷|印度|🇮🇳|India)", use: [__USE_shared__]}
  # [proxy-provider-groups end]'''

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
    platform  = meta.get('platform', 'Unknown')
    version   = meta.get('version',  'unknown')
    updated   = meta.get('updated',  'unknown')
    generated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f'# {platform} | {version} | {updated} | {PROJECT_URL}\n# Generated: {generated}\n\n'

def strip_comments_and_collapse(content):
    result = []
    prev_blank = False
    for line in content.splitlines(keepends=True):
        if line.lstrip().startswith('#'):
            continue
        # Strip inline comments: whitespace + # + anything to EOL.
        # Safe: meaningful # in values (e.g. nameserver group "...#🚀 节点选择")
        # is never preceded by whitespace, so won't be matched.
        stripped = re.sub(r'\s+#.*$', '', line.rstrip('\n'))
        line = stripped + ('\n' if line.endswith('\n') else '')
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

    def parse_groups(value, default):
        if isinstance(value, str):
            return [g.strip() for g in value.split(',')]
        if isinstance(value, list):
            return [str(g) for g in value]
        return list(default)

    providers = {}
    for name, value in raw.items():
        if isinstance(value, str):
            providers[name] = {'url': value, 'groups': ['regional', 'manual'],
                               'extra_domains': [], 'shared': False, 'full': True,
                               'provider_filter': PROVIDER_FILTER}
        elif isinstance(value, dict):
            groups = parse_groups(value.get('groups'), ['regional', 'manual'])
            extra = value.get('extra_domains', [])
            if isinstance(extra, str):
                extra = [extra]
            shared = bool(value.get('shared', False))
            full = bool(value.get('full', True))
            provider_filter = value.get('provider_filter') or PROVIDER_FILTER
            providers[name] = {'url': value['url'], 'groups': groups,
                               'extra_domains': list(extra), 'shared': shared, 'full': full,
                               'provider_filter': provider_filter}
    return providers

def gen_proxy_providers(providers, platform):
    """Generate the full proxy-providers: YAML block."""
    lines = ['proxy-providers:']
    for name, info in providers.items():
        provider_lines = [
            f'  {name}:',
            f'    type: http',
            f'    url: "{info["url"]}"',
            f'    interval: 86400',
            f'    path: ./proxy_provider/{name}.yaml',
            f"    filter: '{info['provider_filter']}'",
        ]
        if platform == 'mihomo':
            provider_lines.append(f"    exclude-filter: '{PROVIDER_EXCLUDE_FILTER}'")
        if platform == 'mihomo':
            health_check = (
                '    health-check: {enable: true, interval: 3600, lazy: false, '
                'url: https://cp.cloudflare.com/generate_204}'
            )
        else:
            health_check = (
                '    health-check: {enable: true, interval: 1800, '
                'url: https://cp.cloudflare.com/generate_204}'
            )
        provider_lines += [health_check, '']
        lines += provider_lines
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

def flatten_shared_groups(content):
    """Replace premium/standard fallback groups with one shared url-test pool."""
    for region in ('香港', '台湾', '日本', '狮城', '美国', '英国'):
        content = content.replace(f'{region}·优选', f'{region}节点')
        content = content.replace(f'{region}·标准', f'{region}节点')

    pattern = re.compile(
        r'  # \[proxy-provider-groups start\].*?'
        r'  # \[proxy-provider-groups end\]',
        re.DOTALL,
    )
    return pattern.sub(lambda _: SHARED_PROVIDER_GROUPS, content)

def inject_clash(content, providers, platform, shared=False):
    """Replace all generation markers in base.yaml content."""
    if shared:
        content = flatten_shared_groups(content)

    content = content.replace(
        '# [GENERATED: proxy-providers]',
        gen_proxy_providers(providers, platform)
    )
    content = content.replace(
        '  # [GENERATED: direct-domains]',
        gen_direct_domains_clash(providers)
    )
    if shared:
        shared_use = ', '.join(providers)
        content = content.replace('[__USE_regional__]', f'[{shared_use}]')
        content = content.replace('[__USE_manual__]',   f'[{shared_use}]')
        content = content.replace('[__USE_economy__]',  f'[{shared_use}]')
        content = content.replace('[__USE_shared__]',   f'[{shared_use}]')
    else:
        content = content.replace('[__USE_regional__]', f'[{use_list(providers, "regional")}]')
        content = content.replace('[__USE_manual__]',   f'[{use_list(providers, "manual")}]')
        content = content.replace('[__USE_economy__]',  f'[{use_list(providers, "economy")}]')
    content = content.replace('[__USE_premium__]',  f'[{use_list(providers, "premium")}]')
    content = content.replace('[__USE_standard__]', f'[{use_list(providers, "standard")}]')
    content = content.replace('__FALLBACK_LAZY__', 'true' if platform == 'mihomo' else 'false')
    return content


def build_clash(platform, providers, suffix='', shared=False):
    platform_path = ROOT / f'clash/src/platform/{platform}.yaml'
    base_path     = ROOT / 'clash/src/base.yaml'

    if platform == 'mihomo':
        output_path = ROOT / f'clash/openclash/dist/UniFOM{suffix}.yaml'
        label    = f'OC{suffix}' if suffix else 'OC'
        gist_env = 'OC_SHARED_GIST_ID' if suffix else 'OC_GIST_ID'
    elif platform == 'stash':
        output_path = ROOT / f'clash/stash/dist/UniFOM{suffix}.yaml'
        label    = f'Stash{suffix}' if suffix else 'Stash'
        gist_env = None
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
    combined = inject_clash(combined, providers, platform, shared)
    combined = strip_comments_and_collapse(combined)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(header)
        f.write(combined)

    print(f'✓ {label} built: {output_path}')

    if gist_env:
        gist_id = os.environ.get(gist_env)
        if gist_id:
            result = subprocess.run(
                ['gh', 'gist', 'edit', gist_id, '--filename', output_path.name, str(output_path)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f'✓ {label} synced to Gist: {gist_id}')
            else:
                print(f'✗ Gist sync failed: {result.stderr.strip()}')

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
    'oc':        lambda p: build_clash('mihomo', {k: v for k, v in p.items() if v['full']}),
    'oc-shared': lambda p: build_clash('mihomo', {k: v for k, v in p.items() if v['shared']}, suffix='-shared', shared=True),
    'stash':     lambda p: build_clash('stash', {k: v for k, v in p.items() if v['full']}),
    'sr':        lambda p: build_sr({k: v for k, v in p.items() if v['full']}),
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
