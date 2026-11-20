"""Re-extract the reproducible text-layer scope of the Auditor-passed batches."""
from collections import Counter
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from regression_batches import BATCHES, diff_rows, extract_batch, gold_rows, projection
from validate_result import validate

GOLD = Path(__file__).with_name("gold")

# Keyed by batch, invoice, rule and field, with exact maximum occurrence counts.
# These remain hard in production and are visible in the batch findings.
HARD_ALLOWLIST = {
    **{
        ("maak", "AK00074096", "H_LINE_MATH", "amount", line):
            (1, f"Printed position {line * 10} shows whole-TWD unit price and a line amount differing by 1 TWD from the product.")
        for line in (11, 12, 14)
    },
}


@pytest.fixture(scope="module", params=BATCHES)
def batch_run(request):
    batch = request.param
    try:
        rows, _, failures = extract_batch(batch, text_only=True)
    except FileNotFoundError as exc:
        pytest.skip(f"Batch source unavailable: {exc}")
    assert not failures, failures
    return batch, gold_rows(rows)


def test_result_fields_match_frozen_gold(batch_run):
    batch, rows = batch_run
    paths = sorted(GOLD.glob(f"{batch}.*.json")) or [GOLD / f"{batch}.json"]
    expected = [row for path in paths for row in json.loads(path.read_text(encoding="utf-8"))]
    diffs = list(diff_rows(batch, expected, [projection(row) for row in rows]))
    assert not diffs, f"{len(diffs)} field diffs. First 20: {diffs[:20]}"


def test_gold_hard_checks(batch_run):
    batch, rows = batch_run
    observed = Counter(
        (batch, f.invoice_no, f.rule_id, f.field, f.row)
        for f in validate(extracts=rows).findings if f.status == "hard"
    )
    allowed = Counter({key: count for key, (count, _) in HARD_ALLOWLIST.items() if key[0] == batch})
    assert observed == allowed, f"Unexpected hard findings: {observed - allowed}. Stale exceptions: {allowed - observed}."
