"""Report rule overlap without changing routing decisions."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
from urllib.request import urlopen

import yaml
from validate import validate_text


def parse_rule(rule):
    parts = [p.strip() for p in rule.split(',')]
    if parts[-1] == 'no-resolve':
        parts.pop()
    if len(parts) != 3 or parts[0] not in ('DOMAIN', 'DOMAIN-SUFFIX', 'IP-CIDR', 'IP-CIDR6'):
        return None
    kind, value, policy = parts
    value = value.lower().rstrip('.')
    if '*' in value or value.startswith('+.'):
        return None
    if kind.startswith('IP-CIDR'):
        value = ipaddress.ip_network(value, strict=False)
    return kind, value, policy


def covers(first, second):
    kind, value, _ = first
    other_kind, other_value, _ = second
    if kind == 'DOMAIN':
        return other_kind == kind and value == other_value
    if kind == 'DOMAIN-SUFFIX' and other_kind in ('DOMAIN', kind):
        return other_value == value or other_value.endswith('.' + value)
    if kind.startswith('IP-CIDR') and other_kind.startswith('IP-CIDR'):
        return value.version == other_value.version and other_value.subnet_of(value)
    return False


def audit(path, remote=False, exceptions=None):
    text = path.read_text()
    platform = 'sr' if path.suffix == '.conf' else 'clash'
    validate_text(text, platform)
    if platform == 'clash':
        data = yaml.safe_load(text)
        rules = data['rules']
        providers = data.get('rule-providers', {})
    else:
        section = text.split('[Rule]', 1)[1].split('\n[', 1)[0]
        rules = [line.strip() for line in section.splitlines() if line.strip() and not line.startswith('#')]
        providers = {}
    expanded = []
    incomplete = []
    skipped = []
    for index, rule in enumerate(rules, 1):
        if rule.startswith('RULE-SET,'):
            parts = rule.split(',')
            name, policy = parts[1], parts[2]
            provider = providers.get(name, {})
            url = provider.get('url', name if platform == 'sr' else None)
            if not remote:
                incomplete.append({'rule': index, 'reason': 'remote not requested'})
                continue
            try:
                if not url or not url.startswith(('https://', 'http://')):
                    raise ValueError('No supported URL')
                with urlopen(url, timeout=20) as response:
                    raw = response.read(10_000_001)
                if len(raw) > 10_000_000:
                    raise ValueError('Rule set too large')
                if provider.get('format') == 'mrs':
                    raise ValueError('MRS requires conversion to text')
                content = raw.decode('utf-8-sig')
                entries = yaml.safe_load(content).get('payload', []) if 'payload:' in content else content.splitlines()
                for entry in entries:
                    entry = str(entry).strip()
                    if not entry or entry.startswith('#'):
                        continue
                    behavior = provider.get('behavior', 'classical')
                    if behavior == 'domain':
                        entry = ('DOMAIN-SUFFIX,' + entry[2:]) if entry.startswith('+.') else 'DOMAIN,' + entry
                    elif behavior == 'ipcidr':
                        entry = ('IP-CIDR6,' if ':' in entry else 'IP-CIDR,') + entry
                    pieces = entry.split(',')
                    expanded.append((f'{index}:{len(expanded)}', ','.join(pieces[:2]) + ',' + policy))
            except Exception as error:
                incomplete.append({'rule': index, 'reason': type(error).__name__})
        else:
            expanded.append((str(index), rule))
    findings = []
    previous = []
    exceptions = exceptions or {}
    for location, rule in expanded:
        parsed = parse_rule(rule)
        if parsed is None:
            skipped.append(location)
            continue
        for old_location, old_rule, old_parsed in previous:
            if covers(old_parsed, parsed):
                identifier = hashlib.sha256((old_rule + '\n' + rule).encode()).hexdigest()[:16]
                findings.append({'id': identifier, 'earlier': old_location, 'later': location,
                                 'kind': 'redundant' if old_parsed[2] == parsed[2] else 'policy-conflict',
                                 'reason': exceptions.get(identifier)})
                break
        previous.append((location, rule, parsed))
    return {'file': path.name, 'structural_validation': 'passed', 'findings': findings,
            'incomplete_remote': incomplete, 'unsupported_rules': skipped,
            'complete': not incomplete and not skipped}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path)
    parser.add_argument('--remote', action='store_true')
    parser.add_argument('--exceptions', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    exceptions = json.loads(args.exceptions.read_text()) if args.exceptions else {}
    report = audit(args.config, args.remote, exceptions)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    readable = [f'Rule audit: {report["file"]}',
                f'Findings: {len(report["findings"])}',
                f'Unfetched/failed rule sets: {len(report["incomplete_remote"])}',
                f'Unsupported rules: {len(report["unsupported_rules"])}']
    readable.extend(f'{item["kind"]}: rule {item["earlier"]} covers {item["later"]}'
                    for item in report['findings'])
    args.output.with_suffix('.txt').write_text('\n'.join(readable) + '\n')
    print('\n'.join(readable[:4]))
