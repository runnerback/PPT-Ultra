#!/usr/bin/env python3
"""Build a lossless skill upload ZIP within the 500-file / 100 MB limits."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "ppt-ultra"
MAX_FILES = 500
MAX_BYTES = 100_000_000  # Also enforce the stricter decimal interpretation of MB.


def tracked_files() -> list[Path]:
    result = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "skills/ppt-ultra"], cwd=ROOT
    )
    paths = [ROOT / p.decode("utf-8") for p in result.split(b"\0") if p]
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Expected a regular tracked file: {path}")
        relative = path.relative_to(SKILL)
        if any(part in {"node_modules", "__pycache__", "output", ".env", ".npmrc"}
               for part in relative.parts) or path.suffix == ".pyc":
            raise ValueError(f"Remove generated/private files from the Git index: {relative}")
    return sorted(paths)


def upload_entrypoint(source: str) -> str:
    if not source.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = source.index("\n---\n", 4) + len("\n---\n")
    return source[:end] + '''
# PPT Ultra — compact upload distribution

This package retains every engine, template, icon, sound, font and instruction
from PPT Ultra. Markdown references remain visible for discovery; the complete
original skill is stored losslessly in `runtime.tar.gz` to fit file-count limits.

## Initialize before following any workflow

1. Retain the host-provided absolute directory containing **this** file as
   `UPLOAD_DIR`. Run `python3 "${UPLOAD_DIR}/bootstrap.py"` with that absolute
   path. If the host exposes Python as `python`, use it instead. This step uses
   only Python's standard library, makes no network requests, installs no
   dependencies, and does not write to the uploaded package.
2. Parse the JSON result. Set `SKILL_DIR` to its absolute `skill_dir` value,
   **not** `UPLOAD_DIR`. Read `${SKILL_DIR}/SKILL.md`, the unmodified original
   entrypoint, and follow its routing, selected workflow and integrity gates.
   Treat this returned path as the host-resolved skill directory for all
   subsequent commands and reference reads, including host brief `skill_dir`.
3. Write decks to the caller's workspace as the original skill requires.
   Configure optional `.env` and install route dependencies using the restored
   `SKILL_DIR`; unpacking itself does not install Python or Node dependencies.

The runtime is cached outside the upload directory and reused on later calls.
If the default temporary directory is not writable, pass
`--cache-dir "<absolute writable cache directory>"`. If initialization fails,
report its error and stop; do not run partial resources or bypass integrity gates.
The host must allow Python execution, a writable cache and bundled `.tar.gz`
resources. This format limits uploaded files, not the restored runtime's files.
'''


def build(output: Path) -> dict:
    files = tracked_files()
    source = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    version = re.search(r'^  version: "([^"\n]+)"$', source, re.MULTILINE)
    if not version:
        raise ValueError("Missing skill version")
    exposed = [p for p in files if p.suffix == ".md" or p.name == "LICENSE" or p.parent == SKILL]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ppt-ultra-package-") as work:
        archive = Path(work) / "runtime.tar.gz"
        entries = {}
        with archive.open("wb") as raw:
            with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                    for path in files:
                        name = path.relative_to(SKILL).as_posix()
                        data = path.read_bytes()
                        mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                        info = tarfile.TarInfo(name)
                        info.size, info.mode = len(data), mode
                        tar.addfile(info, io.BytesIO(data))
                        entries[name] = {"sha256": hashlib.sha256(data).hexdigest(),
                                         "size": len(data), "mode": mode}
        archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
        manifest = {"format": 1, "version": version[1], "archive_sha256": archive_hash,
                    "file_count": len(entries), "runtime_bytes": sum(e["size"] for e in entries.values()),
                    "files": entries}
        candidate = Path(work) / "upload.zip"
        with zipfile.ZipFile(candidate, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for path in exposed:
                name = path.relative_to(SKILL).as_posix()
                data = upload_entrypoint(source).encode("utf-8") if name == "SKILL.md" else path.read_bytes()
                z.writestr(name, data)
            z.writestr("bootstrap.py", (ROOT / "tools" / "upload_bootstrap.py").read_bytes())
            z.writestr("runtime-manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8"))
            z.write(archive, "runtime.tar.gz", compress_type=zipfile.ZIP_STORED)
        with zipfile.ZipFile(candidate) as z:
            upload_count = len(z.infolist())  # No directory entries: even entry-counting hosts fit.
            upload_bytes = sum(info.file_size for info in z.infolist())
            if upload_count > MAX_FILES or max(upload_bytes, candidate.stat().st_size) > MAX_BYTES:
                raise ValueError(f"Upload limits exceeded: {upload_count} files, {upload_bytes} bytes")
            if z.testzip():
                raise ValueError("ZIP CRC verification failed")
        # Copy only a validated build; a failed build leaves the previous ZIP intact.
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False, suffix=".tmp") as tmp:
            staged = Path(tmp.name)
        try:
            shutil.copyfile(candidate, staged)
            staged.replace(output)
        finally:
            staged.unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    return {"zip": str(output), "upload_files": upload_count, "upload_bytes": upload_bytes,
            "zip_bytes": output.stat().st_size, "runtime_files": len(entries),
            "runtime_bytes": manifest["runtime_bytes"], "sha256": digest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "ppt-ultra-upload.zip")
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
