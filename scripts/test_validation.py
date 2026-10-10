import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile

from validate import validate_text
from audit import parse_rule, covers, audit
import build


class ValidationTests(unittest.TestCase):
    def test_unknown_provider_and_policy(self):
        for text in ('proxy-groups: [{name: x, use: [missing]}]',
                     'proxy-groups: []\nrules: [DOMAIN,a.example,missing]',
                     'a: 1\na: 2', '__USE_regional__'):
            with self.assertRaises(ValueError):
                validate_text(text, 'clash')

    def test_domain_boundary_and_cidr(self):
        broad = parse_rule('DOMAIN-SUFFIX,example.com,DIRECT')
        self.assertTrue(covers(broad, parse_rule('DOMAIN,a.example.com,REJECT')))
        self.assertFalse(covers(broad, parse_rule('DOMAIN,notexample.com,DIRECT')))
        self.assertTrue(covers(parse_rule('IP-CIDR,10.0.0.0/8,DIRECT'),
                               parse_rule('IP-CIDR,10.1.0.0/16,REJECT')))
        self.assertFalse(covers(parse_rule('IP-CIDR,10.0.0.0/8,DIRECT'),
                                parse_rule('IP-CIDR6,::/0,REJECT')))

    def test_conflict_and_failed_remote_are_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.yaml'
            path.write_text('proxy-groups: []\nrule-providers:\n  remote: {url: "https://example.com/rules"}\nrules:\n  - DOMAIN-SUFFIX,example.com,DIRECT\n  - DOMAIN,a.example.com,REJECT\n  - RULE-SET,remote,DIRECT\n')
            with patch('audit.urlopen', side_effect=TimeoutError):
                report = audit(path, remote=True)
            self.assertEqual(report['findings'][0]['kind'], 'policy-conflict')
            self.assertEqual(len(report['incomplete_remote']), 1)
            self.assertFalse(report['complete'])


if __name__ == '__main__':
    unittest.main()
