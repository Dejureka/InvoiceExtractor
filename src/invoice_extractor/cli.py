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


def collect_pdfs(paths: list[str | Path]) -> tuple[list[Path], list[str]]:
    """Expand files and directories into a de-duplicated PDF list.

    Returns (pdfs, errors) where errors are human-readable path problems.
    """
    found: list[Path] = []
    errors: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            matches = sorted(
                {*(p.glob("*.pdf")), *(p.glob("*.PDF")), *(p.glob("*.Pdf"))}
            )
            if not matches:
                errors.append(f"No PDFs in directory: {p}")
                continue
            for m in matches:
                key = str(m.resolve()) if m.exists() else str(m)
                if key not in seen:
                    seen.add(key)
                    found.append(m)
        elif p.is_file():
            if p.suffix.lower() != ".pdf":
                errors.append(f"Not a PDF: {p}")
                continue
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                found.append(p)
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
        print("No PDF inputs to extract.", file=sys.stderr)
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

    successes: list[dict] = []
    failures: list[dict] = []

    for pdf in pdfs:
        try:
            data = _prepare_extract(pdf, args.format)
            hard = data.pop("_hard")
            warn = data["meta"].get("text_backend_warning")
            if warn:
                print(f"WARNING: {pdf.name}: {warn}", file=sys.stderr)
            successes.append(data)
            h = data.get("header") or {}
            print(
                f"OK {pdf.name}: format={data['meta'].get('format_id')} "
                f"invoice_no={h.get('invoice_no')} amount={h.get('amount')} "
                f"items={len(data.get('items') or [])} verdict={hard['verdict']} "
                f"backend={data['meta'].get('text_backend')}"
            )
            if args.db or Path(args.db_path).is_file():
                try:
                    conn = connect(args.db_path)
                    record_run(
                        conn,
                        source_hash=file_sha256(pdf),
                        source_file=str(pdf),
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
            failures.append({"source_file": str(pdf), "error": str(e), "meta": {"source_file": str(pdf)}})
            print(f"FAIL {pdf}: {e}", file=sys.stderr)

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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="invoice_extractor",
        description=(
            "Extract invoice header/items to Excel (.xlsx) or JSON from PDF(s). "
            "Multiple PDFs/directories → one workbook (Summary + Lines)."
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
        help="Input PDF path(s) and/or directories of PDFs",
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
        parser.error("pdf path required (or use --init-db / --gui)")
    # Compat attribute for older tests / callers
    args.pdf = args.pdfs[0] if args.pdfs else None
    return cmd_extract(args)


if __name__ == "__main__":
    raise SystemExit(main())
