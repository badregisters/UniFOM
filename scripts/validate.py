"""Structural checks for generated configurations; no network access required."""
import re
import sys
from pathlib import Path

import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f'Duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def validate_text(text, platform):
    if re.search(r'__[A-Z_]+__|\[GENERATED:', text):
        raise ValueError('Unresolved generation marker')
    if platform == 'clash':
        data = yaml.load(text, Loader=UniqueLoader)
        if not isinstance(data, dict):
            raise ValueError('Configuration must be a mapping')
        groups = data.get('proxy-groups', [])
        names = [g['name'] for g in groups]
        proxies = [p['name'] for p in data.get('proxies', [])]
        if len(set(names + proxies)) != len(names + proxies):
            raise ValueError('Duplicate policy name')
        policies = set(names + proxies + ['DIRECT', 'REJECT', 'REJECT-DROP', 'PASS', 'COMPATIBLE'])
        providers = data.get('proxy-providers', {})
        for group in groups:
            for policy in group.get('proxies', []):
                if policy not in policies:
                    raise ValueError(f'Unknown policy in group {group["name"]}: {policy}')
            for provider in group.get('use', []):
                if provider not in providers:
                    raise ValueError(f'Unknown provider: {provider}')
        rules = data.get('rules', [])
        rule_sets = data.get('rule-providers', {})
    else:
        sections = {}
        section = None
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('[') and line.endswith(']'):
                section = line[1:-1]
                if section in sections:
                    raise ValueError(f'Duplicate section: {section}')
                sections[section] = []
            elif section:
                sections[section].append(line)
            else:
                raise ValueError('Entry outside section')
        for required in ('General', 'Proxy Group', 'Rule'):
            if required not in sections:
                raise ValueError(f'Missing section: {required}')
        names = [line.split('=', 1)[0].strip() for line in sections['Proxy Group']]
        if len(set(names)) != len(names):
            raise ValueError('Duplicate policy name')
        policies = set(names + ['DIRECT', 'REJECT', 'REJECT-DROP', 'PROXY'])
        rules = sections['Rule']
        rule_sets = None
    for rule in rules:
        parts = rule.split(',')
        if len(parts) < 2:
            raise ValueError(f'Malformed rule: {rule}')
        policy = parts[-2] if parts[-1].strip() == 'no-resolve' else parts[-1]
        if policy.strip() not in policies:
            raise ValueError(f'Unknown rule policy: {policy}')
        if parts[0] == 'RULE-SET' and rule_sets is not None and parts[1] not in rule_sets:
            raise ValueError(f'Unknown rule provider: {parts[1]}')


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        path = Path(filename)
        validate_text(path.read_text(), 'sr' if path.suffix == '.conf' else 'clash')
        print(f'Validated: {path.name}')
