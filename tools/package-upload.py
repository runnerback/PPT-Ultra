#!/usr/bin/env python3
"""Build a lossless, bounded skill upload and optional plaintext source review volumes."""
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
SKILL = ROOT / 'skills' / 'ppt-ultra'
MAX_FILES = 500
MAX_BYTES = 100_000_000
DEFAULT_PART_BYTES = 8_000_000
# Explicit inputs include new security files before the maintainer commits them.
# All other files must be tracked; untracked private/local files are never swept in.
REQUIRED_RUNTIME_FILES = ('SKILL.md', 'requirements.txt', 'requirements.lock', 'LICENSE', 'LICENSE-AGPL-3.0')
SOURCE_EXTENSIONS = {'.py', '.mjs', '.js', '.jsx', '.ts', '.json', '.sh', '.ps1', '.html', '.css', '.xml', '.md', '.txt', '.lock', '.template', '.example'}


def tracked_files() -> list[Path]:
    result = subprocess.check_output(['git', 'ls-files', '-z', '--', 'skills/ppt-ultra'], cwd=ROOT)
    paths = {ROOT / p.decode('utf-8') for p in result.split(b'\0') if p}
    paths.update(SKILL / name for name in REQUIRED_RUNTIME_FILES)
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Expected a regular distribution file: {path}')
        relative = path.relative_to(SKILL)
        if any(part in {'node_modules', '__pycache__', 'output', '.env', '.npmrc'} for part in relative.parts) or path.suffix == '.pyc':
            raise ValueError(f'Remove generated/private files from the Git index: {relative}')
    return sorted(paths)


def safety_section(source: str) -> str:
    start = source.index('## 安全边界（P1–P4）')
    end = source.index('## Mandatory Load Order', start)
    return source[start:end]


def upload_entrypoint(source: str) -> str:
    if not source.startswith('---\n'):
        raise ValueError('SKILL.md must start with YAML frontmatter')
    end = source.index('\n---\n', 4) + len('\n---\n')
    return source[:end] + '''
# PPT Ultra — compact upload distribution

All engines, instructions and assets are retained. Markdown references are
visible; the complete original skill is in independently readable `runtime-*.tar.gz`
volumes. `runtime-manifest.json` identifies the source revision and every file/hash.
The full source repository is https://github.com/runnerback/PPT-Ultra .

''' + safety_section(source) + '''## Initialize before following any workflow

1. Retain the host-provided absolute directory containing this file as `UPLOAD_DIR`.
   Run `python3 "${UPLOAD_DIR}/bootstrap.py"` with that absolute path (use `python`
   if that is the host's Python command). Initialization uses only the standard
   library; it makes no network requests and installs no dependencies.
2. Parse the JSON result. Set `SKILL_DIR` to its absolute `skill_dir`, not
   `UPLOAD_DIR`. Read `${SKILL_DIR}/SKILL.md`, the original entrypoint, and follow
   its safety boundaries, routing and integrity gates. Use the returned directory
   for every subsequent reference and command, including host brief `skill_dir`.
3. Write decks to the caller's workspace. Install only the hash-locked dependencies
   from the restored directory; keep credentials in host-managed configuration.

The verified runtime is cached outside the upload directory. Use `--cache-dir
"<absolute writable directory>"` if the default temporary directory is unsuitable,
and `--verify` to recheck cached files. Initialization failure stops the workflow;
do not use partial resources or bypass integrity gates. The host must allow Python,
archive resources and a writable cache. Restored runtime file counts are unchanged.
'''


def partitions(files: list[Path], limit: int, file_limit: int | None = None):
    """Bound uncompressed content plus tar/ZIP overhead, not merely compressed size."""
    batch, size = [], 0
    for path in files:
        cost = ((path.stat().st_size + 511) // 512) * 512 + 2048
        if cost + 16384 > limit:
            raise ValueError(f'Single file exceeds review-part limit: {path.relative_to(SKILL)}; use --max-part-bytes')
        if batch and (size + cost + 16384 > limit or (file_limit and len(batch) >= file_limit)):
            yield batch
            batch, size = [], 0
        batch.append(path)
        size += cost
    if batch:
        yield batch


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False, suffix='.tmp') as tmp:
        staged = Path(tmp.name)
    try:
        shutil.copyfile(source, staged)
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)


def build(output: Path, max_part_bytes: int = DEFAULT_PART_BYTES, audit_dir: Path | None = None) -> dict:
    files = tracked_files()
    source = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
    version = re.search(r'^  version: "([^"\n]+)"$', source, re.MULTILINE)
    if not version:
        raise ValueError('Missing skill version')
    exposed = [p for p in files if p.suffix == '.md' or p.name.startswith('LICENSE') or p.parent == SKILL]
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--', 'skills/ppt-ultra', 'tools'], cwd=ROOT))
    audit_parts = []
    with tempfile.TemporaryDirectory(prefix='ppt-ultra-package-') as work:
        staging = Path(work)
        entries, archives = {}, []
        for index, batch in enumerate(partitions(files, max_part_bytes), 1):
            archive = staging / f'runtime-{index:03d}.tar.gz'
            with archive.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode='w', format=tarfile.PAX_FORMAT) as tar:
                    for path in batch:
                        name = path.relative_to(SKILL).as_posix()
                        data = path.read_bytes()
                        mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                        info = tarfile.TarInfo(name)
                        info.size, info.mode = len(data), mode
                        tar.addfile(info, io.BytesIO(data))
                        entries[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data), 'mode': mode, 'archive': archive.name}
            if archive.stat().st_size > max_part_bytes:
                raise ValueError(f'Archive exceeds review-part limit: {archive.name}')
            archives.append({'name': archive.name, 'sha256': sha256(archive), 'bytes': archive.stat().st_size, 'file_count': len(batch)})
        manifest = {'format': 2, 'version': version[1], 'source': {'repository': 'https://github.com/runnerback/PPT-Ultra', 'revision': revision, 'dirty': dirty},
                    'archives': archives, 'max_part_bytes': max_part_bytes, 'file_count': len(entries),
                    'runtime_bytes': sum(e['size'] for e in entries.values()), 'files': entries}
        candidate = staging / 'upload.zip'
        with zipfile.ZipFile(candidate, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for path in exposed:
                name = path.relative_to(SKILL).as_posix()
                data = upload_entrypoint(source).encode('utf-8') if name == 'SKILL.md' else path.read_bytes()
                z.writestr(name, data)
            z.writestr('bootstrap.py', (ROOT / 'tools/upload_bootstrap.py').read_bytes())
            z.writestr('runtime-manifest.json', json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode('utf-8'))
            for archive in archives:
                z.write(staging / archive['name'], archive['name'], compress_type=zipfile.ZIP_STORED)
        with zipfile.ZipFile(candidate) as z:
            upload_count = len(z.infolist())
            upload_bytes = sum(info.file_size for info in z.infolist())
            if upload_count > MAX_FILES or max(upload_bytes, candidate.stat().st_size) > MAX_BYTES:
                raise ValueError(f'Upload limits exceeded: {upload_count} files, {upload_bytes} bytes')
            if any(info.file_size > max_part_bytes for info in z.infolist()):
                raise ValueError('A visible file exceeds --max-part-bytes')
            if z.testzip():
                raise ValueError('ZIP CRC verification failed')
        atomic_copy(candidate, output)
        if audit_dir:
            # These volumes expose code/configuration/docs directly, without nested archives.
            audit_files = [p for p in files if p.suffix in SOURCE_EXTENSIONS or p.name.startswith('LICENSE') or p.name == '.gitignore']
            for index, batch in enumerate(partitions(audit_files, max_part_bytes, file_limit=350), 1):
                name = f'ppt-ultra-{version[1]}-source-{index:02d}.zip'
                audit = staging / name
                with zipfile.ZipFile(audit, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                    for path in batch:
                        z.write(path, path.relative_to(SKILL).as_posix())
                if audit.stat().st_size > max_part_bytes:
                    raise ValueError(f'Source volume exceeds limit: {name}')
                atomic_copy(audit, audit_dir / name)
                audit_parts.append({'name': name, 'sha256': sha256(audit), 'files': [p.relative_to(SKILL).as_posix() for p in batch]})
            report = {'version': version[1], 'source': manifest['source'], 'max_part_bytes': max_part_bytes,
                      'scope': 'Plaintext code, configuration, lockfiles, documentation and licenses. Binary/SVG assets are preserved in the runtime volumes and full directory ZIP.',
                      'volumes': audit_parts, 'files': {p.relative_to(SKILL).as_posix(): entries[p.relative_to(SKILL).as_posix()] for p in audit_files}}
            audit_dir.mkdir(parents=True, exist_ok=True)
            (audit_dir / f'ppt-ultra-{version[1]}-source-manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    digest = sha256(output)
    output.with_suffix(output.suffix + '.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    return {'zip': str(output), 'upload_files': upload_count, 'upload_bytes': upload_bytes, 'zip_bytes': output.stat().st_size,
            'runtime_files': len(entries), 'runtime_bytes': manifest['runtime_bytes'], 'runtime_volumes': len(archives),
            'largest_runtime_volume': max(a['bytes'] for a in archives), 'audit_volumes': len(audit_parts), 'sha256': digest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/ppt-ultra-upload.zip')
    parser.add_argument('--max-part-bytes', type=int, default=DEFAULT_PART_BYTES, help='Maximum bytes per runtime/source volume (default 8,000,000)')
    parser.add_argument('--audit-dir', type=Path, help='Also produce independently readable source ZIP volumes and their manifest')
    args = parser.parse_args()
    if args.max_part_bytes < 16384:
        parser.error('--max-part-bytes must be at least 16384')
    print(json.dumps(build(args.output.resolve(), args.max_part_bytes, args.audit_dir.resolve() if args.audit_dir else None), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
