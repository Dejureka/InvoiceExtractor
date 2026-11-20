"""Run the audited real batches through the same pairing pipeline as the CLI."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from invoice_extractor.cli import collect_pdfs
from invoice_extractor.export import _lines_row, _summary_row, write_extracts
from invoice_extractor.formats.ma_ak_billing_v1 import extract_from_text
from invoice_extractor.ocr import is_ocr_backend, tesseract_available
from invoice_extractor.pairing import (
    PairRow, STATUS_INV_ONLY, auto_pair, dedupe_shared_packing_units, extract_pair_row,
)
from invoice_extractor.text_layer import extract_layout_text, text_layer_looks_unreliable
from validate_result import (
    LINE_FIELDS, SUMMARY_FIELDS, is_bl_only, markdown_table, validate,
)

DOWNLOADS = Path("/home/box/Downloads")
BATCHES = {
    "ma3": (DOWNLOADS / "MA-batch-final/MA_3rd data/3rd data", "*/*", "ma_3rd"),
    "pt4": (DOWNLOADS / "PT-batch-4th/4th data", "", "pt_4th"),
    "bhc4": (DOWNLOADS / "BHC-batch-4th/BHC_4th data", "case *", "bhc_4th"),
    "bhc5": (DOWNLOADS / "BHC-batch-5th/BHC_5th data", "case *", "bhc_5th"),
    "bhc6": (DOWNLOADS / "BHC-batch-6th/BHC_6th data", "case*/run", "bhc_6th"),
    "ebike1": (Path("/workspace/ebike_1st"), "", "ebike_1st_r2"),
    "soe2": (DOWNLOADS / "SOE-batch-2nd/extracted", "*", "soe_2nd"),
    "maak": (ROOT / "fixtures", "ma_ak_AK0007409*_layout.txt", "ma_ak_74096_shipment"),
}
BL_FIELDS = {"bl_no", "bl_packages", "bl_gross_weight_kg"}


def reviewed(batch):
    folder = ROOT / "docs/review_shots" / BATCHES[batch][2]
    rows = []
    for path in sorted(folder.rglob("*.json")):
        obj = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(obj, dict) and isinstance(obj.get("header"), dict):
            rows.append(obj)
    return rows


def extract_batch(batch, *, text_only=None):
    """Return extracts and a ledger of skipped inputs and extraction failures."""
    root, pattern, _ = BATCHES[batch]
    if not root.is_dir():
        raise FileNotFoundError(root)
    groups = sorted(root.glob(pattern)) if pattern else [root]
    if not groups:
        raise FileNotFoundError(f"{root}/{pattern}")
    skip_ocr = not tesseract_available() if text_only is None else text_only
    rows, skipped, failures = [], {}, []
    if batch == "maak":
        for fixture in groups:
            invoice = fixture.name.removeprefix("ma_ak_").removesuffix("_layout.txt")
            rows.append(extract_from_text(
                fixture.read_text(encoding="utf-8"), source_file=str(fixture.with_name(f"{invoice}.PDF")),
                text_backend="pdftotext -layout",
            ).to_dict())
        dedupe_shared_packing_units(rows)
        return rows, [], failures

    snapshots = reviewed(batch)
    ocr_sources = {
        Path(d["meta"]["source_file"]).resolve()
        for d in snapshots
        if d.get("meta", {}).get("source_file") and is_ocr_backend(d["meta"].get("text_backend"))
        and Path(d["meta"]["source_file"]).is_absolute()
    }
    ocr_soe_names = {
        Path(d["meta"]["source_file"]).name for d in snapshots
        if is_ocr_backend(d["meta"].get("text_backend"))
    } if batch == "soe2" else set()
    reviewed_invoices = {
        (Path(d["meta"]["source_file"]).parent.name, Path(d["meta"]["source_file"]).name): d
        for d in snapshots if d["header"].get("invoice_no")
    }
    ma_bills = {
        Path(d["meta"]["source_file"]).parent: Path(d["meta"]["source_file"])
        for d in snapshots if batch == "ma3" and not d["header"].get("invoice_no")
    }
    # Audit snapshots often contain OCR BL results separately. For BHC 4th,
    # several invoice snapshots are paired with a BL that has no native text.
    @lru_cache(maxsize=None)
    def requires_ocr(path):
        if not skip_ocr or not path or path.suffix.lower() in {".xls", ".xlsx", ".xlsm"}:
            return False
        if path.resolve() in ocr_sources or path.name in ocr_soe_names:
            return True
        text, _, needs_ocr = extract_layout_text(path)
        return needs_ocr or text_layer_looks_unreliable(text)

    for group in groups:
        if not group.is_dir():
            continue
        paths, errors = collect_pdfs([group])
        failures.extend(errors)
        case = []
        if batch == "soe2":
            # The SOE auditor explicitly scoped this batch to CI attachments.
            pairs = [
                PairRow(pair_id=str(i), inv_path=path, status=STATUS_INV_ONLY)
                for i, path in enumerate(paths, 1)
                if (group.name, path.name) in reviewed_invoices
            ]
        elif (ma_bill := ma_bills.get(group)) in paths:
            # MA's audited runs selected the known shipment BL explicitly,
            # including scans whose filename and native layer cannot identify it.
            pairs = [
                replace(pair, bl_path=ma_bill)
                for pair in auto_pair([path for path in paths if path != ma_bill])
                if pair.inv_path is not None
            ]
        else:
            pairs = auto_pair(paths)
        for pair in pairs:
            if pair.skipped:
                continue
            label = pair.inv_path or pair.bl_path or pair.pkl_path
            if not label or not (pair.inv_path or pair.bl_path):
                continue
            try:
                ocr_input = next((path for path in (pair.pkl_path, pair.inv_path)
                                  if requires_ocr(path)), None)
                if ocr_input:
                    skipped.setdefault(ocr_input, f"invoice or PL, affects {label.name}")
                    continue
                old = reviewed_invoices.get((group.name, label.name))
                old_bl = old["meta"].get("bl_file") if old is not None else None
                omitted_bl = pair.bl_path if requires_ocr(pair.bl_path) else None
                if omitted_bl is None and not pair.bl_path and old_bl:
                    old_path = Path(old_bl)
                    if old_path.is_file() and requires_ocr(old_path):
                        omitted_bl = old_path
                if omitted_bl:
                    skipped[omitted_bl] = "BL requires OCR, invoice kept"
                    if not pair.inv_path:
                        continue
                    pair = replace(pair, bl_path=None)
                data = extract_pair_row(pair)
                if data is None:
                    continue
                if skip_ocr and (data["meta"].get("needs_ocr")
                                 or "ocr_failed" in (data["meta"].get("text_backend") or "")):
                    skipped.setdefault(label, "invoice requires OCR")
                    continue
                for field in ("_hard", "_pair_id", "_pair_status"):
                    data.pop(field, None)
                if omitted_bl:
                    data["meta"]["regression_ocr_bl_omitted"] = True
                    if old and old["meta"].get("needs_gold"):
                        # Preserve the known audit exclusion when its only
                        # uncertainty is on the omitted OCR bill.
                        gold = set(old["meta"].get("needs_gold_fields") or ())
                        if gold and gold <= BL_FIELDS:
                            data["meta"]["regression_audit_needs_gold"] = True
                case.append(data)
            except Exception as exc:
                failures.append(f"{label}: {exc}")
        dedupe_shared_packing_units(case)
        rows.extend(case)
    return rows, [f"{path} [{reason}]" for path, reason in sorted(skipped.items())], failures


def projection(data):
    """Only values emitted in Result Summary and Lines, plus format ID."""
    hdr = data["header"]
    return {
        "format_id": data.get("meta", {}).get("format_id"),
        "header": {key: value for key, value in zip(SUMMARY_FIELDS, _summary_row(hdr)) if value is not None},
        "items": [
            {key: value for key, value in zip(LINE_FIELDS, _lines_row(item, hdr)) if value is not None}
            for item in data.get("items", [])
        ],
    }


def gold_rows(rows):
    return [d for d in rows if not is_bl_only(d) and not d["meta"].get("needs_gold")
            and not d["meta"].get("needs_ocr") and not d["meta"].get("regression_audit_needs_gold")]


def flatten(data):
    result = {"format_id": data["format_id"]}
    result.update((f"Summary.{field}", value) for field, value in data["header"].items())
    result["Lines.count"] = len(data["items"])
    for row, item in enumerate(data["items"], 1):
        result.update((f"Lines[{row}].{field}", value) for field, value in item.items())
    return result


def index(rows):
    counts = Counter()
    out = {}
    for data in rows:
        header = data["header"]
        invoice = str(header.get("invoice_no") or f"BL {header.get('bl_no')}")
        counts[invoice] += 1
        key = invoice if counts[invoice] == 1 else f"{invoice} [{counts[invoice]}]"
        out[key] = data
    return out


def diff_rows(batch, before, after):
    left, right = index(before), index(after)
    for invoice in sorted(left.keys() | right.keys()):
        if invoice not in left or invoice not in right:
            yield batch, invoice, "(row)", "present" if invoice in left else "missing", "present" if invoice in right else "missing"
            continue
        baseline, current = flatten(left[invoice]), flatten(right[invoice])
        for field in sorted(baseline.keys() | current.keys()):
            if baseline.get(field) != current.get(field):
                yield batch, invoice, field, baseline.get(field), current.get(field)


def audit_comparison(batch, rows):
    snapshots = reviewed(batch)
    by_source = {}
    by_invoice = {}
    for data in snapshots:
        source = (data.get("meta") or {}).get("source_file")
        if source:
            by_source[Path(source).name.casefold()] = data
        invoice = data["header"].get("invoice_no")
        if invoice:
            by_invoice.setdefault(str(invoice), []).append(data)

    for data in rows:
        if is_bl_only(data) or not data["header"].get("invoice_no"):
            continue
        source = Path(data["meta"].get("source_file") or "").name.casefold()
        invoice = str(data["header"].get("invoice_no"))
        matches = by_invoice.get(invoice, [])
        old = by_source.get(source)
        if old is None and len(matches) == 1:
            old = matches[0]
        if old is None:
            yield batch, invoice, "(reviewed extract)", "missing", source
            continue
        baseline, current = projection(old), projection(data)
        if data["meta"].get("regression_ocr_bl_omitted"):
            for field in BL_FIELDS:
                baseline["header"].pop(field, None)
        yield from diff_rows(batch, [baseline], [current])


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("out/regress/baseline"))
    parser.add_argument("--save-baseline", action="store_true")
    parser.add_argument("--batches", help="Comma-separated: " + ",".join(BATCHES))
    parser.add_argument("--report", type=Path, default=Path("out/regress/report.md"))
    args = parser.parse_args(argv)
    batches = args.batches.split(",") if args.batches else list(BATCHES)
    if invalid := set(batches) - BATCHES.keys():
        parser.error("Unknown batches: " + ", ".join(sorted(invalid)))
    statuses, diffs, audit_diffs, details = [], [], [], []
    failed = False
    for batch in batches:
        try:
            rows, skipped, failures = extract_batch(batch)
        except FileNotFoundError as exc:
            statuses.append((batch, 0, 0, 0, 0, 0, "missing sources"))
            details.append((batch, "missing", str(exc)))
            continue
        details.extend((batch, "OCR skip", value) for value in skipped)
        details.extend((batch, "extraction failure", value) for value in failures)
        current = args.report.parent / "current" / batch
        current.mkdir(parents=True, exist_ok=True)
        work = current / "Result.xlsx"
        extracts = current / "extracts.json"
        write_extracts(rows, work)
        write_json(extracts, rows)
        report = validate(work, extracts=extracts)
        report.write(current / "findings.md")
        snapshot = [projection(d) for d in rows]
        baseline = args.baseline / f"{batch}.json"
        batch_diff = []
        if args.save_baseline and not failures:
            write_json(baseline, snapshot)
        elif baseline.is_file():
            batch_diff = list(diff_rows(batch, json.loads(baseline.read_text(encoding="utf-8")), snapshot))
        else:
            batch_diff = [(batch, "", "(baseline)", "missing", "present")]
        diffs.extend(batch_diff)
        audit_diffs.extend(audit_comparison(batch, rows))
        hard, warn = report.counts["hard"], report.counts["warn"]
        statuses.append((batch, report.invoices_checked, hard, warn, len(batch_diff), len(skipped), len(failures)))
        print(f"{batch}: {report.invoices_checked} invoices, hard={hard}, warn={warn}, "
              f"diff={len(batch_diff)}, OCR skips={len(skipped)}, failures={len(failures)}", flush=True)
        failed |= bool(failures or batch_diff or hard)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    cols = ("Batch", "Invoice", "Field", "Baseline", "Current")
    args.report.write_text(
        "# Batch regression\n\n"
        + markdown_table(("Batch", "Invoices", "Hard", "Warn", "Diffs", "OCR skips", "Failures"), statuses)
        + "\n## Baseline differences\n\n" + markdown_table(cols, diffs)
        + "\n## Auditor snapshot differences\n\n" + markdown_table(cols, audit_diffs)
        + "\n## Input exclusions and failures\n\n" + markdown_table(("Batch", "Reason", "Input"), details),
        encoding="utf-8",
    )
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
