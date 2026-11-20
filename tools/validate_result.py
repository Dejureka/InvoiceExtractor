"""Audit exported invoice results without changing extraction or hard_check."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
from dataclasses import astuple, dataclass, fields
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.utils.exceptions import InvalidFileException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from invoice_extractor import export
from invoice_extractor.checker import AMOUNT_TOL, REQUIRE_LINE_HS_FORMATS, _labeled_total
from invoice_extractor.pairing import STATUS_BL_ONLY

# SIX ISO 4217 List One, including registered funds and special-purpose codes.
ISO_CURRENCIES = frozenset("""
AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BHD BIF BMD BND BOB BOV BRL BSD
BTN BWP BYN BZD CAD CDF CHE CHF CHW CLF CLP CNY COP COU CRC CUP CVE CZK DJF DKK
DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF
IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP
LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MXV MYR MZN NAD
NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD
SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD
TWD TZS UAH UGX USD USN UYI UYU UYW UZS VED VES VND VUV WST XAD XAF XAG XAU XBA
XBB XBC XBD XCD XCG XDR XOF XPD XPF XPT XSU XTS XUA XXX YER ZAR ZMW ZWG
""".split())

RULES = {
    "shipment_first_prefixes": ("ma_", "bhc_"),
    "soft_hs_prefixes": ("bhc_",),
    "hard_hs_formats": REQUIRE_LINE_HS_FORMATS,
    "hs_lengths": (6, 8, 10, 11),
    "ebike": "ebike_ax_billing_v1",
    "amount_tolerance": Decimal("0.01"),
    "weight_tolerance": Decimal(str(AMOUNT_TOL)),
}
SUMMARY_FIELDS = (
    "invoice_no", "total_pkg", "package_mode", "gross_weight_kg", "incoterm",
    "amount", "item_line_count", "total_quantity", "currency", "bl_no",
    "bl_packages", "bl_gross_weight_kg",
)
LINE_FIELDS = (
    "part_no", "description", "qty", "unit_price", "amount", "unit", "origin",
    "hs_code", "net_weight", "invoice_no", "currency",
)
NUMERIC_FIELDS = {
    "total_pkg", "gross_weight_kg", "amount", "item_line_count", "total_quantity",
    "bl_packages", "bl_gross_weight_kg", "qty", "unit_price", "net_weight",
}
IDENTIFIER_FIELDS = {"invoice_no", "hs_code", "bl_no"}
NUMBER_TOKEN = re.compile(r"(?<![\w.])[+-]?\d[\d,]*(?:\.\d+)?(?![\w.])")
SHIPMENT_NOTE = re.compile(r"shipment pkg/GW \(deduped\) on ([^;]+)", re.I)
PRINTED_PACKING = re.compile(r"printed pkg/GW\s+([\d.,]+)\s*/\s*([\d.,]+)", re.I)
PACKING_FIELDS = ("total_pkg", "gross_weight_kg")
SAGINOMIYA_PROFILE = re.compile(r"\bprofile=saginomiya\b", re.I)
GW_FROM_BL_NOTE = re.compile(r"\buse BL G\.?W\b", re.I)


def printed_pn_blank_noted(data) -> bool:
    """True when the extract documents that the source printed no PN (sanhua rule)."""
    meta = data.get("meta") or {}
    note = str(meta.get("notes") or "")
    return bool(re.search(r"(CUSTOMERS NO\.|Bosch PN|\bPN\b)[^;]*\bblank on this document\b", note, re.I))


@dataclass
class Finding:
    status: str
    rule_id: str
    invoice_no: str
    row: str | int
    field: str
    expected: object
    actual: object
    page: int | str
    position: str
    note: str


@dataclass
class Report:
    findings: list[Finding]
    invoices_checked: int

    @property
    def counts(self):
        counts = Counter(f.status for f in self.findings)
        return {status: counts[status] for status in ("ok", "warn", "hard")}

    def summary(self):
        yield ("invoices checked", "", self.invoices_checked)
        for group, counts in (
            ("status", self.counts),
            ("rule", Counter(f.rule_id for f in self.findings)),
            ("invoice", Counter(f.invoice_no for f in self.findings)),
        ):
            for key, count in sorted(counts.items()):
                yield group, key, count

    def markdown(self):
        return (
            "# Result validation\n\n" + markdown_table(("Group", "Name", "Count"), self.summary())
            + "\n## Findings\n\n"
            + markdown_table(tuple(f.name for f in fields(Finding)), map(astuple, self.findings))
        )

    def write(self, path):
        path = Path(path)
        if path.suffix.lower() not in {".md", ".xlsx"}:
            raise ValueError("Report must end in .xlsx or .md")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".md":
            path.write_text(self.markdown(), encoding="utf-8")
            return
        wb = Workbook()
        wb.active.title = "Findings"
        for sheet, headings, rows in (
            (wb.active, tuple(f.name for f in fields(Finding)), map(astuple, self.findings)),
            (wb.create_sheet("Summary"), ("Group", "Name", "Count"), self.summary()),
        ):
            sheet.append(headings)
            for values in rows:
                sheet.append([display(value) for value in values])
                for cell in sheet[sheet.max_row]:
                    if isinstance(cell.value, str):
                        cell.data_type = "s"
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
        wb.save(path)


def display(value):
    if isinstance(value, Decimal):
        return str(value)
    return export._cell(value)


def markdown_table(headings, rows):
    def render(row):
        return "| " + " | ".join(
            str(display(v) if v is not None else "").replace("|", "\\|").replace("\n", "<br>")
            for v in row
        ) + " |\n"

    return render(headings) + render(["---"] * len(headings)) + "".join(map(render, rows))


def blank(value):
    return value is None or isinstance(value, str) and not value.strip()


def number(value):
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def first_number(*values):
    return next((parsed for value in values if (parsed := number(value)) is not None), None)


def gold_fields(meta):
    fields_ = meta.get("needs_gold_fields") or ()
    if isinstance(fields_, str):
        fields_ = [fields_]
    return {str(value).rsplit(".", 1)[-1] for value in fields_}


def notes_for(header, meta):
    return "; ".join(str(value) for value in (header.get("summary_note"), meta.get("notes")) if value)


def non_first_shipment(header, meta):
    fmt = meta.get("format_id") or ""
    if not fmt.startswith(RULES["shipment_first_prefixes"]):
        return False
    note = notes_for(header, meta)
    shipment = meta.get("shipment_packing") or {}
    first = shipment.get("first_invoice")
    invoice = str(header.get("invoice_no") or "")
    match = SHIPMENT_NOTE.search(note)
    if match:
        target = match[1].strip()
        return bool(target and target != invoice and (not first or target == str(first)))
    return bool(
        shipment.get("mode") == "shipment_first" and first and str(first) != invoice
        and (PRINTED_PACKING.search(note) or str(first) in note)
    )


def invoice_source(data):
    meta = data["meta"]
    return meta.get("inv_file") or meta.get("source_file") or ""


def twin_rows(group):
    if len(group) != 2 or not all(map(invoice_source, group)):
        return False
    left, right = (Path(str(invoice_source(d)).replace("\\", "/")) for d in group)
    extensions = {left.suffix.lower(), right.suffix.lower()}
    return left.parent == right.parent and extensions in ({".pdf", ".xls"}, {".pdf", ".xlsx"})


def twin_label(twin):
    source = invoice_source(twin)
    return f"{twin['_summary_row']} ({source})" if "_summary_row" in twin else str(source)


def bill_refs(header):
    refs = header.get("invoice_refs") or ()
    if isinstance(refs, str):
        refs = re.split(r"[,;\s]+", refs)
    return set(map(str, refs))


def gw_from_bl(data, bills):
    header, meta = data["header"], data["meta"]
    if (meta.get("format_id") != "bhc_vendor_ci_v1"
            or not SAGINOMIYA_PROFILE.search(str(meta.get("notes") or ""))
            or not GW_FROM_BL_NOTE.search(str(header.get("summary_note") or ""))):
        return False
    bl_no = header.get("bl_no")
    gw = header.get("bl_gross_weight_kg")
    weights = [] if blank(gw) else [gw]
    linked = bool(bl_no or meta.get("bl_file") or meta.get("bl_used"))
    for bill in bills:
        h = bill["header"]
        if ((bl_no and str(bl_no) == str(h.get("bl_no") or h.get("hbl_no")))
                or (not bl_no and str(header.get("invoice_no")) in bill_refs(h))):
            linked = True
            value = first_number(h.get("gross_weight_kg"), h.get("bl_gross_weight_kg"))
            if value is not None:
                weights.append(value)
    return all((number(value) or 0) > 0 for value in weights) if weights else not linked


class Audit:
    def __init__(self, stack):
        self.stack = stack
        self.report = Report([], 0)
        self.pdf = {}
        self.locations = {}

    def pages(self, path):
        if path not in self.pdf:
            try:
                import pymupdf as fitz
            except ImportError:  # Older PyMuPDF distributions use this import name.
                import fitz

            pages = ()
            if Path(path).is_file() and Path(path).suffix.lower() == ".pdf":
                try:
                    doc = self.stack.enter_context(fitz.open(path))
                    pages = tuple((page, page.get_textpage()) for page in doc)
                except (RuntimeError, ValueError, OSError):
                    pass
            self.pdf[path] = pages
        return self.pdf[path]

    def locate(self, path, anchors):
        key = path, anchors
        if key not in self.locations:
            self.locations[key] = self.find_anchor(path, anchors)
        return self.locations[key]

    def find_anchor(self, path, anchors):
        if path:
            try:
                pages = self.pages(path)
                for anchor in anchors:
                    for page, text in pages:
                        hits = page.search_for(anchor, textpage=text)
                        if hits:
                            return page.number + 1, str(tuple(round(v, 2) for v in hits[0]))
            except (RuntimeError, ValueError, OSError):
                pass
        return "?", "anchor: " + (anchors[0] if anchors else "?")

    def add(self, data, status, rule, field, expected, actual, *, line=None, row=None,
            note="", anchor=None, related=(), source=None):
        header, meta = data["header"], data["meta"]
        marked = gold_fields(meta)
        if marked.intersection((field, *related)):
            status = "warn"
            note = f"{note}; needs_gold".strip("; ")
        if row is None:
            row = data.get("_summary_row", "header")
            if line is not None:
                row = data.get("_line_rows", {}).get(line, line)
        anchors = tuple(dict.fromkeys(
            str(v).strip() for v in (anchor, actual, header.get("invoice_no"), field)
            if not blank(v)
        ))
        page, position = self.locate(source or meta.get("source_file"), anchors)
        self.report.findings.append(Finding(
            status, rule, str(header.get("invoice_no") or header.get("bl_no") or ""),
            row, field, expected, actual, page, position, note,
        ))

    def invoice(self, data, twin, bills):
        header, items, meta = data["header"], data["items"], data["meta"]
        fmt = meta.get("format_id") or ""
        note = notes_for(header, meta)
        ebike = fmt == RULES["ebike"]
        non_first = non_first_shipment(header, meta)
        for field in ("invoice_no", "invoice_date", "currency", "amount", *PACKING_FIELDS):
            if field == "invoice_date" and data.get("_no_date_column"):
                continue
            value = header.get(field)
            numeric = field in NUMERIC_FIELDS
            missing = number(value) is None if numeric else blank(value)
            if field in PACKING_FIELDS and number(value) == 0 and not non_first:
                missing = True
            if missing:
                if (field in PACKING_FIELDS and blank(value) and twin
                        and (number(twin["header"].get(field)) or 0) > 0):
                    self.add(data, "warn", "W_TWIN_PKG_BLANK", field, twin["header"][field], value,
                             note=f"Packing value carried by twin row {twin_label(twin)}")
                elif field == "gross_weight_kg" and not twin and blank(value) and gw_from_bl(data, bills):
                    self.add(data, "warn", "W_GW_FROM_BL", field, "BL gross weight", value,
                             note=header["summary_note"])
                else:
                    self.add(data, "hard", "H_HDR_MISSING", field, "present", value)
            if field in PACKING_FIELDS and twin:
                other = twin["header"].get(field)
                if not blank(value) and not blank(other) and number(value) != number(other):
                    self.add(data, "hard", "H_TWIN_PKG_CONFLICT", field, other, value,
                             note=f"Packing value differs from twin row {twin_label(twin)}")
        raw_date = header.get("invoice_date")
        if not blank(raw_date) and not valid_date(raw_date):
            self.add(data, "hard", "H_DATE", "invoice_date", "valid date", raw_date)
        currency = header.get("currency")
        if not blank(currency) and (not isinstance(currency, str) or currency not in ISO_CURRENCIES):
            self.add(data, "hard", "H_CURRENCY", "currency", "ISO 4217 code", currency)
        pkg = number(header.get("total_pkg"))
        if pkg is not None and pkg != 0 and (pkg < 0 or pkg != pkg.to_integral_value()):
            self.add(data, "hard", "H_PKG_INTEGER", "total_pkg", "positive integer", pkg)
        count = number(header.get("item_line_count"))
        if count is not None and count != len(items):
            self.add(data, "hard", "H_LINE_COUNT", "item_line_count", count, len(items))
        total_nw = first_number(meta.get("total_nw"), meta.get("total_net_weight_kg"),
                                header.get("total_nw"), header.get("total_net_weight_kg"))
        if total_nw is None:
            match = re.search(r"Total Net Weight\s+([\d.,]+)\s*kg", note, re.I)
            if match:
                total_nw = number(match[1].replace(",", ""))
        gw = number(header.get("gross_weight_kg"))
        if total_nw is not None and gw is not None and gw <= total_nw and not non_first:
            self.add(data, "hard", "H_GW_NW", "gross_weight_kg", f"> {total_nw}", gw)

        positions = []
        for index, item in enumerate(items, 1):
            position = next((item[k] for k in ("item_no", "item_number", "pos_no", "position_no", "pos", "position")
                             if not blank(item.get(k))), None)
            positions.append(position)
            self.line(data, item, index, fmt, ebike, total_nw)
        if any(value is not None for value in positions):
            projected = [number(value) for value in positions]
            valid = all(value is not None and value == value.to_integral_value() for value in projected)
            # Commercial documents commonly number positions 10, 20, ... .
            start = projected[0]
            step = 10 if start == 10 else 1
            if not valid or start not in (0, 1, 10) or projected != [
                start + step * index for index in range(len(items))
            ]:
                self.add(data, "hard", "H_LINE_POS", "item_no", "continuous printed positions", positions)
        self.invoice_amount(data, note)
        self.packing(data, note, non_first)
        if (meta.get("watermark") or meta.get("is_copy") or meta.get("copy_watermark")
                or meta.get("not_valid")
                or re.search(r"\bnot valid\b|\bcopy watermark\b|\bwatermark\s*[:=]?\s*copy\b"
                             r"|\bmarked (?:as )?copy\b|(?:^|;)\s*copy\s*(?:$|;)", note, re.I)):
            self.add(data, "warn", "W_WATERMARK", "watermark", "original", meta.get("watermark") or note or "Copy",
                     anchor="NOT VALID" if "not valid" in note.lower() else "Copy")
        currency_text = f"{currency} {meta.get('currencies')} {note}".upper()
        if ebike or meta.get("dual_currency") or all(re.search(rf"\b{c}\b", currency_text) for c in ("EUR", "HUF")):
            self.add(data, "warn", "W_DUAL_CURRENCY", "currency", "EUR invoice value", currency,
                     anchor="HUF", note="EUR invoice with HUF conversion")

    def line(self, data, item, index, fmt, ebike, total_nw):
        part = item.get("part_no")

        def finding(status, rule, field, expected, actual, note="", related=()):
            self.add(data, status, rule, field, expected, actual, line=index,
                     note=note, anchor=part, related=related)

        qty, price, amount = (number(item.get(key)) for key in ("qty", "unit_price", "amount"))
        for field, missing in (("part_no", blank(part)), ("qty", qty is None), ("amount", amount is None)):
            if not missing:
                continue
            if field == "part_no" and printed_pn_blank_noted(data):
                # Documented rule (ADD_INVOICE_FORMAT.md, bhc_vendor_ci_v1 sanhua):
                # PN not printed on the PDF -> leave blank + note. Note must exist.
                finding("warn", "W_PN_BLANK_PRINTED", field, "present", item.get(field),
                        note="PN not printed on source; documented blank+note rule")
                continue
            finding("hard", "H_LINE_MISSING", field, "present", item.get(field))
        hs = item.get("hs_code")
        if blank(hs):
            if fmt in RULES["hard_hs_formats"]:
                finding("hard", "H_HS_MISSING", "hs_code", "HS code", hs)
            elif ebike or fmt.startswith(RULES["soft_hs_prefixes"]):
                finding("warn", "W_HS_MISSING", "hs_code", "HS code", hs)
        else:
            digits = re.sub(r"[.\s]", "", str(hs))
            if not re.fullmatch(r"[0-9]+", digits) or len(digits) not in RULES["hs_lengths"]:
                finding("hard", "H_HS_FORMAT", "hs_code", "6, 8, 10 or 11 digits", hs)

        pricing = item.get("pricing_unit")
        divisor = Decimal(1) if blank(pricing) else number(pricing)
        if divisor is None or divisor <= 0:
            finding("hard", "H_PRICING_UNIT", "pricing_unit", "positive number", pricing)
        elif None not in (qty, price, amount):
            if ebike and qty:
                expected_price = round(amount / qty, 6)
                if price != expected_price:
                    finding("hard", "H_LINE_MATH", "unit_price", expected_price, price,
                            related=("amount", "qty"))
            else:
                calculated = qty * price / divisor
                printed_unit = number(item.get("amount_decimal_unit"))
                if printed_unit is None or printed_unit <= 0:
                    printed_unit = Decimal(1).scaleb(amount.as_tuple().exponent)
                tolerance = max(RULES["amount_tolerance"], printed_unit / 2)
                delta = abs(calculated - amount)
                if delta:
                    status, rule = ("hard", "H_LINE_MATH") if delta > tolerance else ("warn", "W_ROUNDING")
                    finding(status, rule, "amount", calculated, amount,
                            f"Tolerance {tolerance}", related=("qty", "unit_price", "pricing_unit"))
        nw = first_number(item.get("net_weight"), item.get("net_weight_kg"))
        if ebike and total_nw is not None and nw is not None and nw > total_nw:
            finding("warn", "W_LINE_NW", "net_weight", f"≤ {total_nw}", nw)

    def invoice_amount(self, data, note):
        meta = data["meta"]
        labeled, label = _labeled_total(data)
        expected = first_number(meta.get("printed_amount"), labeled)
        amounts = [number(item.get("amount")) for item in data["items"]]
        if any(value is None for value in amounts):
            return
        total = sum(amounts, Decimal(0))
        note_lower = note.lower()
        amount_override = (
            "ocr total" in note_lower or "vendor typo" in note_lower
            or re.search(r"printed (?:total|amount|value)", note_lower)
        )
        used_line_sum = (
            meta.get("vendor_typo") or meta.get("line_sum_used")
            or amount_override and ("sum(lines)" in note_lower or "line sum" in note_lower)
        )
        if used_line_sum:
            note_values = [number(v.replace(",", "")) for v in NUMBER_TOKEN.findall(note)]
            printed = re.search(r"(?:printed(?:\s+(?:invoice\s+)?(?:total|amount|value))?|OCR TOTAL(?: read)?)"
                                r"\s*[:=]?\s*(?:[A-Z]{3}\s+)?([\d,.]+)", note, re.I)
            documented = printed is not None or expected is not None and expected != total and expected in note_values
            if not documented or number(data["header"].get("amount")) == total:
                self.add(data, "warn" if documented else "hard",
                         "W_VENDOR_TOTAL" if documented else "H_VENDOR_TOTAL_NOTE", "amount",
                         printed[1] if printed else expected, total, note=note)
            else:
                self.add(data, "hard", "H_VENDOR_TOTAL_VALUE", "amount", total,
                         data["header"].get("amount"), note="Documented line sum differs from invoice value")
        elif expected is not None and (meta.get("printed_amount") is not None or "sum(lines)" not in str(label).lower()):
            delta = abs(expected - total)
            if delta:
                mismatch = delta > RULES["amount_tolerance"]
                self.add(data, "hard" if mismatch else "warn",
                         "H_PRINTED_AMOUNT" if mismatch else "W_ROUNDING",
                         "amount", expected, total, anchor=expected, note=str(label or "Printed total"))

    def packing(self, data, note, non_first):
        header, meta = data["header"], data["meta"]
        shipment_family = (meta.get("format_id") or "").startswith(RULES["shipment_first_prefixes"])
        shipment = (meta.get("shipment_packing") or {}) if shipment_family else {}
        printed = PRINTED_PACKING.search(note)
        first_note = shipment_family and re.search(r"shipment pkg/GW \(deduped\)\s+([\d.,]+)\s*/\s*([\d.,]+) on this first", note, re.I)
        for index, field, keys in (
            (1, "total_pkg", ("printed_pkg", "printed_total_pkg", "labeled_pkg")),
            (2, "gross_weight_kg", ("printed_gw", "printed_gross_weight_kg", "labeled_gross_weight_kg")),
        ):
            actual = number(header.get(field))
            expected = first_number(*(meta.get(key) for key in keys))
            if expected is None and printed:
                expected = number(printed[index].replace(",", ""))
            if non_first:
                expected = Decimal(0)
            elif shipment.get("mode") == "shipment_first" and shipment.get(field) is not None:
                expected = number(shipment[field])
            elif first_note:
                expected = number(first_note[index].replace(",", ""))
            if expected is not None and actual is not None and expected != actual:
                tolerance = Decimal(0) if field == "total_pkg" or non_first else RULES["weight_tolerance"]
                mismatch = abs(expected - actual) > tolerance
                self.add(data, "hard" if mismatch else "warn",
                         "H_PRINTED_PACKING" if mismatch else "W_ROUNDING",
                         field, expected, actual, anchor=expected)

    def bill_of_lading(self, invoices, bills, twins):
        groups = defaultdict(list)
        totals = defaultdict(list)
        bill_metadata = defaultdict(list)
        for data in invoices:
            h = data["header"]
            if not blank(h.get("bl_no")):
                key = str(h["bl_no"])
                groups[key].append(data)
                totals[key].append((h.get("bl_packages"), h.get("bl_gross_weight_kg")))
        for bill in bills:
            h = bill["header"]
            key = h.get("bl_no") or h.get("hbl_no")
            if blank(key):
                continue
            totals[str(key)].append((first_number(h.get("packages"), h.get("bl_packages")),
                                     first_number(h.get("gross_weight_kg"), h.get("bl_gross_weight_kg"))))
            bill_metadata[str(key)].append(bill["meta"])
            refs = bill_refs(h)
            for data in invoices:
                inv = data["header"].get("invoice_no")
                if not data["header"].get("bl_no") and str(inv) in refs:
                    groups[str(key)].append(data)

        membership = defaultdict(set)
        for key, group in groups.items():
            for data in group:
                membership[id(data)].add(key)
        for key, group in groups.items():
            for index, field, bl_field, document_field in (
                (0, "total_pkg", "bl_packages", "packages"),
                (1, "gross_weight_kg", "bl_gross_weight_kg", "gross_weight_kg"),
            ):
                bill_meta = bill_metadata[key]
                source = next((m["source_file"] for m in bill_meta if m.get("source_file")), None)
                marked_on_bill = any(gold_fields(m).intersection((bl_field, document_field)) for m in bill_meta)
                marked = next((data for data in group if gold_fields(data["meta"]).intersection((field, bl_field))),
                              group[0])
                if marked_on_bill:
                    meta = {**marked["meta"], "needs_gold_fields": gold_fields(marked["meta"]) | {bl_field}}
                    marked = {**marked, "meta": meta}
                expected = {n for values in totals[key] if (n := number(values[index])) is not None}
                values = self.shipment_values(group, field, twins, membership, key)
                if len(expected) > 1:
                    self.add(marked, "hard", "H_BL_TOTAL_CONFLICT", bl_field,
                             "one total", sorted(map(str, expected)), note=f"BL {key}", source=source)
                if len(expected) != 1 or None in values:
                    continue
                target = next(iter(expected))
                actual = sum(values, Decimal(0))
                tolerance = Decimal(0) if index == 0 else RULES["weight_tolerance"]
                delta = abs(actual - target)
                if delta:
                    mismatch = delta > tolerance
                    self.add(marked, "hard" if mismatch else "warn",
                             "H_BL_TOTAL" if mismatch else "W_ROUNDING",
                             bl_field, target, actual, anchor=target, note=f"BL {key}", related=(field,),
                             source=source or marked["meta"].get("bl_file"))

    @staticmethod
    def shipment_values(group, field, twins, membership, key):
        values = []
        counted = set()
        for data in group:
            if id(data) in counted:
                continue
            value = data["header"].get(field)
            twin = twins.get(id(data))
            if twin and (not membership[id(twin)] or key in membership[id(twin)]):
                counted.add(id(twin))
                known = {
                    number(raw) for raw in (value, twin["header"].get(field)) if not blank(raw)
                }
                # Conflicting twin values already have a hard packing finding.
                values.append(next(iter(known)) if len(known) == 1 else None)
            else:
                values.append(number(value))
        return values


def valid_date(value):
    if isinstance(value, date):
        return True
    try:
        date.fromisoformat(str(value))
        return True
    except ValueError:
        pass
    for fmt in ("%Y/%m/%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y", "%d-%b-%Y", "%d/%b/%y",
                "%b.%d,%Y", "%b %d, %Y", "%d-%b-%y"):
        try:
            datetime.strptime(str(value), fmt)
            return True
        except ValueError:
            continue
    return False


def read_extracts(inputs):
    """Read individual extracts, lists, or snapshots keyed by source stem."""
    if isinstance(inputs, (str, Path, dict)):
        inputs = [inputs]
    result = []
    for value in inputs:
        if isinstance(value, dict):
            if "header" in value:
                if (not isinstance(value["header"], dict)
                        or value.get("meta") is not None and not isinstance(value["meta"], dict)
                        or value.get("items") is not None and (
                            not isinstance(value["items"], list)
                            or any(not isinstance(item, dict) for item in value["items"])
                        )):
                    raise ValueError("Invalid extract header/items/meta")
                result.append({**value, "meta": value.get("meta") or {}, "items": value.get("items") or []})
            elif value:
                result.extend(read_extracts(value.values()))
            else:
                raise ValueError("Empty extract object")
        elif isinstance(value, list):
            result.extend(read_extracts(value))
        else:
            path = Path(value)
            if path.is_dir():
                paths = sorted(path.rglob("*.json"))
                if not paths:
                    raise ValueError(f"No JSON files in {path}")
                result.extend(read_extracts(paths))
            else:
                raw = json.loads(path.read_text(encoding="utf-8-sig"))
                if not isinstance(raw, (dict, list)):
                    raise ValueError(f"Expected extract object or list in {path}")
                result.extend(read_extracts(raw))
    return result


def workbook_rows(sheet):
    headings = [cell.value for cell in sheet[1]]
    for cells in sheet.iter_rows(min_row=2):
        if any(cell.value is not None for cell in cells):
            yield cells[0].row, dict(zip(headings, (cell.value for cell in cells)))


def workbook_extracts(wb):
    summaries, lines = wb[export.SUMMARY_SHEET], wb[export.LINES_SHEET]
    metadata = []
    if export.META_SHEET in wb:
        metadata = [row for _, row in workbook_rows(wb[export.META_SHEET]) if row.get("status") != "error"]
    by_invoice = defaultdict(list)
    for row, values in workbook_rows(lines):
        item = dict(zip(LINE_FIELDS, (values.get(col) for col in export.LINES_COLS)))
        by_invoice[str(item["invoice_no"])].append((row, item))
    result = []
    summary_rows = list(workbook_rows(summaries))
    remaining = Counter(str(values.get("Invoice No.")) for _, values in summary_rows)
    for index, (row, values) in enumerate(summary_rows):
        names = export.summary_header_map(list(values))
        header = dict(zip(SUMMARY_FIELDS, (values.get(names.get(col)) for col in export.SUMMARY_COLS)))
        date_name = next((key for key in ("Invoice Date", "Date", "invoice_date") if key in values), None)
        if date_name:
            header["invoice_date"] = values[date_name]
        for col in ("Packages", export.SUMMARY_GW_COL):
            column = names.get(col)
            if column:
                cell = next(cell for cell in summaries[1] if cell.value == column)
                comment = summaries.cell(row, cell.column).comment
                if comment:
                    header["summary_note"] = comment.text
                    break
        key = str(header["invoice_no"])
        remaining[key] -= 1
        entries = by_invoice.get(key, [])
        if looks_bl_only(header):
            entries = []
        else:
            count = number(header.get("item_line_count"))
            if remaining[key] and count is not None and 0 <= count == count.to_integral_value():
                entries = entries[:int(count)]
            by_invoice[key] = by_invoice[key][len(entries):]
        meta = metadata[index].copy() if index < len(metadata) else {}
        details = meta.get("checker_details")
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except ValueError:
                details = None
        if isinstance(details, dict):
            meta["needs_gold_fields"] = details.get("needs_gold_fields")
        result.append({
            "header": header, "meta": meta, "items": [item for _, item in entries],
            "_summary_row": f"Summary!{row}",
            "_line_rows": {i: f"Lines!{line}" for i, (line, _) in enumerate(entries, 1)},
            "_no_date_column": date_name is None,
        })
    orphans = [(row, item) for entries in by_invoice.values() for row, item in entries]
    return result, orphans


def workbook_checks(audit, wb, entries, orphans, format_filter):
    for row, item in orphans:
        if not format_filter:
            audit.add({"header": {"invoice_no": item["invoice_no"]}, "meta": {}},
                      "hard", "H_ORPHAN_LINE", "invoice_no", "matching Summary row", item["invoice_no"],
                      row=f"Lines!{row}", anchor=item["part_no"])
    for data in entries:
        if not selected(data, format_filter):
            continue
        for fields_, values, row in (
            (SUMMARY_FIELDS, data["header"], data["_summary_row"]),
            *((LINE_FIELDS, item, data["_line_rows"][i]) for i, item in enumerate(data["items"], 1)),
        ):
            ws, row_number = row.split("!")
            headers = [cell.value for cell in wb[ws][1]]
            aliases = export.summary_header_map(headers)
            names = export.SUMMARY_COLS if ws == export.SUMMARY_SHEET else export.LINES_COLS
            for field, name in zip(fields_, names):
                value = values.get(field)
                if blank(value):
                    continue
                cell = wb[ws].cell(int(row_number), headers.index(aliases.get(name, name)) + 1)
                if problem := cell_problem(field, cell):
                    audit.add(data, "hard", "H_XLSX_TYPE", field, problem, value,
                              row=f"{ws}!{cell.coordinate}")


def cell_problem(field, cell):
    value = cell.value
    if blank(value):
        return None
    if field in NUMERIC_FIELDS and (cell.data_type != "n" or number(value) is None):
        return "number"
    if field in IDENTIFIER_FIELDS and (
        not isinstance(value, str) or cell.data_type == "f"
        or re.fullmatch(r"[+-]?\d+(?:\.\d+)?[eE][+-]?\d+", value)
    ):
        return "text identifier"
    if field == "unit_price":
        match = re.fullmatch(r"[#0,]+(?:\.([#0]+))?", cell.number_format.split(";")[0])
        if match and (precision := len(match.group(1) or "")) < 6:
            price = number(value)
            if price is not None and price != round(price, precision):
                return "number format that displays the stored precision"
    return None


def compare_workbook(audit, wb, extracts, format_filter):
    """Compare logical cell values and Excel value types using exporter row mappings."""
    expected_rows = {
        export.SUMMARY_SHEET: [(d, export._summary_row(d["header"])) for d in extracts],
        export.LINES_SHEET: [(d, export._lines_row(it, d["header"])) for d in extracts for it in d["items"]],
        export.META_SHEET: [(d, export._meta_row(d["meta"])) for d in extracts],
    }
    empty = {"header": {}, "meta": {}}
    expected_wb = Workbook()
    for sheet_name, cols, internal in (
        (export.SUMMARY_SHEET, export.SUMMARY_COLS, SUMMARY_FIELDS),
        (export.LINES_SHEET, export.LINES_COLS, LINE_FIELDS),
        (export.META_SHEET, export.META_COLS, export.META_COLS),
    ):
        sheet = wb[sheet_name] if sheet_name in wb else None
        if sheet is None:
            # Legacy Result can be audited alone. A paired export must have all sheets.
            audit.add(empty, "hard", "H_XLSX_DIFF", sheet_name, "sheet present", None, row=sheet_name)
            continue
        rows = expected_rows[sheet_name]
        expected_ws = expected_wb.active
        for row in range(1, max(sheet.max_row, len(rows) + 1) + 1):
            data, values = (empty, cols) if row == 1 else (
                rows[row - 2] if row - 2 < len(rows) else (empty, [])
            )
            if row > 1 and data is not empty and not selected(data, format_filter):
                continue
            for col in range(1, max(sheet.max_column, len(cols)) + 1):
                actual = sheet.cell(row, col)
                raw = export._cell(values[col - 1]) if col <= len(values) else None
                expected = Cell(expected_ws, row=1, column=1, value=raw)
                if expected.data_type == "n" and isinstance(raw, float):
                    raw = float(format(raw, ".16g"))  # openpyxl serialization precision
                if raw == "":
                    raw = None
                field = internal[col - 1] if col <= len(internal) else actual.column_letter
                if raw == actual.value and (raw is None or expected.data_type == actual.data_type):
                    if row > 1 and sheet_name != export.META_SHEET and (problem := cell_problem(field, actual)):
                        audit.add(data, "hard", "H_XLSX_TYPE", field, problem, actual.value,
                                  row=f"{sheet_name}!{actual.coordinate}")
                    continue
                audit.add(data, "hard", "H_XLSX_DIFF", field, raw, actual.value,
                          row=f"{sheet_name}!{actual.coordinate}",
                          note=f"Expected Excel type {expected.data_type}, found {actual.data_type}")
            if sheet_name == export.SUMMARY_SHEET and row > 1 and data is not empty:
                for field, col in (("total_pkg", 2), ("gross_weight_kg", 4)):
                    actual = sheet.cell(row, col)
                    note = data["header"].get("summary_note") or None
                    found = actual.comment.text if actual.comment else None
                    if found != note:
                        audit.add(data, "hard", "H_XLSX_DIFF", field, note, found,
                                  row=f"{sheet_name}!{actual.coordinate}", note="Excel cell note")


def selected(data, filters):
    return not filters or (data["meta"].get("format_id") or "") in filters


def looks_bl_only(header):
    return bool(header.get("bl_no")) and all(
        blank(header.get(field))
        for field in ("invoice_no", "amount", "total_pkg", "gross_weight_kg", "item_line_count")
    )


def is_bl_only(data):
    return data.get("doc_type") == "bl" or data["meta"].get("pair_status") == STATUS_BL_ONLY or (
        data.get("_no_date_column") and not data["items"]
        and looks_bl_only(data["header"]) and not data["meta"].get("format_id")
    )


def history_findings(data):
    # TODO: Add a reviewed, vendor-specific history source for outlier detection.
    return ()


def validate(result_xlsx=None, extracts=None, *, bl_extracts=None, format_filter=None) -> Report:
    """Validate a workbook, JSON extracts, or both. JSON line indices start at 1."""
    if result_xlsx is None and extracts is None:
        raise ValueError("Supply a Result workbook or extract JSON")
    unordered = False
    if extracts is not None:
        if not isinstance(extracts, (str, Path, dict)):
            extracts = list(extracts)
            inputs = extracts
        else:
            inputs = [extracts]
        unordered = any(isinstance(path, (str, Path)) and Path(path).is_dir() for path in inputs)
    data = read_extracts(extracts) if extracts is not None else None
    bills = read_extracts(bl_extracts) if bl_extracts is not None else []
    filters = {format_filter} if isinstance(format_filter, str) else set(format_filter or ())
    with ExitStack() as stack:
        audit = Audit(stack)
        if result_xlsx is not None:
            wb = load_workbook(result_xlsx)
            stack.callback(wb.close)
            if not {export.SUMMARY_SHEET, export.LINES_SHEET}.issubset(wb.sheetnames):
                raise ValueError("Result workbook must have Summary and Lines sheets")
            entries, orphans = workbook_extracts(wb)
            if data is None:
                data = entries
                workbook_checks(audit, wb, entries, orphans, filters)
            else:
                # JSON directories lose the CLI's traversal order. Recover it
                # only when the workbook identifies the same unique source files.
                sources = [d["meta"].get("source_file") for d in entries]
                by_source = {d["meta"].get("source_file"): d for d in data}
                if (unordered and None not in sources and len(set(sources)) == len(sources) == len(data)
                        and set(sources) == set(by_source)):
                    data = [by_source[source] for source in sources]
                compare_workbook(audit, wb, data, filters)
                line_row = 2
                annotated = []
                for row, entry in enumerate(data, 2):
                    annotated.append({
                        **entry, "_summary_row": f"Summary!{row}",
                        "_line_rows": {i + 1: f"Lines!{line_row + i}" for i in range(len(entry["items"]))},
                    })
                    line_row += len(entry["items"])
                data = annotated
        invoices = [d for d in data if not is_bl_only(d)]
        selected_invoices = [d for d in invoices if selected(d, filters)]
        audit.report.invoices_checked = len(selected_invoices)
        groups = defaultdict(list)
        for entry in invoices:
            invoice = entry["header"].get("invoice_no")
            if not blank(invoice):
                groups[str(invoice)].append(entry)
        twins = {}
        for group in groups.values():
            if twin_rows(group):
                left, right = group
                twins.update({id(left): right, id(right): left})
        bills += [d for d in data if is_bl_only(d)]
        for entry in selected_invoices:
            twin = twins.get(id(entry))
            audit.invoice(entry, twin, bills)
            invoice = str(entry["header"].get("invoice_no"))
            if twin:
                audit.add(entry, "warn", "W_TWIN", "invoice_no", "PDF/Excel pair", invoice,
                          note=f"Twin row {twin_label(twin)}")
            elif len(groups[invoice]) > 1:
                audit.add(entry, "hard", "H_DUPLICATE", "invoice_no", "unique", invoice)
            audit.report.findings.extend(history_findings(entry))
        # Include all rows when summing a selected invoice's shipment.
        if filters:
            keys = {d["header"].get("bl_no") for d in selected_invoices} - {None, ""}
            invoices = [d for d in invoices if selected(d, filters) or d["header"].get("bl_no") in keys]
        audit.bill_of_lading(invoices, bills, twins)
        return audit.report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_xlsx", nargs="?", type=Path)
    parser.add_argument("--extract-json", action="append", nargs="+", type=Path)
    parser.add_argument("--bl-json", action="append", nargs="+", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--format-filter", action="append", help="Exact format ID, repeatable or comma-separated")
    args = parser.parse_args(argv)
    try:
        if args.out and any(args.out.resolve() == path.resolve() for path in (
            [args.result_xlsx] * bool(args.result_xlsx)
            + [p for group in args.extract_json or [] for p in group]
            + [p for group in args.bl_json or [] for p in group]
        )):
            raise ValueError("Report output must differ from inputs")
        report = validate(
            args.result_xlsx,
            [p for group in args.extract_json for p in group] if args.extract_json else None,
            bl_extracts=[p for group in args.bl_json or [] for p in group],
            format_filter=[part.strip() for value in args.format_filter or [] for part in value.split(",")],
        )
        if args.out:
            report.write(args.out)
        else:
            sys.stdout.write(report.markdown())
    except (OSError, ValueError, BadZipFile, InvalidFileException) as exc:
        parser.error(str(exc))
    return int(bool(report.counts["hard"]))


if __name__ == "__main__":
    raise SystemExit(main())
