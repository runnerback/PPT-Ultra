#!/usr/bin/env python3
"""Restore the original PPT Ultra skill from a verified local resource archive."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import tempfile


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_path(name: str) -> Path:
    parts = PurePosixPath(name).parts
    if (not parts or PurePosixPath(name).is_absolute() or ".." in parts
            or "\\" in name or ":" in name or PurePosixPath(name).as_posix() != name):
        raise ValueError(f"Invalid archive path: {name!r}")
    return Path(*parts)


def verify_runtime(root: Path, manifest: dict) -> None:
    for name, info in manifest["files"].items():
        path = root / safe_path(name)
        if (not path.is_file() or path.is_symlink() or path.stat().st_size != info["size"]
                or digest_file(path) != info["sha256"]):
            raise ValueError(f"Runtime verification failed: {name}")


def restore(package: Path, cache: Path, verify: bool = False) -> dict:
    manifest_data = (package / "runtime-manifest.json").read_bytes()
    manifest = json.loads(manifest_data)
    if manifest["format"] not in (1, 2) or manifest["file_count"] != len(manifest["files"]):
        raise ValueError("Unsupported or inconsistent runtime manifest")
    for name in manifest["files"]:
        safe_path(name)
    if manifest["format"] == 1:
        archives = [{"name": "runtime.tar.gz", "sha256": manifest["archive_sha256"], "file_count": manifest["file_count"]}]
    else:
        archives = manifest["archives"]
        names = [a["name"] for a in archives]
        if not archives or len(set(names)) != len(names):
            raise ValueError("Missing or duplicate runtime volumes")
        if sum(a["file_count"] for a in archives) != manifest["file_count"]:
            raise ValueError("Runtime volume file counts do not match manifest")
        if any(info["archive"] not in names for info in manifest["files"].values()):
            raise ValueError("Unknown runtime volume in file manifest")
    for item in archives:
        relative = safe_path(item["name"])
        if len(relative.parts) != 1 or not item["name"].endswith(".tar.gz"):
            raise ValueError("Invalid runtime volume filename")
        archive = package / relative
        if archive.is_symlink() or digest_file(archive) != item["sha256"]:
            raise ValueError("Runtime archive checksum mismatch; re-upload the original package")
    identity = hashlib.sha256(manifest_data).hexdigest()
    target = cache.resolve() / identity
    runtime = target / "ppt-ultra"
    marker = target / ".complete"
    if marker.is_file() and marker.read_text(encoding="utf-8") == identity:
        if not (runtime / "SKILL.md").is_file():
            raise ValueError("Runtime cache is incomplete; use a fresh --cache-dir")
        if verify:
            verify_runtime(runtime, manifest)
        return {"skill_dir": str(runtime), "cached": True, "files": manifest["file_count"]}
    if target.exists():
        raise ValueError("Incomplete cache directory; use a fresh --cache-dir")
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".unpack-", dir=cache) as work:
        stage = Path(work) / "ready"
        restored = stage / "ppt-ultra"
        restored.mkdir(parents=True)
        seen = set()
        for item in archives:
            volume_count = 0
            with tarfile.open(package / item["name"], "r:gz") as tar:
                for member in tar:
                    relative = safe_path(member.name)
                    if not member.isfile() or member.name in seen or member.name not in manifest["files"]:
                        raise ValueError(f"Unexpected runtime member: {member.name}")
                    info = manifest["files"][member.name]
                    if manifest["format"] == 2 and info["archive"] != item["name"]:
                        raise ValueError(f"Runtime member in wrong volume: {member.name}")
                    if member.size != info["size"]:
                        raise ValueError(f"Runtime size mismatch: {member.name}")
                    destination = restored / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as source, destination.open("xb") as out:
                        shutil.copyfileobj(source, out)
                    if digest_file(destination) != info["sha256"]:
                        raise ValueError(f"Runtime checksum mismatch: {member.name}")
                    destination.chmod(info["mode"] & 0o777)
                    seen.add(member.name)
                    volume_count += 1
            if volume_count != item["file_count"]:
                raise ValueError(f"Runtime volume file count mismatch: {item['name']}")
        if seen != set(manifest["files"]):
            raise ValueError("Runtime archive is missing files")
        (stage / ".complete").write_text(identity, encoding="utf-8")
        try:
            stage.rename(target)
        except OSError:
            # A concurrent initialization may have finished the same immutable bundle.
            if not marker.is_file() or marker.read_text(encoding="utf-8") != identity:
                raise
            verify_runtime(runtime, manifest)
    return {"skill_dir": str(runtime), "cached": False, "files": manifest["file_count"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path,
                        default=Path(tempfile.gettempdir()) / "ppt-ultra-runtime")
    parser.add_argument("--verify", action="store_true", help="Recheck every cached file's SHA-256")
    args = parser.parse_args()
    try:
        result = restore(Path(__file__).resolve().parent, args.cache_dir, args.verify)
    except (OSError, ValueError, KeyError, TypeError, EOFError, tarfile.TarError) as exc:
        print(f"PPT Ultra initialization failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
