"""BHC vendor commercial invoice family v1 (layout family, one format_id).

Small Asian vendors that ship to Bosch Home Comfort Taiwan with a plain
"COMMERCIAL INVOICE" table (PO / Bosch PN / vendor code / qty / unit price /
amount + TOTAL row) and a packing list either in the same file or split.
Instead of one ``format_id`` per vendor (user 2026-10: prefer ~8–15 layout
families), each vendor is a *profile* inside this module; ``meta.notes``
records ``profile=<name>``.

Profiles (BHC 4th batch, 2026-10-05):

- ``sanhua``      浙江三花 ZHEJIANG SANHUA — ``SHC-THT2609029客户资料.pdf`` + ``.xls``
                  twin (INV + PL sheets). Groups ``DESCRIPTION OF GOODS: … H.S
                  CODE:##########`` give HS for the rows below. PN = CUSTOMERS
                  NO. (Bosch ``3EF59091A``); the PDF can leave it blank (row
                  P10062198-30) while the .xls has it → PN None + note.
                  pkg = ``8托PLTS`` (pallets), GW = ``G.W毛重: 3,185.00``.
- ``welling``     GUANGDONG WELLING MOTOR / WELLING INTERNATIONAL HK —
                  ``CI PL MDBWHTWJCH260915.pdf`` (INV + PL). PN = 2nd column
                  (``2NA09101Z``); pkg/GW = PL ``TOTAL: 63 CTNS … 28972.8``.
- ``broad_ocean`` BROAD-OCEAN MOTOR (HONGKONG) 大洋 — ``COMMERCIAL_INVOICE
                  BHC-TW 2026-09-23.xls`` + split ``PACKING LIST … .xls``.
                  PN = ``2NA39372A / DC MOTOR …``; PL ``1-7  7  7 …`` (pallets,
                  cartons) + ``TOTAL qty NW GW CBM``.
- ``hipus``       HIPUS Co., Ltd. — ``IV_117-BHCTW-26K-41.PDF`` (+ .xlsx twin,
                  Header/Detail sheets); 2-line rows (PO / Code / vendor code /
                  desc, then COO / qty / JPY price / JPY amount). One shared
                  ``PL_117-…, 121-….xlsx`` for two invoices: pallets are keyed
                  as packing units so the shipment total goes on the first
                  invoice and the other gets 0 (``pairing.dedupe_shared_packing_units``,
                  same mode B as MA 2026-09-29).
- ``hailiang``    HONGKONG HAILIANG METAL TRADING 海亮 — ``26HLHK01Q10009B-
                  发票箱单.xlsx`` (invoice + packing list sheets). Copper coil
                  priced per KG; PN = PO NO (``P100592670060``, same idea as
                  Marubeni copper S/N); pkg = PACKAGES column of the PL TOTAL.

Only Result fields are extracted (no vessel / ETD / CBM / container).
BHC: missing HS is soft.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, en_date_to_iso, us_float

MATCH_HINTS = {
    "filename_regex": r"SHC-THT|MDBWH|BHC-TW|BHCTW|HLHK",
    "keywords": [
        "ZHEJIANG SANHUA INTELLIGENT CONTROLS",
        "WELLING INTERNATIONAL HONG KONG",
        "BROAD-OCEAN MOTOR",
        "HIPUS Co",
        "HAILIANG METAL TRADING",
    ],
}

NOTES = (
    "BHC vendor CI family (profiles sanhua / welling / broad_ocean / hipus / hailiang). "
    "Labeled TOTAL amount drives the hard check; PN = Bosch customer PN column "
    "(hailiang: PO NO). pkg/GW from the PL TOTAL (combined or split PKL via "
    "parse_packing). HIPUS shared PL → packing_units per pallet (shipment total on "
    "first invoice). BHC 4th batch 2026-10-05."
)

RULES_JSON = {
    "id": "bhc_vendor_ci_v1",
    "profiles": ["sanhua", "welling", "broad_ocean", "hipus", "hailiang"],
}

_BOSCH_PN = re.compile(r"\b(\d[A-Z]{2}\d{5}[A-Z])\b")
_NOT_INVOICE = re.compile(
    r"B/L\s*NO|BILL\s+OF\s+LADING|到貨通知|ARRIVAL\s+NOTICE|WAYBILL|SEA\s+WAYBILL",
    re.I,
)

_PROFILE_ANCHORS: list[tuple[str, re.Pattern[str]]] = [
    ("sanhua", re.compile(r"ZHEJIANG\s+SANHUA|浙江三花", re.I)),
    ("welling", re.compile(r"WELLING\s+(?:INTERNATIONAL|MOTOR)|GUANGDONG\s+WELLING", re.I)),
    ("broad_ocean", re.compile(r"BROAD-?\s?OCEAN\s+MOTOR", re.I)),
    ("hipus", re.compile(r"\bHIPUS\s+Co|^No\.\t\d{3}-BHCTW-\d{2}[A-Z]-\d{2}\b", re.I | re.M)),
    ("hailiang", re.compile(r"HAILIANG\s+METAL", re.I)),
]


def _profile(text: str) -> Optional[str]:
    for name, rx in _PROFILE_ANCHORS:
        if rx.search(text or ""):
            return name
    return None


def match_score(text: str, filename: str = "") -> float:
    prof = _profile(text)
    if not prof:
        return 0.0
    score = 0.6
    tu = (text or "").upper()
    if "COMMERCIAL INVOICE" in tu or re.search(r"(?m)^\s*INVOICE\s*$", tu) or "=== SHEET: INVOICE" in tu:
        score += 0.2
    if re.search(r"SHC-THT|MDBWH|BHC-?TW|HLHK", filename or "", re.I):
        score += 0.1
    if _NOT_INVOICE.search(text or ""):
        score -= 0.6
    return max(0.0, min(score, 0.95))


# --------------------------------------------------------------------------- helpers

def _num(s: str | None) -> Optional[float]:
    if s is None:
        return None
    s = s.strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _r2(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, 4 if abs(x - round(x, 2)) > 1e-6 and abs(x) < 100 else 2)


def _money(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, 2)


def _incoterm(text: str) -> Optional[str]:
    m = re.search(r"\b(FOB|CIF|CFR|CIP|EXW|FCA|DAP|DDP)\s+([A-Z][A-Za-z]{3,15})\b", text)
    if m and m.group(2).upper() not in {"USD", "JPY", "DAYS", "THE"}:
        return f"{m.group(1)} {m.group(2)}"
    return None


_COUNTRY = {
    "CHINA": "China", "JAPAN": "Japan", "VIET NAM": "Viet Nam", "VIETNAM": "Viet Nam",
    "MALAYSIA": "Malaysia", "THAILAND": "Thailand", "SOUTH KORE": "South Korea",
    "SOUTH KOREA": "South Korea", "KOREA": "South Korea", "TAIWAN": "Taiwan",
    "INDONESIA": "Indonesia", "PHILIPPINES": "Philippines",
}


def _country(s: str | None) -> Optional[str]:
    if not s:
        return None
    return _COUNTRY.get(re.sub(r"\s+", " ", s.strip()).upper(), s.strip())


def _split_cols(line: str) -> list[str]:
    if "\t" in line:
        return [c.strip() for c in line.split("\t") if c.strip()]
    return [c.strip() for c in re.split(r"\s{2,}", line.strip()) if c.strip()]


class _Out:
    def __init__(self) -> None:
        self.invoice_no: Optional[str] = None
        self.invoice_date: Optional[str] = None
        self.items: list[Item] = []
        self.amount: Optional[float] = None
        self.labeled: Optional[float] = None
        self.label: Optional[str] = None
        self.total_qty: Optional[float] = None
        self.currency = "USD"
        self.incoterm: Optional[str] = None
        self.vendor: Optional[str] = None
        self.origin: Optional[str] = None
        self.pkg: Optional[float] = None
        self.gw: Optional[float] = None
        self.units: Optional[dict[str, float]] = None
        self.notes: list[str] = []
        self.gold_fields: list[str] = []


# --------------------------------------------------------------------------- packing parsers
# Each returns (pkg, gw, units|None, note|None). Used for the combined PL part and
# for split PKL overlay (pairing calls ``parse_packing``).

def _pack_sanhua(text: str):
    m = re.search(r"TOTAL\s+[\d,]+\s*PCS\s+PACKED\s+IN\s+(\d+)\s*箱?\s*CTNS?\s+(\d+)\s*托?\s*PLTS?", text, re.I)
    pkg = float(m.group(2)) if m else None
    note = f"PL: {m.group(1)} CTNS on {m.group(2)} PLTS → pkg = pallets" if m else None
    g = re.search(r"G\.?\s*W[^\n:：]*[:：]\s*([\d,]+(?:\.\d+)?)", text[m.end():] if m else text)
    gw = _num(g.group(1)) if g else None
    return pkg, gw, None, note


def _pack_welling(text: str):
    m = re.search(
        r"(?m)^\s*TOTAL:?\s+(\d+)\s+CTNS?\s+[\d,]+\s+([\d,.]+)\s+([\d,.]+)\s+[\d,.]+",
        text,
    )
    if not m:
        return None, None, None, None
    return float(m.group(1)), _num(m.group(3)), None, None


def _pack_broad_ocean(text: str):
    pk = text
    if "PACKING LIST" in text.upper():
        pk = text[text.upper().index("PACKING LIST"):]
    pallets = 0
    cartons = 0
    for m in re.finditer(r"(?m)^\s*\d+\s*-\s*\d+\t(\d+)\t(\d+)\t", pk):
        pallets += int(m.group(1))
        cartons += int(m.group(2))
    m_t = re.search(r"(?m)^\s*TOTAL\t[\d.]+\t([\d.]+)\t([\d.]+)\t[\d.]+", pk)
    gw = _num(m_t.group(2)) if m_t else None
    m_say = re.search(r"SAY\s+TOTAL\s*\(?\s*(\d+)\s*\)?\s*(CARTONS?|PALLETS?|PLTS?|PKGS?)", pk, re.I)
    pkg = float(pallets) if pallets else (float(m_say.group(1)) if m_say else None)
    note = None
    if pallets and m_say and int(m_say.group(1)) != pallets:
        note = f"PL pallets {pallets} vs SAY TOTAL {m_say.group(1)} {m_say.group(2)}"
    elif pallets:
        note = f"PL {pallets} pallets / {cartons} cartons"
    return pkg, gw, None, note


def _pack_hipus(text: str):
    """Shared PL attached sheet: ``1\\t1\\tPALLET\\t3BS37439A … 327.5\\t335.5\\t1.573\\t121-…``."""
    units: dict[str, float] = {}
    for m in re.finditer(
        r"(?m)^(\d{1,3})\t1\tPALLET\t[^\n]*?\tPCS\t([\d.]+)\t([\d.]+)\t([\d.]+)\t",
        text,
    ):
        units[f"PALLET-{int(m.group(1))}"] = float(m.group(3))
    m_t = re.search(r"(?m)^(\d+)\tPALLETS?\tTOTAL\t[\d.]+\tPCS\t([\d.]+)\t([\d.]+)", text)
    pkg = float(m_t.group(1)) if m_t else (float(len(units)) if units else None)
    gw = float(m_t.group(3)) if m_t else (round(sum(units.values()), 3) if units else None)
    note = None
    if units and (len(units) != pkg or abs(sum(units.values()) - (gw or 0)) > 0.01):
        note = f"PL pallet rows {len(units)} / {sum(units.values()):g} ≠ TOTAL {pkg} / {gw}"
        units = {}
    refs = re.search(r"Attached sheet for Inv\.?No\.?\s*([^\n]+)", text, re.I)
    if refs and "," in refs.group(1):
        note = (note + "; " if note else "") + f"one PL for {refs.group(1).strip()}"
    return pkg, gw, (units or None), note


def _pack_hailiang(text: str):
    pk = text.split("=== Sheet: packing list ===", 1)[-1]
    m = re.search(r"(?m)^TOTAL:?\t(\d+)\t(\d+)\t([\d.]+)\t([\d.]+)\t([\d.]+)", pk)
    if not m:
        return None, None, None, None
    note = (
        f"PL TOTAL row has two counts: {m.group(1)} (under a stale column, labeled "
        f"PACKAGES below) and {m.group(2)} (PACKAGES column header / PKGS) → pkg = {m.group(2)}"
    )
    return float(m.group(2)), _num(m.group(4)), None, note


_PACKERS: dict[str, Callable] = {
    "sanhua": _pack_sanhua,
    "welling": _pack_welling,
    "broad_ocean": _pack_broad_ocean,
    "hipus": _pack_hipus,
    "hailiang": _pack_hailiang,
}


def parse_packing(text: str) -> Optional[dict]:
    """Split-PKL overlay hook for ``pairing``: ``{pkg, gw, units, note}`` or None."""
    prof = _profile(text)
    if not prof:
        return None
    pkg, gw, units, note = _PACKERS[prof](text)
    if pkg is None and gw is None:
        return None
    return {"pkg": pkg, "gw": gw, "units": units, "note": note, "profile": prof}


# --------------------------------------------------------------------------- invoice profiles

def _inv_sanhua(text: str, o: _Out) -> None:
    o.vendor = "ZHEJIANG SANHUA INTELLIGENT CONTROLS CO.,LTD."
    m = re.search(r"Inv\s*No\.?\s*:?\s*(SHC/[A-Z0-9]+)", text, re.I)
    o.invoice_no = m.group(1).upper() if m else None
    m = re.search(r"Invoice\s+Date:?\s*([A-Za-z]{3,9})\.?\s*(\d{1,2}),\s*(\d{4})", text, re.I)
    if m:
        o.invoice_date = en_date_to_iso(f"{m.group(1)} {m.group(2)}, {m.group(3)}")
    inv_part = re.split(r"\bPACKING\s+LIST\b|=== Sheet: 报关箱单", text, maxsplit=1)[0]
    if re.search(r"MADE\s+IN\s+CHINA", text, re.I):
        o.origin = "China"
    hs = None
    desc = None
    blank_pn = []
    for line in inv_part.splitlines():
        g = re.search(r"DESCRIPTION OF GOODS:\s*[^\n(]*\((.+)\)\s*H\.?S\.?\s*CODE:?\s*(\d{6,10})", line, re.I)
        if g:
            desc, hs = re.sub(r"\s+", " ", g.group(1)).strip(), g.group(2)
            continue
        if not re.match(r"\s*P\d{8}-\d{2}\b", line):
            continue
        cols = _split_cols(line)
        nums = [c for c in cols if re.fullmatch(r"[\d,]+(?:\.\d+)?", c)]
        if len(nums) < 3:
            continue
        qty, price, amt = (_num(x) for x in nums[-3:])
        po = cols[0]
        pn_m = _BOSCH_PN.search(" ".join(cols[1:-3]))
        pn = pn_m.group(1) if pn_m else None
        extra = None
        if pn_m:
            rest = " ".join(cols[1:-3]).replace(pn, "", 1).strip()
            # "3EF59091A 4.5W" → keep "4.5W" with the description; vendor code dropped
            w = re.match(r"([\d.]+W)\b", rest)
            extra = w.group(1) if w else None
        else:
            blank_pn.append(po)
        o.items.append(
            Item(
                invoice_no=o.invoice_no,
                part_no=pn,
                description=(f"{desc} {extra}" if extra else desc),
                qty=qty,
                unit="PCS",
                unit_price=price,
                amount=_money(amt),
                origin=o.origin,
                hs_code=hs,
                currency="USD",
            )
        )
    if blank_pn:
        o.notes.append(
            "CUSTOMERS NO. (Bosch PN) blank on this document for " + ", ".join(blank_pn)
            + " — check the .xls twin / figure"
        )
    m = re.search(r"TOTAL:?\s*\t?\s*(\d[\d,]*)\s*PCS[^\n]*?TOTAL:?\s*([\d,]+\.?\d*)", inv_part, re.I)
    if m:
        o.total_qty = _num(m.group(1))
        o.labeled = _money(_num(m.group(2)))
        o.label = "TOTAL"
    m = re.search(r"\b(FOB|CIF|CFR|EXW|FCA)\s+(SHANGHAI|NINGBO|[A-Z]{4,12})\b", inv_part)
    o.incoterm = f"{m.group(1)} {m.group(2)}" if m else None
    o.pkg, o.gw, _, note = _pack_sanhua(text[len(inv_part):])
    if note:
        o.notes.append(note)


def _inv_welling(text: str, o: _Out) -> None:
    o.vendor = "WELLING INTERNATIONAL HONG KONG LIMITED"
    m = re.search(r"INVOICE\s+NO\.?\s*:?\s*([A-Z0-9-]{6,})", text, re.I)
    o.invoice_no = m.group(1).upper() if m else None
    m = re.search(r"DATE\s*:?\s*(\d{1,2}/[A-Za-z]{3}/\d{2,4})", text, re.I)
    o.invoice_date = m.group(1) if m else None
    inv_part = re.split(r"\bPACKING\s+LIST\b", text, maxsplit=1)[0]
    desc = "DC MOTOR" if re.search(r"\bDC\s+MOTOR\b", inv_part) else None
    for line in inv_part.splitlines():
        m = re.match(
            r"\s*(?P<po>P\d{9,13})\s+(?P<pn>\d[A-Z]{2}\d{5}[A-Z])\s+(?P<vpn>\S+)\s+"
            r"(?P<qty>[\d,]+)\s+(?P<price>[\d.]+)\s+(?P<amt>[\d,.]+)\s*(?P<cn>\S*)\s*$",
            line,
        )
        if not m:
            continue
        o.items.append(
            Item(
                invoice_no=o.invoice_no,
                part_no=m.group("pn"),
                description=desc,
                qty=_num(m.group("qty")),
                unit="PCS",
                unit_price=_num(m.group("price")),
                amount=_money(_num(m.group("amt"))),
                currency="USD",
            )
        )
    m = re.search(r"(?m)^\s*TOTAL:?\s+([\d,]+)\s+([\d,]+(?:\.\d+)?)\s*$", inv_part)
    if m:
        o.total_qty = _num(m.group(1))
        o.labeled = _money(_num(m.group(2)))
        o.label = "TOTAL"
    o.incoterm = _incoterm(inv_part)
    o.notes.append("origin not printed on CI (exporter Guangdong, CN) — Co left blank")
    o.pkg, o.gw, _, _ = _pack_welling(text[len(inv_part):])


def _inv_broad_ocean(text: str, o: _Out) -> None:
    o.vendor = "BROAD-OCEAN MOTOR(HONGKONG) CO., Ltd."
    m = re.search(r"INVOICE\s+NO\.?\s*:?\s*\n?\s*([0-9A-Z][0-9A-Z-]{5,})", text, re.I)
    o.invoice_no = m.group(1).upper() if m else None
    m = re.search(r"DATE:?\s*\n?\s*(\d{4}-\d{2}-\d{2})", text, re.I)
    o.invoice_date = m.group(1) if m else None
    if re.search(r"COUNTRY\s+OF\s+ORIGIN\s+CHINA", text, re.I):
        o.origin = "China"
    for m in re.finditer(
        r"(?P<pn>\d[A-Z]{2}\d{5}[A-Z])\s*/\s*(?P<desc>[^\n\t]+)\n(?P<desc2>[^\t\n]*)\t"
        r"(?P<qty>[\d.]+)\t(?P<price>[\d.]+)\t(?P<amt>[\d.]+)(?:\t(?P<po>P\d+))?",
        text,
    ):
        d = re.sub(r"\s+", " ", f"{m.group('desc')} {m.group('desc2')}").strip()
        o.items.append(
            Item(
                invoice_no=o.invoice_no,
                part_no=m.group("pn"),
                description=d,
                qty=_num(m.group("qty")),
                unit="PCS",
                unit_price=_num(m.group("price")),
                amount=_money(_num(m.group("amt"))),
                origin=o.origin,
                currency="USD",
            )
        )
    m = re.search(r"(?m)^\s*TOTAL\t([\d.]+)\t([\d.]+)\s*$", text)
    if m:
        o.total_qty = _num(m.group(1))
        o.labeled = _money(_num(m.group(2)))
        o.label = "TOTAL"
    m = re.search(r"Incoterm:?\s*\n*\s*((?:FOB|CIF|CFR|EXW|FCA|DAP)\s+[A-Za-z]+)", text, re.I)
    o.incoterm = m.group(1).strip() if m else _incoterm(text)
    if "PACKING LIST" in text.upper():
        o.pkg, o.gw, _, note = _pack_broad_ocean(text)
        if note:
            o.notes.append(note)


_HIPUS_ROW_A = re.compile(r"^\s*(?P<idx>\d{1,3})\s+(?P<rest>\S.*?)\s*$")
_HIPUS_ROW_B = re.compile(
    r"^\s*(?P<coo>[A-Za-z][A-Za-z .]*?)\s+(?P<qty>[\d,]+)\s*(?P<unit>PCS|PC|SET|KG|M)\s+"
    r"JPY(?P<price>[\d,]+(?:\.\d+)?)\s+JPY(?P<amt>[\d,]+)\.-\s*$"
)


def _inv_hipus_pdf(text: str, o: _Out) -> None:
    lines = text.splitlines()
    for i, line in enumerate(lines[:-1]):
        a = _HIPUS_ROW_A.match(line)
        b = _HIPUS_ROW_B.match(lines[i + 1]) if a else None
        if not (a and b):
            continue
        toks = a.group("rest").split()
        codes = []
        for t in toks:
            if re.search(r"\d", t) and len(codes) < 3:
                codes.append(t)
            else:
                break
        if len(codes) < 2:
            continue
        pn = codes[1]
        desc = " ".join(toks[len(codes):]) or None
        o.items.append(
            Item(
                invoice_no=o.invoice_no,
                part_no=pn,
                description=desc,
                qty=_num(b.group("qty")),
                unit="PCS" if b.group("unit").upper().startswith("PC") else b.group("unit").upper(),
                unit_price=_num(b.group("price")),
                amount=_num(b.group("amt")),
                origin=_country(b.group("coo")),
                currency="JPY",
            )
        )
    m = re.search(r"TOTAL:\s*([\d,]+)\s*PCS\s+JPY([\d,]+)\.-", text)
    if m:
        o.total_qty = _num(m.group(1))
        o.labeled = _num(m.group(2))
        o.label = "TOTAL"


def _inv_hipus_xlsx(text: str, o: _Out) -> None:
    """Detail sheet (database export): ``… qty\\tPC\\t1\\tprice\\tamt\\t0\\tamt\\t…``."""
    detail = text.split("=== Sheet: Detail ===", 1)[-1]
    countries = "|".join(sorted({re.escape(k.title()) for k in _COUNTRY} | {"Viet Nam", "South Korea"}, key=len, reverse=True))
    for line in detail.splitlines():
        m = re.search(r"\t(?P<qty>\d+(?:\.\d+)?)\tPCS?\t1\t(?P<price>\d+(?:\.\d+)?)\t(?P<amt>\d+(?:\.\d+)?)\t0\t(?P=amt)\t", line)
        if not m:
            continue
        cells = [c for c in line.split("\t")]
        pn = cells[1] if len(cells) > 1 and re.search(r"\d", cells[1]) else cells[0]
        idx = cells.index(pn)
        desc = cells[idx + 1] if idx + 1 < len(cells) else None
        mc = re.search(rf"\t({countries})\t", line)
        o.items.append(
            Item(
                invoice_no=o.invoice_no,
                part_no=pn,
                description=desc,
                qty=_num(m.group("qty")),
                unit="PCS",
                unit_price=_num(m.group("price")),
                amount=_num(m.group("amt")),
                origin=_country(mc.group(1)) if mc else None,
                currency="JPY",
            )
        )
    if o.items:
        o.labeled = sum(it.amount or 0 for it in o.items)
        o.label = "sum(lines) (xlsx twin; no TOTAL row)"
        o.notes.append("xlsx twin: no TOTAL row — cross-check against the PDF")


def _inv_hipus(text: str, o: _Out) -> None:
    o.vendor = "HIPUS Co., Ltd."
    o.currency = "JPY"
    m = re.search(r"\bNo\.?\s*\t?\s*(\d{3}-[A-Z]{3,8}-\d{2}[A-Z]-\d{2})", text)
    o.invoice_no = m.group(1) if m else None
    m = re.search(r"Date\.?\s*\t?\s*([A-Za-z]+\s+\d{1,2},\s*\d{4}|\d{4}/\d{2}/\d{2})", text)
    if m:
        d = m.group(1)
        o.invoice_date = d.replace("/", "-") if "/" in d else en_date_to_iso(d)
    m = re.search(r"TradeTerms\s*(?:\t|\n[^\n]*?)\s*\b(FOB|CIF|CFR|EXW|FCA|DAP|DDP)\b", text)
    o.incoterm = m.group(1) if m else None
    if "=== Sheet: Detail ===" in text:
        _inv_hipus_xlsx(text, o)
    else:
        _inv_hipus_pdf(text, o)


def _inv_hailiang(text: str, o: _Out) -> None:
    o.vendor = "HONGKONG HAILIANG METAL TRADING LIMITED"
    inv_sheet = text.split("=== Sheet: packing list ===", 1)[0]
    m = re.search(r"\b(\d{2}HLHK\d{2}[A-Z]\d{5}[A-Z]?)\b", inv_sheet)
    o.invoice_no = m.group(1) if m else None
    m_pl = re.search(r"INVOICE\s+NO\.?:?\s*([0-9A-Z]{8,})", text, re.I)
    if m_pl and o.invoice_no and m_pl.group(1) != o.invoice_no:
        o.notes.append(
            f"invoice no {o.invoice_no} (invoice sheet / PL header / filename); PL also prints "
            f"'INVOICE NO.: {m_pl.group(1)}' (looks like template residue) — confirm"
        )
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s+00:00:00", inv_sheet)
    o.invoice_date = m.group(1) if m else None
    if re.search(r"MADE\s+IN\s+CHINA", text, re.I):
        o.origin = "China"
    desc0 = "REFINED COPPER COIL" if "REFINED COPPER COIL" in inv_sheet.upper() else None
    for m in re.finditer(
        r"(?m)^(?P<po>P\d{9,13})\t(?P<spec>[^\t\n]+)\t(?P<qty>[\d.]+)\t(?P<price>[\d.]+)\t(?P<amt>[\d.]+)\s*$",
        inv_sheet,
    ):
        o.items.append(
            Item(
                invoice_no=o.invoice_no,
                part_no=m.group("po"),
                description=f"{desc0} {m.group('spec')}".strip() if desc0 else m.group("spec"),
                qty=_num(m.group("qty")),
                unit="KGS",
                unit_price=_num(m.group("price")),
                amount=_money(_num(m.group("amt"))),
                origin=o.origin,
                currency="USD",
            )
        )
    m = re.search(r"(?m)^TOTAL:?\s*\t[^\t\n]*\t([\d.]+)\t([\d.]+)\s*$", inv_sheet)
    if m:
        o.total_qty = _num(m.group(1))
        o.labeled = _money(_num(m.group(2)))
        o.label = "TOTAL"
    o.incoterm = _incoterm(inv_sheet)
    o.notes.append("PN = PO NO (no Bosch PN printed; copper priced per KG)")
    o.pkg, o.gw, _, note = _pack_hailiang(text)
    if note:
        o.notes.append(note)


_INVOICERS: dict[str, Callable[[str, _Out], None]] = {
    "sanhua": _inv_sanhua,
    "welling": _inv_welling,
    "broad_ocean": _inv_broad_ocean,
    "hipus": _inv_hipus,
    "hailiang": _inv_hailiang,
}


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    prof = _profile(text)
    o = _Out()
    if prof:
        _INVOICERS[prof](text, o)
    for it in o.items:
        it.invoice_no = o.invoice_no
    sum_lines = round(sum(it.amount or 0 for it in o.items), 2) if o.items else None
    amount = o.labeled if o.labeled is not None else sum_lines
    if o.total_qty is None and o.items:
        o.total_qty = float(sum(it.qty or 0 for it in o.items))
    header = Header(
        invoice_no=o.invoice_no,
        invoice_date=o.invoice_date,
        total_pkg=o.pkg,
        gross_weight_kg=o.gw,
        incoterm=o.incoterm,
        item_line_count=len(o.items) if o.items else None,
        total_quantity=o.total_qty,
        amount=amount,
        currency=o.currency,
        vendor=o.vendor,
        origin=o.origin,
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="bhc_vendor_ci_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=o.labeled if o.labeled is not None else sum_lines,
        labeled_amount_label=o.label or "sum(lines)",
        source="combined" if (o.pkg is not None or o.gw is not None) else None,
        notes="; ".join([f"profile={prof}"] + o.notes) if prof else None,
    )
    if o.gold_fields:
        meta.needs_gold_fields = list(o.gold_fields)
    if not o.invoice_no or amount is None or not o.items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=o.items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(text, source_file=path, text_backend=backend, needs_ocr=needs_ocr)
