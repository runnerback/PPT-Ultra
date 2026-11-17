#!/usr/bin/env python3
"""Test compact upload restoration, integrity failures and a real built package."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

from upload_bootstrap import restore


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.package = Path(self.work.name) / "package"
        self.package.mkdir()
        self.cache = Path(self.work.name) / "cache with spaces"

    def bundle(self, files, member_type=None):
        archive = self.package / "runtime.tar.gz"
        entries = {}
        with tarfile.open(archive, "w:gz") as tar:
            for name, data in files.items():
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                if member_type:
                    entry.type = member_type
                    entry.linkname = "outside"
                tar.addfile(entry, io.BytesIO(data))
                entries[name] = {"sha256": hashlib.sha256(data).hexdigest(),
                                 "size": len(data), "mode": 0o644}
        manifest = {"format": 1, "file_count": len(files), "files": entries,
                    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
        (self.package / "runtime-manifest.json").write_text(json.dumps(manifest))

    def test_restore_and_reuse_without_writing_package(self):
        self.bundle({"SKILL.md": b"instructions", "assets/图标.svg": b"<svg/>"})
        before = {p.name: p.read_bytes() for p in self.package.iterdir()}
        first = restore(self.package, self.cache)
        self.assertFalse(first["cached"])
        self.assertEqual((Path(first["skill_dir"]) / "assets/图标.svg").read_bytes(), b"<svg/>")
        (Path(first["skill_dir"]) / ".env").write_text("USER_SETTING=keep")
        second = restore(self.package, self.cache, verify=True)
        self.assertTrue(second["cached"])
        self.assertEqual(first["skill_dir"], second["skill_dir"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.package.iterdir()})
        self.assertEqual((Path(first["skill_dir"]) / ".env").read_text(), "USER_SETTING=keep")

    def test_corrupt_archive_fails_before_extracting(self):
        self.bundle({"SKILL.md": b"instructions"})
        with (self.package / "runtime.tar.gz").open("ab") as out:
            out.write(b"corrupted")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            restore(self.package, self.cache)
        self.assertFalse(self.cache.exists())

    def test_verify_detects_changed_cached_files(self):
        self.bundle({"SKILL.md": b"instructions"})
        result = restore(self.package, self.cache)
        (Path(result["skill_dir"]) / "SKILL.md").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "Runtime verification failed"):
            restore(self.package, self.cache, verify=True)

    def test_path_traversal_is_rejected(self):
        self.bundle({"../outside": b"escape"})
        with self.assertRaisesRegex(ValueError, "Invalid archive path"):
            restore(self.package, self.cache)
        self.assertFalse((self.cache / "outside").exists())

    def test_symbolic_links_are_rejected(self):
        self.bundle({"SKILL.md": b""}, member_type=tarfile.SYMTYPE)
        with self.assertRaisesRegex(ValueError, "Unexpected runtime member"):
            restore(self.package, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_mismatched_file_digest_leaves_no_cache(self):
        self.bundle({"SKILL.md": b"instructions"})
        path = self.package / "runtime-manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"]["SKILL.md"]["sha256"] = "0" * 64
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Runtime checksum mismatch"):
            restore(self.package, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])


def verify_package(path: Path, smoke: bool = False) -> None:
    root = Path(__file__).resolve().parent.parent
    source = root / "skills" / "ppt-ultra"
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", "skills/ppt-ultra"], cwd=root)
    expected = {p.relative_to(source).as_posix(): p
                for name in tracked.split(b"\0") if name
                for p in [root / name.decode("utf-8")]}
    with tempfile.TemporaryDirectory(prefix="ppt-ultra-upload-test-") as work:
        package = Path(work) / "uploaded skill"
        with zipfile.ZipFile(path) as z:
            assert len(z.infolist()) <= 500
            assert sum(p.file_size for p in z.infolist()) <= 100_000_000
            assert path.stat().st_size <= 100_000_000
            assert "SKILL.md" in z.namelist()  # Direct upload root, not a nested folder.
            assert not any(p.is_dir() for p in z.infolist())
            z.extractall(package)
        command = [sys.executable, str(package / "bootstrap.py"), "--cache-dir", str(Path(work) / "cache")]
        first = json.loads(subprocess.check_output(command, cwd=work))
        runtime = Path(first["skill_dir"])
        assert not first["cached"]
        actual = {p.relative_to(runtime).as_posix() for p in runtime.rglob("*") if p.is_file()}
        assert actual == set(expected), f"Restored file set differs: {actual ^ set(expected)}"
        for name, original in expected.items():
            assert (runtime / name).read_bytes() == original.read_bytes(), f"Content changed: {name}"
            if original.suffix == ".md" and name != "SKILL.md":
                assert (package / name).read_bytes() == original.read_bytes(), f"Visible reference changed: {name}"
        second = json.loads(subprocess.check_output(command + ["--verify"], cwd=work))
        assert second["cached"] and second["skill_dir"] == first["skill_dir"]
        subprocess.run([sys.executable, str(runtime / "scripts/attribution_guard.py")], check=True, cwd=work)
        if shutil.which("node") and not smoke:
            subprocess.run(["node", str(runtime / "engines/html-editorial/scripts/check-presenter-runtime-sync.mjs")],
                           check=True, cwd=work, stdout=subprocess.DEVNULL)
        if smoke:
            # Run the existing suite against the restored skill, not the source tree.
            checkout = Path(work) / "smoke-checkout"
            (checkout / "skills").mkdir(parents=True)
            (checkout / "skills/ppt-ultra").symlink_to(runtime, target_is_directory=True)
            shutil.copytree(root / "tools", checkout / "tools", ignore=shutil.ignore_patterns("__pycache__"))
            subprocess.run(["bash", str(checkout / "tools/smoke.sh")], check=True,
                           env={**os.environ, "PYTHON": sys.executable}, cwd=work)
        print(f"PASS: {len(expected)} files restored byte-for-byte; cache reuse and integrity gate passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, help="Also verify a built ZIP against the current source tree")
    parser.add_argument("--smoke", action="store_true", help="Run tools/smoke.sh against the restored skill (requires its dependencies)")
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BootstrapTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.zip:
        verify_package(args.zip.resolve(), smoke=args.smoke)
