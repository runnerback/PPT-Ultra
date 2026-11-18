#!/usr/bin/env python3
"""Check tracked and unignored new files for privacy mistakes; never print values.

Complement this with Gitleaks for credential detection. Company-specific names
or domains can be supplied as one regex per line in an ignored local file.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})')
HOME = re.compile(r'(?:/Users/|/home/|[A-Z]:\\Users\\)([^/\\\s"\x27<>`|()\[\]{}]+)')
PRIVATE_KEY = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')
PRIVATE_IP = re.compile(r'https?://((?:\d{1,3}\.){3}\d{1,3})(?=[:/\s"\x27]|$)')
INTERNAL_HOST = re.compile(r'https?://[\w.-]+\.(?:internal|corp|intranet)(?=[:/\s"\x27]|$)', re.I)
PHONE = re.compile(r'(?:手机号|手机号码|mobile|phone)\s*[=:：]\s*["\x27]?(1[3-9]\d{9})(?!\d)', re.I)


def reserved_domain(domain: str) -> bool:
    domain = domain.lower()
    return (domain in {'example.com', 'example.org', 'example.net', 'users.noreply.github.com'}
            or domain.endswith(('.example', '.invalid', '.test', '.localhost')))


def check_file(name: str, data: bytes, extra_patterns: list[re.Pattern] | None = None) -> list[dict]:
    findings = []
    path = Path(name)
    def add(rule: str, offset: int = 0):
        # Deliberately omit snippets, matches and hashes of sensitive values.
        findings.append({'path': name, 'line': data[:offset].count(b'\n') + 1, 'rule': rule})
    if ((path.name == '.env' or path.name.startswith('.env.'))
            and path.name not in {'.env.example', '.env.template'}):
        add('private-environment-file')
    if path.suffix.lower() in {'.p12', '.pfx', '.key'} or path.name in {'id_rsa', 'id_ed25519', 'credentials.json', 'cookies.txt'}:
        add('credential-container-file')
    if b'\0' in data:
        return findings
    text = data.decode('utf-8', errors='replace')
    def match(rule, m):
        add(rule, len(text[:m.start()].encode('utf-8')))
    # Copyright/license notices may be required to preserve upstream attribution.
    attribution_file = path.name.upper().startswith(('LICENSE', 'COPYING', 'THIRD_PARTY_NOTICES'))
    if not attribution_file:
        for m in EMAIL.finditer(text):
            if not reserved_domain(m.group(1)):
                match('non-example-contact-email', m)
    for m in HOME.finditer(text):
        if m.group(1).lower() not in {'你的用户名', '用户名', 'username', 'user', 'example', 'runner'}:
            match('personal-home-path', m)
    for m in PRIVATE_KEY.finditer(text):
        match('private-key', m)
    for m in PRIVATE_IP.finditer(text):
        try:
            ip = ipaddress.ip_address(m.group(1))
        except ValueError:
            continue
        if any(ip in network for network in (ipaddress.ip_network('10.0.0.0/8'), ipaddress.ip_network('172.16.0.0/12'), ipaddress.ip_network('192.168.0.0/16'))):
            match('private-network-endpoint', m)
    for m in INTERNAL_HOST.finditer(text):
        match('internal-hostname', m)
    for m in PHONE.finditer(text):
        match('personal-phone-number', m)
    for pattern in extra_patterns or []:
        for m in pattern.finditer(text):
            match('local-organization-pattern', m)
    return findings


def scan(extra_patterns: list[re.Pattern] | None = None) -> tuple[int, list[dict]]:
    tracked = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    names = [n.decode('utf-8') for n in tracked.split(b'\0') if n]
    findings = []
    for name in names:
        path = ROOT / name
        if not path.exists():
            continue
        if path.is_symlink():
            findings.append({'path': name, 'line': 1, 'rule': 'symlink-requires-review'})
            continue
        findings.extend(check_file(name, path.read_bytes(), extra_patterns))
    return len(names), findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patterns-file', type=Path, help='Ignored LOCAL regex file; do not commit employer-specific patterns')
    parser.add_argument('--report', type=Path, help='Write only file/line/rule metadata, never matched values')
    args = parser.parse_args()
    patterns = []
    if args.patterns_file:
        try:
            patterns = [re.compile(line, re.I) for line in args.patterns_file.read_text().splitlines() if line.strip() and not line.startswith('#')]
        except (OSError, re.error):
            print('Unable to read or compile the local pattern file; contents omitted.', file=sys.stderr)
            return 2
    count, findings = scan(patterns)
    report = {'scanned_candidate_files': count, 'findings': findings}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    for item in findings:
        print(f"{item['path']}:{item['line']}: {item['rule']} (value omitted)")
    print(f"Privacy check: {count} tracked/unignored candidate files; {len(findings)} findings")
    return bool(findings)


if __name__ == '__main__':
    raise SystemExit(main())
