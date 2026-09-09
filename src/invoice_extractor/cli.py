"""CLI: invoice-extract / python -m invoice_extractor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from invoice_extractor import __version__
from invoice_extractor.checker import hard_check
from invoice_extractor.db import connect, record_run, seed_builtin_formats
from invoice_extractor.gold_stub import (
    load_gold,
    offline_compare,
    write_needs_gold_placeholder,
)
from invoice_extractor.rules_engine import extract_invoice, file_sha256


def _out_path_for(pdf: Path, out: str | None) -> Path:
    if out:
        return Path(out)
    return pdf.with_suffix(pdf.suffix + ".extract.json") if pdf.suffix else pdf.with_suffix(".extract.json")


def cmd_init_db(args: argparse.Namespace) -> int:
    path = seed_builtin_formats(args.db)
    print(f"DB ready: {path}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    pdf = Path(args.pdf)
    if not pdf.is_file():
        print(f"File not found: {pdf}", file=sys.stderr)
        return 2

    result = extract_invoice(pdf, format_id=args.format)
    data = result.to_dict()
    hard = hard_check(data)
    data["meta"]["checker_verdict"] = hard["verdict"]
    if hard["verdict"] == "pass" and data["meta"].get("confidence") == "rules":
        data["meta"]["confidence"] = "high"
    elif hard["verdict"] == "conflict":
        data["meta"]["confidence"] = "conflict"
    data["meta"]["checker_issues"] = hard.get("issues")

    if args.gold:
        cmp = offline_compare(data, args.gold)
        data["meta"]["gold_compare"] = cmp
        print(json.dumps(cmp, ensure_ascii=False, indent=2))
        if args.out:
            Path(args.out).write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return 0 if cmp["verdict"] == "pass" and not cmp.get("diffs") else 1

    out = _out_path_for(pdf, args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")

    if data["meta"].get("needs_gold") or hard["verdict"] == "needs_gold":
        stub = out.with_suffix(".needs_gold.json")
        write_needs_gold_placeholder(stub, data)
        print(f"Gold stub: {stub}")

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
                gold_json=load_gold(args.gold) if args.gold else None,
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"(run log skipped: {e})", file=sys.stderr)

    # brief stdout summary
    h = data.get("header") or {}
    print(
        f"format={data['meta'].get('format_id')} invoice_no={h.get('invoice_no')} "
        f"amount={h.get('amount')} items={len(data.get('items') or [])} "
        f"verdict={hard['verdict']}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="invoice_extractor",
        description="Extract invoice header/items JSON from PDF (rules engine v1)",
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
    p.add_argument("pdf", nargs="?", help="Input PDF path")
    p.add_argument("--out", help="Output JSON path (default: <pdf>.extract.json)")
    p.add_argument("--gold", help="Gold JSON for offline compare via checker")
    p.add_argument("--format", help="Force format_id (bitzer_v1|pt_gloria_v1|hangji_v1|nidec_v1|hitachi_gls_v1|highly_v1)")
    p.add_argument(
        "--record-run",
        dest="db",
        action="store_true",
        help="Record run into SQLite",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.init_db:
        return cmd_init_db(args)
    if not args.pdf:
        parser.error("pdf path required (or use --init-db)")
    return cmd_extract(args)


if __name__ == "__main__":
    raise SystemExit(main())
