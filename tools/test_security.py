#!/usr/bin/env python3
"""Offline regression checks for distribution security boundaries (stdlib only)."""
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / 'skills/ppt-ultra'
PROJECT = SKILL / 'engines/html-themed/project'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class SecurityTests(unittest.TestCase):
    def test_python_dependency_closure_is_exact_and_hashed(self):
        requirements = (SKILL / 'requirements.txt').read_text()
        self.assertIn('--require-hashes', requirements)
        self.assertIn('--only-binary=:all:', requirements)
        self.assertIn('-r requirements.lock', requirements)
        lock = (SKILL / 'requirements.lock').read_text()
        records = re.findall(r'^([a-zA-Z0-9][^\n]*(?:\n[ \t]+[^\n]*)*)', lock, re.M)
        self.assertGreater(len(records), 19)
        pins = set()
        for record in records:
            first = record.splitlines()[0].rstrip(' \\')
            self.assertRegex(first, r'^[A-Za-z0-9_.-]+==[0-9][^ ;]*')
            self.assertRegex(record, r'--hash=sha256:[0-9a-f]{64}')
            self.assertNotRegex(first.split(';')[0], r'>=|<=|~=| @ |https?://')
            pins.add(first)
        direct = {line for line in (ROOT / 'tools/python-requirements.in').read_text().splitlines() if line and not line.startswith('#')}
        self.assertEqual(len({line.split('==')[0] for line in direct}), 19)
        self.assertTrue(direct <= pins, direct - pins)

    def test_npm_direct_pins_and_transitive_integrity(self):
        package = json.loads((PROJECT / 'package.json').read_text())
        lock = json.loads((PROJECT / 'package-lock.json').read_text())
        for group in ('dependencies', 'devDependencies'):
            self.assertEqual(package[group], lock['packages'][''][group])
            for name, version in package[group].items():
                self.assertRegex(version, r'^\d+\.\d+\.\d+$')
                self.assertEqual(version, lock['packages']['node_modules/' + name]['version'])
        for name, item in lock['packages'].items():
            if name:
                self.assertRegex(item['integrity'], r'^sha512-[A-Za-z0-9+/]+=*$')

    def test_launchers_do_not_install_browsers_or_use_mirrors(self):
        for extension in ('sh', 'ps1'):
            script = (SKILL / f'engines/html-themed/scripts/render_goal_deck.{extension}').read_text()
            self.assertIn('--ignore-scripts', script)
            self.assertNotRegex(script, r'npmmirror|PLAYWRIGHT_DOWNLOAD_HOST|npm install|install chromium')
        self.assertNotRegex((PROJECT / 'npmrc.template').read_text(), r'(?m)^registry\s*=')

    def test_entrypoint_boundaries_and_neutral_sponsors(self):
        source = (SKILL / 'SKILL.md').read_text()
        boundary = source[source.index('## 安全边界（P1–P4）'):source.index('## Mandatory Load Order')]
        for label in ('P1', 'P2', 'P3', 'P4', '不得', '日志', '外部'):
            self.assertIn(label, boundary)
        self.assertIn('license: "AGPL-3.0 (bundles MIT components; see NOTICE.md)"', source)
        for name in ('SPONSORS.md', 'SPONSORS_CN.md'):
            self.assertNotRegex((SKILL / name).read_text(), r'(?i)aff=|packyapi|apikey\.fan|runapi\.host')

    def test_attribution_guard_still_rejects_license_and_metadata_tampering(self):
        guard = module('security_guard', SKILL / 'scripts/attribution_guard.py')
        self.assertTrue(guard._metadata_is_valid())
        self.assertTrue(guard._protected_files_are_valid())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (*guard._REQUIRED_ATTRIBUTION_FILES, 'SKILL.md'):
                shutil.copyfile(SKILL / name, root / name)
            guard._SKILL_DIR = root
            for name in ('LICENSE', 'LICENSE-AGPL-3.0'):
                original = (root / name).read_bytes()
                (root / name).write_bytes(original + b'tampered')
                self.assertFalse(guard._protected_files_are_valid())
                (root / name).write_bytes(original)
            text = (root / 'SKILL.md').read_text()
            (root / 'SKILL.md').write_text(text.replace('upstream_license: "MIT"', 'upstream_license: "invalid"'))
            self.assertFalse(guard._metadata_is_valid())

    def test_python_automatic_log_omits_argument_and_output_content(self):
        transcript = module('security_transcript', SKILL / 'scripts/workflow_transcript.py')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'audit.log'
            audit = transcript._AutomaticTranscript(path.open('w'), io.StringIO(), ['tool.py', 'PRIVATE_SENTINEL'])
            audit.start()
            audit.write_stream('stdout', '[ERROR] PRIVATE_SENTINEL\n')
            audit.write_stream('stderr', 'secret PRIVATE_SENTINEL')
            audit.close()
            self.assertNotIn('PRIVATE_SENTINEL', path.read_text())
            self.assertIn('output_lines=2', path.read_text())

    @unittest.skipUnless(shutil.which('node'), 'Node.js not available')
    def test_registry_validation_does_not_echo_credentials(self):
        command = ['node', str(PROJECT / 'scripts/ensure-registry.mjs')]
        env = {**os.environ, 'PPT_ULTRA_NPM_REGISTRY': 'https://user:PRIVATE_SENTINEL@example.invalid'}
        result = subprocess.run(command, capture_output=True, text=True, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('PRIVATE_SENTINEL', result.stdout + result.stderr)
        env.pop('PPT_ULTRA_NPM_REGISTRY')
        self.assertEqual(subprocess.check_output(command, env=env, text=True).strip(), 'https://registry.npmjs.org')

    @unittest.skipUnless(shutil.which('node'), 'Node.js not available')
    def test_js_telemetry_omits_error_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = """
                const {beginWorkflowStage} = await import(process.argv[1]);
                beginWorkflowStage({goalPath: process.argv[2], stage: 'render', runId: 'test'})
                  .finish({ok: false, error: new Error('browser PRIVATE_SENTINEL')});
            """
            subprocess.run(['node', '--input-type=module', '-e', script,
                            (PROJECT / 'scripts/workflow-telemetry.mjs').as_uri(), str(Path(tmp) / 'goal.json')], check=True)
            report = (Path(tmp) / 'workflow-telemetry.json').read_text()
            self.assertNotIn('PRIVATE_SENTINEL', report)
            self.assertEqual(json.loads(report)['failureCount'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
