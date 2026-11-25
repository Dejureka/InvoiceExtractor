"""Private sample store: real invoices that must never be committed.

The repo is public, so real PDFs, full-text fixtures and gold files with prices
live outside git, in one fixed folder on the box:

    $INVOICE_SAMPLES   (default: /workspace/invoice-samples)
    ├── manifest.csv   batch,file,sha256,bytes  (file is relative to the root)
    ├── regression/<batch>/...   inputs of tools/regression_batches.py
    ├── unit/...                 inputs of individual tests
    ├── gold/<name>.json         frozen Result values for formats without repo gold
    └── regress-baseline/<batch>.json

Rules:
- The manifest is the contract. A file it lists that is missing or has a
  different sha256 is an error (tests FAIL, the regression FAILS).
- With no manifest at all, tests that need samples fail locally and skip only
  in CI (environment variable CI set), where private samples never exist.

Run ``python tools/samples.py --check`` to verify, ``--write`` to rebuild the
manifest after adding files on purpose.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DEFAULT_ROOT = Path("/workspace/invoice-samples")
MANIFEST = "manifest.csv"
TRACKED_DIRS = ("regression", "unit", "gold", "review")


class SamplesUnavailable(RuntimeError):
    """The private sample store or one of its manifest files is unusable."""


@dataclass(frozen=True)
class Entry:
    batch: str
    file: str
    sha256: str
    bytes: int


def root() -> Path:
    return Path(os.environ.get("INVOICE_SAMPLES") or DEFAULT_ROOT)


def in_ci() -> bool:
    return bool(os.environ.get("CI"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@lru_cache(maxsize=None)
def _manifest(base: str) -> dict[str, Entry]:
    path = Path(base) / MANIFEST
    if not path.is_file():
        raise SamplesUnavailable(f"no sample manifest at {path}")
    with path.open(encoding="utf-8", newline="") as fh:
        return {
            row["file"]: Entry(row["batch"], row["file"], row["sha256"], int(row["bytes"]))
            for row in csv.DictReader(fh)
        }


def manifest() -> dict[str, Entry]:
    return _manifest(str(root()))


@lru_cache(maxsize=None)
def _verified(base: str, rel: str) -> None:
    entry = _manifest(base).get(rel)
    if entry is None:
        raise SamplesUnavailable(f"{rel} is not listed in {Path(base) / MANIFEST}")
    path = Path(base) / rel
    if not path.is_file():
        raise SamplesUnavailable(f"manifest lists {rel} but it is missing under {base}")
    if path.stat().st_size != entry.bytes or sha256(path) != entry.sha256:
        raise SamplesUnavailable(f"{rel} changed (sha256 differs from the manifest)")


def path(rel: str) -> Path:
    """Absolute path of a sample (no checks; use :func:`require` before reading)."""
    return root() / rel


def require(*rels: str) -> list[Path]:
    """Verify files or folders against the manifest and return their paths.

    A folder passes when the manifest lists at least one file under it and all of
    them verify.
    """
    base = str(root())
    out = []
    for rel in rels:
        rel = rel.strip("/")
        entries = _manifest(base)
        if rel in entries:
            _verified(base, rel)
        else:
            under = [f for f in entries if f.startswith(rel + "/")]
            if not under:
                raise SamplesUnavailable(f"{rel} is not listed in {Path(base) / MANIFEST}")
            for f in under:
                _verified(base, f)
        out.append(Path(base) / rel)
    return out


def check_batch(batch: str) -> list[str]:
    """Problems for every manifest file of one batch (empty list = all good)."""
    base = str(root())
    problems = []
    entries = [e for e in _manifest(base).values() if e.batch == batch]
    if not entries:
        return [f"manifest has no files for batch {batch!r}"]
    for e in entries:
        try:
            _verified(base, e.file)
        except SamplesUnavailable as exc:
            problems.append(str(exc))
    return problems


def _batch_of(rel: Path) -> str:
    parts = rel.parts
    if parts[0] == "regression" and len(parts) > 2:
        return parts[1]
    if parts[0] in ("unit", "review") and len(parts) > 2:
        return f"{parts[0]}:{parts[1]}"
    return parts[0]


def write_manifest() -> int:
    base = root()
    rows = []
    for top in TRACKED_DIRS:
        for p in sorted((base / top).rglob("*")):
            if p.is_file():
                rel = p.relative_to(base)
                rows.append((_batch_of(rel), rel.as_posix(), sha256(p), p.stat().st_size))
    with (base / MANIFEST).open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(("batch", "file", "sha256", "bytes"))
        w.writerows(rows)
    _manifest.cache_clear()
    _verified.cache_clear()
    return len(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="rebuild manifest.csv from the files on disk")
    ap.add_argument("--check", action="store_true", help="verify every manifest file")
    args = ap.parse_args(argv)
    if args.write:
        print(f"wrote {write_manifest()} entries to {root() / MANIFEST}")
    if args.check or not args.write:
        bad = []
        for e in manifest().values():
            try:
                _verified(str(root()), e.file)
            except SamplesUnavailable as exc:
                bad.append(str(exc))
        print(f"{len(manifest())} files, {len(bad)} problems")
        for b in bad:
            print("  " + b)
        return int(bool(bad))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
