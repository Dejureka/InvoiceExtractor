"""Shared test setup.

Private samples (real invoices) are outside git; see tools/samples.py.
Mark a test with ``@pytest.mark.private_samples("unit/x.pdf", ...)``:
- locally, every listed path must be in the manifest and match its sha256,
  otherwise the test FAILS (it never silently skips);
- in CI (env CI set) with no manifest, the test is skipped with a clear reason.
CI also deselects them explicitly with ``-m "not private_samples"``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import samples  # noqa: E402


def require_samples(*rels: str) -> list[Path]:
    """Same check as the marker, for paths only known inside a test."""
    try:
        return samples.require(*rels)
    except samples.SamplesUnavailable as exc:
        if samples.in_ci() and not (samples.root() / samples.MANIFEST).is_file():
            pytest.skip(f"private samples are not available in CI: {exc}")
        pytest.fail(f"private sample check failed: {exc}", pytrace=False)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    for mark in item.iter_markers("private_samples"):
        require_samples(*mark.args)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "private_samples(*paths): needs real invoices from the private sample store "
        "(tools/samples.py); fails locally if missing, skipped in CI",
    )
