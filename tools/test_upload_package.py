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

    def multibundle(self):
        entries, volumes = {}, []
        for i, name in enumerate(("SKILL.md", "assets/example.svg"), 1):
            self.bundle({name: name.encode()})
            old = json.loads((self.package / "runtime-manifest.json").read_text())
            archive = f"runtime-{i:03d}.tar.gz"
            (self.package / "runtime.tar.gz").rename(self.package / archive)
            entries[name] = {**old["files"][name], "archive": archive}
            volumes.append({"name": archive, "sha256": old["archive_sha256"], "file_count": 1})
        manifest = {"format": 2, "file_count": 2, "files": entries, "archives": volumes}
        (self.package / "runtime-manifest.json").write_text(json.dumps(manifest))
        return manifest

    def test_multiple_volumes_restore_and_verify(self):
        self.multibundle()
        result = restore(self.package, self.cache)
        self.assertEqual((Path(result["skill_dir"]) / "assets/example.svg").read_bytes(), b"assets/example.svg")
        self.assertTrue(restore(self.package, self.cache, verify=True)["cached"])

    def test_missing_volume_rejected_even_for_cached_runtime(self):
        self.multibundle()
        restore(self.package, self.cache)
        (self.package / "runtime-002.tar.gz").unlink()
        with self.assertRaises(FileNotFoundError):
            restore(self.package, self.cache)

    def test_wrong_volume_rejected_without_partial_cache(self):
        manifest = self.multibundle()
        manifest["files"]["SKILL.md"]["archive"] = "runtime-002.tar.gz"
        (self.package / "runtime-manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "wrong volume"):
            restore(self.package, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_corrupt_second_volume_rejected_before_extraction(self):
        self.multibundle()
        with (self.package / "runtime-002.tar.gz").open("ab") as out:
            out.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            restore(self.package, self.cache)
        self.assertFalse(self.cache.exists())


def verify_package(path: Path, smoke: bool = False) -> None:
    root = Path(__file__).resolve().parent.parent
    source = root / "skills" / "ppt-ultra"
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", "skills/ppt-ultra"], cwd=root)
    expected = {p.relative_to(source).as_posix(): p
                for name in tracked.split(b"\0") if name
                for p in [root / name.decode("utf-8")]}
    for name in ("LICENSE-AGPL-3.0", "requirements.lock"):
        expected[name] = source / name
    with tempfile.TemporaryDirectory(prefix="ppt-ultra-upload-test-") as work:
        package = Path(work) / "uploaded skill"
        with zipfile.ZipFile(path) as z:
            assert len(z.infolist()) <= 500
            assert sum(p.file_size for p in z.infolist()) <= 100_000_000
            assert path.stat().st_size <= 100_000_000
            assert "SKILL.md" in z.namelist()  # Direct upload root, not a nested folder.
            original = (source / "SKILL.md").read_text()
            boundary = original[original.index("## 安全边界（P1–P4）"):original.index("## Mandatory Load Order")]
            assert boundary in z.read("SKILL.md").decode()
            manifest = json.loads(z.read("runtime-manifest.json"))
            assert manifest["format"] == 2
            assert all(p.file_size <= manifest["max_part_bytes"] for p in z.infolist())
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


def verify_audit(path: Path) -> None:
    source = Path(__file__).resolve().parent.parent / "skills/ppt-ultra"
    manifest = json.loads(path.read_text())
    seen = set()
    for volume in manifest["volumes"]:
        archive = path.parent / volume["name"]
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == volume["sha256"]
        assert archive.stat().st_size <= manifest["max_part_bytes"]
        with zipfile.ZipFile(archive) as z:
            assert len(z.infolist()) <= 350
            assert sum(info.file_size for info in z.infolist()) <= manifest["max_part_bytes"]
            assert set(z.namelist()) == set(volume["files"])
            for name in z.namelist():
                assert name not in seen
                assert not name.endswith((".zip", ".gz")), "Source review volumes must not nest archives"
                data = z.read(name)
                assert data == (source / name).read_bytes()
                assert hashlib.sha256(data).hexdigest() == manifest["files"][name]["sha256"]
                seen.add(name)
    assert seen == set(manifest["files"])
    # Independent expected coverage: every tracked executable-source file, plus locks.
    root = source.parent.parent
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", "skills/ppt-ultra"], cwd=root)
    for raw in tracked.split(b"\0"):
        if raw:
            file = root / raw.decode()
            if file.suffix in {".py", ".js", ".mjs", ".jsx", ".ts", ".sh", ".ps1"}:
                assert file.relative_to(source).as_posix() in seen
    assert {"requirements.lock", "engines/html-themed/project/package-lock.json", "SKILL.md", "LICENSE-AGPL-3.0"} <= seen
    print(f"PASS: {len(seen)} plaintext review files in {len(manifest['volumes'])} bounded source ZIPs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, help="Also verify a built ZIP against the current source tree")
    parser.add_argument("--smoke", action="store_true", help="Run tools/smoke.sh against the restored skill (requires its dependencies)")
    parser.add_argument("--audit-manifest", type=Path, help="Verify plaintext source volumes, coverage, hashes and size limits")
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BootstrapTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.zip:
        verify_package(args.zip.resolve(), smoke=args.smoke)
    if args.audit_manifest:
        verify_audit(args.audit_manifest.resolve())
