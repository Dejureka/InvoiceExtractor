# Consolidation U1 — private sample store + tests that fail instead of skip

Branch `consolidate/u1-private-samples` (base main `e18dfb0`). Test/tool-only: **no `src/` change, portable not affected.**

## What changed
- `tools/samples.py`: one fixed private store for real invoices, outside git (`$INVOICE_SAMPLES`, default `/workspace/invoice-samples`), with `manifest.csv` = batch, file, sha256, bytes (574 files at commit time; `python3 tools/samples.py --check` → 0 problems).
- `tools/regression_batches.py`: the 7 real batches are read from `regression/<batch>/` in the store (copied 1:1 from `/home/box/Downloads/...` and `/workspace/ebike_1st`). Reviewed-snapshot paths in `docs/review_shots/` are rebased onto the store (`LEGACY_ROOTS`). Manifest check before every batch. **Missing sources now make the run exit 1** (before: printed "missing sources" and exited 0). Baseline default moved from `out/regress/baseline` (wiped on box reset) to the store.
- `tests/conftest.py`: marker `@pytest.mark.private_samples(paths…)` + `require_samples()`. Locally: a missing file or sha mismatch **fails**. In CI (`CI` set, no manifest): skipped with an explicit reason; CI also deselects with `-m "not private_samples"` (U2).
- 13 test files: hard-coded `/home/box/...`, `/workspace/...` paths and "skip if missing" replaced by the marker. Tesseract-unavailable skips kept (environment, not data). No assertion changed.
- `tests/test_pt_dremel.py` read text files from `out/pt_dremel/txt`, which had already been wiped → 3 tests were silently skipped. Regenerated with `pdftotext -layout` from the same 16 PDFs into `unit/pt_dremel_txt/`; the 3 tests run and pass again.

## Evidence
| Check | Result |
|---|---|
| Regression 8 batches vs `regress-baseline` | diff 0 on all 8; hard 0 |
| Full `extracts.json` (every field, notes, flags) main vs U1, paths normalised | identical on all 8 batches |
| pytest (box, GUI tests deselected — no tkinter here) | main: 513 pass / 20 skip → U1: 516 pass / 17 skip (3 pt_dremel un-skipped; remaining 17 skips are all "tesseract unavailable") |
| `INVOICE_SAMPLES=/tmp/none` locally | 23 failed + 36 errors (all private-sample tests) — nothing silently skipped |
| same with `CI=true` | 474 pass / 59 skipped |
| `CI=true -m "not private_samples"` | 472 pass / 73 deselected |
| one manifest file deleted in a copy of the store | `private sample check failed: manifest lists regression/pt4/… but it is missing` |
| `regression_batches.py` with no store | `pt4: MISSING SOURCES`, exit 1 |

Private paths (not in git): `/workspace/invoice-samples/README.md`, `manifest.csv`, regression report `/workspace/invoice-samples/review/consolidation_u1/regress_report.md`.
