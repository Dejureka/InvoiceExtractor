"""CLI: invoice-extract / python -m invoice_extractor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from invoice_extractor import __version__
from invoice_extractor.checker import hard_check
from invoice_extractor.db import connect, record_run, seed_builtin_formats
from invoice_extractor.export import (
    default_result_path,
    is_json_out,
    write_extract,
    write_extracts,
)
from invoice_extractor.gold_stub import (
    load_gold,
    offline_compare,
    write_needs_gold_placeholder,
)
from invoice_extractor.rules_engine import extract_invoice, file_sha256
from invoice_extractor.bl_rules_engine import extract_bl
from invoice_extractor.checker_bl import hard_check_bl
from invoice_extractor.export import write_bl_extracts


_INPUT_GLOBS = (
    "*.pdf",
    "*.PDF",
    "*.Pdf",
    "*.xlsx",
    "*.XLSX",
    "*.xlsm",
    "*.XLSM",
    "*.xls",
    "*.XLS",
)
_INPUT_SUFFIXES = frozenset({".pdf", ".xlsx", ".xlsm", ".xls"})


def collect_pdfs(paths: list[str | Path]) -> tuple[list[Path], list[str]]:
    """Expand files and directories into a de-duplicated PDF/Excel list.

    Accepts ``.pdf``, ``.xlsx``, ``.xlsm``, ``.xls``. Skips tool outputs
    (``InvoiceExtract_Result.xlsx``, templates) and anything under ``ocr_out/``.

    Returns (files, errors) where errors are human-readable path problems.
    """
    from invoice_extractor.excel_text import should_skip_input

    found: list[Path] = []
    errors: list[str] = []
    seen: set[str] = set()

    def _add(m: Path) -> None:
        if should_skip_input(m):
            return
        if m.suffix.lower() not in _INPUT_SUFFIXES:
            return
        key = str(m.resolve()) if m.exists() else str(m)
        if key not in seen:
            seen.add(key)
            found.append(m)

    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            matches: set[Path] = set()
            for pat in _INPUT_GLOBS:
                matches.update(p.glob(pat))
            usable = sorted(m for m in matches if not should_skip_input(m))
            if not usable:
                errors.append(f"No PDF/Excel inputs in directory: {p}")
                continue
            for m in usable:
                _add(m)
        elif p.is_file():
            if should_skip_input(p):
                errors.append(f"Skipped tool output/template: {p}")
                continue
            if p.suffix.lower() not in _INPUT_SUFFIXES:
                errors.append(f"Not a PDF/Excel input: {p}")
                continue
            _add(p)
        else:
            errors.append(f"Path not found: {p}")
    return found, errors


def _out_path_for(pdf: Path, out: str | None, *, multi: bool = False) -> Path:
    """Resolve output path.

    - Explicit ``--out`` wins.
    - Otherwise always ``InvoiceExtract_Result.xlsx`` at the tool outermost root
      (single or multi). ``pdf`` / ``multi`` kept for call-site compatibility.
    """
    if out:
        return Path(out)
    return default_result_path()


def _prepare_extract(pdf: Path, format_id: str | None) -> dict:
    result = extract_invoice(pdf, format_id=format_id)
    data = result.to_dict()
    hard = hard_check(data)
    data["meta"]["checker_verdict"] = hard["verdict"]
    if hard["verdict"] == "pass" and data["meta"].get("confidence") == "rules":
        data["meta"]["confidence"] = "high"
    elif hard["verdict"] == "conflict":
        data["meta"]["confidence"] = "conflict"
    data["meta"]["checker_issues"] = hard.get("issues")
    data["meta"]["checker_details"] = hard.get("details")
    from invoice_extractor.text_layer import backend_warning

    warn = backend_warning(data["meta"].get("text_backend"))
    if warn:
        data["meta"]["text_backend_warning"] = warn
    data["_hard"] = hard
    return data


def cmd_init_db(args: argparse.Namespace) -> int:
    path = seed_builtin_formats(args.db)
    print(f"DB ready: {path}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    raw_paths: list[str] = []
    if getattr(args, "pdfs", None):
        raw_paths.extend(args.pdfs)
    if getattr(args, "pdf", None):
        # backward: single positional still present in some call sites
        if args.pdf not in raw_paths:
            raw_paths.insert(0, args.pdf)

    pdfs, path_errors = collect_pdfs(raw_paths)
    for err in path_errors:
        print(err, file=sys.stderr)
    if not pdfs:
        print("No PDF/Excel inputs to extract.", file=sys.stderr)
        return 2

    multi = len(pdfs) > 1
    # Gold compare only supported for single PDF
    if args.gold and multi:
        print("--gold requires a single PDF", file=sys.stderr)
        return 2

    if args.gold:
        pdf = pdfs[0]
        data = _prepare_extract(pdf, args.format)
        hard = data.pop("_hard")
        warn = data["meta"].get("text_backend_warning")
        if warn:
            print(f"WARNING: {warn}", file=sys.stderr)
        cmp = offline_compare(data, args.gold)
        data["meta"]["gold_compare"] = cmp
        print(json.dumps(cmp, ensure_ascii=False, indent=2))
        if args.out:
            write_extract(data, Path(args.out))
        return 0 if cmp["verdict"] == "pass" and not cmp.get("diffs") else 1

    from invoice_extractor.pairing import (
        STATUS_BL_ONLY,
        STATUS_PKL_ONLY,
        auto_pair,
        extract_pair_row,
    )

    successes: list[dict] = []
    failures: list[dict] = []
    # BL / arrival PDFs are paired into INV rows (or become 僅 提單 Summary rows).
    # Pure BL batch still works via --doc-type bl (dedicated BL sheet).
    pairs = auto_pair(pdfs)
    print(f"Paired {len(pairs)} unit(s) from {len(pdfs)} PDF(s)", file=sys.stderr)

    for row in pairs:
        # Skip PKL-only; BL-only is kept (Summary BL columns).
        if row.skipped or row.status == STATUS_PKL_ONLY or (
            row.pkl_path and not row.inv_path and not row.bl_path
        ):
            print(
                f"SKIP {row.pair_id}: {row.status} "
                f"inv={row.display_inv} pkl={row.display_pkl} bl={row.display_bl}",
                file=sys.stderr,
            )
            continue
        label = row.inv_path or row.bl_path or row.pkl_path
        try:
            data = extract_pair_row(row, format_id=args.format)
            if data is None:
                print(f"SKIP {row.pair_id}: empty", file=sys.stderr)
                continue
            hard = data.pop("_hard")
            data.pop("_pair_status", None)
            data.pop("_pair_id", None)
            warn = data["meta"].get("text_backend_warning")
            if warn:
                print(f"WARNING: {Path(label).name}: {warn}", file=sys.stderr)
            successes.append(data)
            h = data.get("header") or {}
            print(
                f"OK {row.pair_id} {Path(label).name}: "
                f"format={data['meta'].get('format_id')} "
                f"pair={data['meta'].get('pair_status')} "
                f"invoice_no={h.get('invoice_no')} amount={h.get('amount')} "
                f"pkg={h.get('total_pkg')} gw={h.get('gross_weight_kg')} "
                f"bl={h.get('bl_no')} bl_pkg={h.get('bl_packages')} "
                f"bl_gw={h.get('bl_gross_weight_kg')} "
                f"items={len(data.get('items') or [])} verdict={hard['verdict']} "
                f"backend={data['meta'].get('text_backend')}"
            )
            if args.db or Path(args.db_path).is_file():
                try:
                    conn = connect(args.db_path)
                    record_run(
                        conn,
                        source_hash=file_sha256(Path(label)),
                        source_file=str(label),
                        format_id=None,
                        rules_out=data,
                        verdict=hard["verdict"],
                        confidence=data["meta"].get("confidence") or "rules",
                        needs_human=hard["verdict"] != "pass",
                        gold_json=None,
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"(run log skipped: {e})", file=sys.stderr)
        except Exception as e:
            failures.append(
                {
                    "source_file": str(label),
                    "error": str(e),
                    "meta": {"source_file": str(label)},
                }
            )
            print(f"FAIL {label}: {e}", file=sys.stderr)

    if not successes and failures:
        print(f"All {len(failures)} file(s) failed; no workbook written.", file=sys.stderr)
        return 1

    # Default Excel: always InvoiceExtract_Result.xlsx at tool root (unless --out)
    if args.out:
        out = Path(args.out)
    else:
        out = default_result_path()

    if is_json_out(out):
        if len(successes) == 1:
            written = write_extract(successes[0], out)
        else:
            written = write_extracts(successes, out, failures=failures)
        print(f"Wrote {written}")
    else:
        written = write_extracts(successes, out, failures=failures)
        print(f"Wrote {written} ({len(successes)} invoice(s), {len(failures)} failed)")

    for data in successes:
        if data["meta"].get("needs_gold") or data["meta"].get("checker_verdict") == "needs_gold":
            if not multi and not is_json_out(Path(written) if isinstance(written, Path) else out):
                stub = Path(written).with_suffix(".needs_gold.json")
                write_needs_gold_placeholder(stub, data)
                print(f"Gold stub: {stub}")

    if failures:
        print(f"Failed files ({len(failures)}):", file=sys.stderr)
        for f in failures:
            print(f"  - {f.get('source_file')}: {f.get('error')}", file=sys.stderr)
        return 1
    return 0



def _prepare_bl_extract(pdf: Path, format_id: str | None) -> dict:
    result = extract_bl(pdf, format_id=format_id)
    data = result.to_dict()
    hard = hard_check_bl(data)
    data["meta"]["checker_verdict"] = hard["verdict"]
    if hard["verdict"] == "pass" and data["meta"].get("confidence") == "rules":
        data["meta"]["confidence"] = "high"
    elif hard["verdict"] == "conflict":
        data["meta"]["confidence"] = "conflict"
    data["meta"]["checker_issues"] = hard.get("issues")
    data["meta"]["checker_details"] = hard.get("details")
    from invoice_extractor.text_layer import backend_warning

    warn = backend_warning(data["meta"].get("text_backend"))
    if warn:
        data["meta"]["text_backend_warning"] = warn
    data["_hard"] = hard
    return data


def cmd_extract_bl(args: argparse.Namespace) -> int:
    """Extract BL / arrival-notice / HBL PDFs → BL sheet or JSON."""
    raw_paths: list[str] = list(getattr(args, "pdfs", None) or [])
    if getattr(args, "pdf", None) and args.pdf not in raw_paths:
        raw_paths.insert(0, args.pdf)

    pdfs, path_errors = collect_pdfs(raw_paths)
    for err in path_errors:
        print(err, file=sys.stderr)
    if not pdfs:
        print("No PDF/Excel inputs to extract.", file=sys.stderr)
        return 2

    successes: list[dict] = []
    failures: list[dict] = []
    for pdf in pdfs:
        try:
            data = _prepare_bl_extract(pdf, args.format)
            hard = data.pop("_hard")
            warn = data["meta"].get("text_backend_warning")
            if warn:
                print(f"WARNING: {pdf.name}: {warn}", file=sys.stderr)
            successes.append(data)
            h = data.get("header") or {}
            print(
                f"OK {pdf.name}: format={data['meta'].get('format_id')} "
                f"bl_no={h.get('bl_no') or h.get('hbl_no')} "
                f"vessel={h.get('vessel')} voy={h.get('voyage')} "
                f"eta={h.get('eta')} pkg={h.get('packages')} "
                f"gw={h.get('gross_weight_kg')} "
                f"inv_refs={h.get('invoice_refs')} verdict={hard['verdict']}"
            )
        except Exception as e:
            failures.append(
                {
                    "source_file": str(pdf),
                    "error": str(e),
                    "meta": {"source_file": str(pdf)},
                }
            )
            print(f"FAIL {pdf}: {e}", file=sys.stderr)

    if not successes and failures:
        print(f"All {len(failures)} file(s) failed; no workbook written.", file=sys.stderr)
        return 1

    if args.out:
        out = Path(args.out)
    else:
        out = default_result_path().with_name("BLExtract_Result.xlsx")

    written = write_bl_extracts(successes, out, failures=failures)
    print(f"Wrote {written} ({len(successes)} BL(s), {len(failures)} failed)")
    if failures:
        return 1
    return 0



def cmd_ocr_pdf(args: argparse.Namespace) -> int:
    """Scan PDF(s) → searchable PDFs under ocr_out/ (no invoice extract)."""
    from invoice_extractor.ocr import (
        default_ocr_out_dir,
        pdfs_to_searchable_pdfs,
        resolve_ocr_lang,
        find_tesseract,
        tesseract_available,
    )

    raw_paths: list[str] = list(getattr(args, "pdfs", None) or [])
    if getattr(args, "pdf", None) and args.pdf not in raw_paths:
        raw_paths.insert(0, args.pdf)

    files, path_errors = collect_pdfs(raw_paths)
    for err in path_errors:
        print(err, file=sys.stderr)
    # OCR is PDF-only — skip Excel inputs with a clear note.
    skipped_non_pdf = [f for f in files if f.suffix.lower() != ".pdf"]
    pdfs = [f for f in files if f.suffix.lower() == ".pdf"]
    for f in skipped_non_pdf:
        print(f"OCR skipped (not a PDF): {f}", file=sys.stderr)
    if not pdfs:
        print("No PDF inputs for OCR.", file=sys.stderr)
        return 2

    if not tesseract_available():
        print(
            "tesseract not found (install Tesseract OCR, set TESSERACT_CMD, "
            "or place portable tesseract/ next to the app)",
            file=sys.stderr,
        )
        return 2

    dest_dir = Path(args.out) if args.out else default_ocr_out_dir()
    lang = resolve_ocr_lang(find_tesseract())
    print(f"OCR lang={lang}; output dir={dest_dir}")
    written, failures = pdfs_to_searchable_pdfs(pdfs, dest_dir)
    for w in written:
        print(f"OK {w}")
    for src, err in failures:
        print(f"FAIL {src}: {err}", file=sys.stderr)
    if failures and not written:
        return 1
    if failures:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="invoice_extractor",
        description=(
            "Extract invoice header/items to Excel (.xlsx) or JSON from PDF/Excel inputs. "
            "Multiple files/directories → one workbook (Summary + Lines)."
        ),
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--init-db", action="store_true", help="Create/seed SQLite format DB")
    p.add_argument(
        "--db",
        dest="db_path",
        default=str(
            Path(__file__).resolve().parents[2] / "data" / "invoice_formats.db"
        ),
        help="Path to invoice_formats.db",
    )
    p.add_argument(
        "pdfs",
        nargs="*",
        help="Input PDF/Excel path(s) and/or directories (.pdf/.xlsx/.xlsm/.xls)",
    )
    p.add_argument(
        "--out",
        help=(
            f"Output path (default: {default_result_path().name} at tool root; "
            "same file every run). Use .json for JSON; .xlsx for Excel (template-based)."
        ),
    )
    p.add_argument("--gold", help="Gold JSON for offline compare via checker (single PDF)")
    p.add_argument(
        "--format",
        help="Force format_id (bitzer_v1|pt_gloria_v1|hangji_v1|nidec_v1|hitachi_gls_v1|highly_v1)",
    )
    p.add_argument(
        "--record-run",
        dest="db",
        action="store_true",
        help="Record run into SQLite",
    )
    p.add_argument(
        "--gui",
        action="store_true",
        help="Launch GUI (also default when no args)",
    )
    p.add_argument(
        "--ocr-pdf",
        action="store_true",
        help=(
            "OCR scan PDF(s) to searchable/copyable PDFs under ocr_out/ "
            "(stem.ocr.pdf). Does not run invoice extract. "
            "--out may set the output directory."
        ),
    )
    p.add_argument(
        "--doc-type",
        choices=["invoice", "bl"],
        default="invoice",
        help="invoice (default) or bl (arrival notice / HBL / B/L)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # No args or explicit --gui → GUI (double-click / empty invocation)
    if not argv or argv == ["--gui"] or argv == ["gui"]:
        from invoice_extractor.gui import run_gui

        run_gui()
        return 0
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "gui", False):
        from invoice_extractor.gui import run_gui

        run_gui()
        return 0
    if args.init_db:
        return cmd_init_db(args)
    if not args.pdfs:
        parser.error("pdf path required (or use --init-db / --gui / --ocr-pdf)")
    # Compat attribute for older tests / callers
    args.pdf = args.pdfs[0] if args.pdfs else None
    if getattr(args, "ocr_pdf", False):
        return cmd_ocr_pdf(args)
    if getattr(args, "doc_type", "invoice") == "bl":
        return cmd_extract_bl(args)
    return cmd_extract(args)


if __name__ == "__main__":
    raise SystemExit(main())
