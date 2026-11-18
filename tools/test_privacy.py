#!/usr/bin/env python3
"""Test privacy rules using synthetic examples only."""
import importlib.util
from pathlib import Path
import re
import unittest

spec = importlib.util.spec_from_file_location('privacy', Path(__file__).with_name('privacy-check.py'))
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


class PrivacyTests(unittest.TestCase):
    def test_secret_and_private_containers_are_rejected(self):
        self.assertTrue(privacy.check_file('.env.production', b''))
        self.assertTrue(privacy.check_file('signing.p12', b'\x00\x01'))
        self.assertFalse(privacy.check_file('.env.example', b'# Empty configuration'))

    def test_internal_network_and_personal_paths(self):
        address = 'https://' + '.'.join(['10', '20', '30', '40']) + '/api'
        path = '/Users/' + 'synthetic-person' + '/project'
        findings = privacy.check_file('sample.md', (address + '\n' + path).encode())
        self.assertEqual({f['rule'] for f in findings}, {'private-network-endpoint', 'personal-home-path'})
        self.assertEqual([f['line'] for f in findings], [2, 1])
        self.assertNotIn(address, repr(findings))
        self.assertNotIn('synthetic-person', repr(findings))

    def test_examples_and_licenses_remain_valid(self):
        self.assertFalse(privacy.check_file('sample.md', b'hello@sample.example https://127.0.0.1:5200'))
        email = ('author' + '@' + 'synthetic-domain' + '.com').encode()
        self.assertTrue(privacy.check_file('sample.md', email))
        self.assertFalse(privacy.check_file('LICENSE', email))

    def test_local_patterns_are_never_echoed(self):
        findings = privacy.check_file('sample.md', b'private-fixture', [re.compile('private-fixture')])
        self.assertEqual(findings[0]['rule'], 'local-organization-pattern')
        self.assertNotIn('private-fixture', repr(findings))

    def test_path_prefix_examples_and_regex_are_not_usernames(self):
        self.assertFalse(privacy.check_file('example.py', b"prefix = '/Users/'"))
        self.assertFalse(privacy.check_file('example.py', b"pattern = r'(?:/Users/|/home/)name'"))


if __name__ == '__main__':
    unittest.main(verbosity=2)
