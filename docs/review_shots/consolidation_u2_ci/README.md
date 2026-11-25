# Consolidation U2 — CI pytest job

Branch `consolidate/u2-ci-pytest` (on top of U1). Adds `.github/workflows/tests.yml` only.

- Runs on every push / PR: ubuntu, Python 3.12, poppler + xvfb, `pip install -e ".[gui,dev]"`, `pytest -m "not private_samples"` with `CI=true` and no private store.
- Tests that need the private store carry `@pytest.mark.private_samples` and are deselected in CI; locally they **fail** (not skip) when the manifest says a file should exist and it doesn't (U1).
- `pyproject.toml` untouched (marker registered in `tests/conftest.py`) so the portable-build workflow is not triggered.

Evidence: GitHub Actions run 45579579465 on `ae6a621` — success, **483 passed, 1 skipped (tesseract), 61 deselected** in 4.8 s.
