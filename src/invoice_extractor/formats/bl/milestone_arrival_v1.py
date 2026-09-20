"""Milestone Forwarding (里運國際) Taiwan arrival notice — shared MA HBL family.

Samples: ``到貨通知 HBL005094.pdf`` … ``HBL005188.pdf`` under 90-S-26MA-* packs.
Agent: 里運國際 / MILESTONE FORWARDING WORLDWIDE CO., LTD.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta, loose_date_to_iso

MATCH_HINTS = {
    "filename_regex": r"到貨通知|HBL\d{5,}",
    "keywords": [
        "ARRIVAL NOTICE",
        "到貨通知書",
        "MILESTONE FORWARDING",
        "里運國際",
        "B/L",
        "HBL",
    ],
}

NOTES = (
    "Milestone / 里運國際 Taiwan arrival notice (到貨通知書). Shared layout for "
    "HBL00##### MA sea shipments (PORT KLANG → KEELUNG/TAIPEI). "
    "Samples: 到貨通知 HBL005094/5135/5145/5146/5188/5189.pdf (MA inv+bl 6 packs)."
)

RULES_JSON = {
    "id": "milestone_arrival_v1",
    "doc_kind": "arrival_notice",
    "header": {
        "bl_no": r"B/L\s*NO\s*:\s*(HBL\d+)",
        "vessel": r"Ocean Vessel",
        "voyage": r"VOY\.?\s*NO",
        "eta": r"抵港日期",
        "packages": r"(\d+)\s+(?:PALLETS?|PKGS?|PACKAGES?)",
        "gross_weight_kg": r"([\d,.]+)\s*KGS",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename
    if "到貨" in fn or re.search(r"HBL\d{5,}", fn, re.I):
        score += 0.2
    if "ARRIVAL NOTICE" in text or "到貨通知書" in text:
        score += 0.25
    if "MILESTONE FORWARDING" in text or "里運國際" in text:
        score += 0.35
    if re.search(r"B/L\s*NO\s*:\s*HBL\d+", text, re.I):
        score += 0.25
    if "CEVA LOGISTICS" in text or "PYRAMID LINES" in text:
        score -= 0.6
    if "DHL GLOBAL FORWARDING" in text or "海運 LCL 到貨通知" in text:
        score -= 0.6
    if "HIPPOPO" in text.upper():
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def _left_col(line: str) -> str:
    """Keep left column of a two-column arrival-notice layout line."""
    parts = re.split(r"[^\S\n]{2,}", line.strip())
    parts = [p for p in parts if p]
    if not parts:
        return ""
    left = parts[0]
    if left.startswith(":"):
        left = left[1:].strip()
    # drop right-side B/L / ARRIVAL crumbs if somehow joined
    left = re.split(r"\bB/L\b|ARRIVAL NOTICE|里運國際|MILESTONE", left, maxsplit=1)[0].strip()
    return left


def _block_after(label: str, text: str, *, max_lines: int = 4) -> str | None:
    """Collect up to max_lines of left-column content after a label line."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if re.match(rf"^\s*{re.escape(label)}\b", ln, re.I):
            parts: list[str] = []
            for j in range(i + 1, min(i + 1 + max_lines + 3, len(lines))):
                raw = lines[j]
                if not raw.strip():
                    if parts:
                        break
                    continue
                if re.match(
                    r"^\s*(Consignee|Notify|Shipper|Ocean Vessel|Port of Loading|"
                    r"Marks and Numbers|1st Vessel)\b",
                    raw,
                    re.I,
                ):
                    break
                left = _left_col(raw)
                if not left:
                    continue
                parts.append(left)
                if len(parts) >= max_lines:
                    break
            return " ".join(parts) if parts else None
    return None


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="Milestone Forwarding (里運國際)", load_type="FCL")

    m = re.search(r"B/L\s*NO\s*:\s*(HBL\d+)", text, re.I)
    if m:
        h.bl_no = m.group(1).upper()
        h.hbl_no = h.bl_no

    # Vessel / voyage: line after "Ocean Vessel ... VOY.NO." headers
    m = re.search(
        r"Ocean Vessel\s+VOY\.?\s*NO\.?[^\n]*\n\s*([A-Z0-9][A-Z0-9 \-/]*?)\s{2,}([A-Z]?\d{2,4})\b",
        text,
        re.I,
    )
    if m:
        h.vessel = m.group(1).strip()
        h.voyage = m.group(2).strip()
    else:
        # fallback: first vessel-like token near Ocean Vessel block
        m = re.search(
            r"Ocean Vessel.{0,80}?\n\s*([A-Z][A-Z0-9 ]{2,}?)\s{2,}(N\d{2,4}|\d{3,4}[A-Z]?)\b",
            text,
            re.I | re.S,
        )
        if m:
            h.vessel = re.sub(r"\s+", " ", m.group(1)).strip()
            h.voyage = m.group(2).strip()

    m = re.search(
        r"Port of Loading\s+Port of Discharge\s+Port of Delivery\s+抵港日期\s*\n"
        r"\s*([A-Z][A-Z0-9 ]*?)\s{2,}([A-Z][A-Z0-9 ]*?)\s{2,}([A-Z][A-Z0-9 ]*?)\s{2,}([\d/]+)",
        text,
        re.I,
    )
    if m:
        h.pol = m.group(1).strip()
        h.pod = m.group(2).strip()
        h.eta = loose_date_to_iso(m.group(4).strip())
    else:
        m = re.search(r"抵港日期\s*\n?[^\n]*?(\d{4}/\d{1,2}/\d{1,2})", text)
        if m:
            h.eta = loose_date_to_iso(m.group(1))
        m = re.search(r"Port of Loading.{0,120}?PORT KLANG", text, re.I | re.S)
        if m:
            h.pol = "PORT KLANG"
        m = re.search(r"Port of Discharge.{0,80}?(TAIPEI|KEELUNG)", text, re.I | re.S)
        if m:
            h.pod = m.group(1).upper()

    # Cargo row: container / size / seal … N UNIT … GW KGS … CBM
    m = re.search(
        r"(?P<ctr>[A-Z]{4}\d{7})\s*/\s*(?P<size>\d+['′]?(?:CY|HQ|GP|HC)?)\s*/\s*"
        r"(?P<seal>\S+)\s+"
        r"(?P<pkg>\d+)\s+(?P<unit>PALLETS?|PKGS?|PACKAGES?)\s+"
        r"(?P<gw>[\d,.]+)\s*KGS\s+(?P<cbm>[\d,.]+)\s*CBM",
        text,
        re.I,
    )
    if m:
        h.container_nos = m.group("ctr").upper()
        h.packages = float(m.group("pkg"))
        unit = m.group("unit").upper()
        if unit.startswith("PALLET"):
            h.package_unit = "PALLET"
        elif unit.startswith("PKG"):
            h.package_unit = "PKG"
        else:
            h.package_unit = "PACKAGE"
        h.gross_weight_kg = us_float(m.group("gw"))
        h.measurement_cbm = us_float(m.group("cbm"))
        if "40" in m.group("size") or "20" in m.group("size"):
            h.load_type = "FCL"

    # Invoice refs (may be commercial INV or MA Document No.)
    refs: list[str] = []
    for rm in re.finditer(
        r"INVOICE\s*(?:NO\.?\s*:?|:)?\s*([0-9,\s]+)",
        text,
        re.I,
    ):
        chunk = rm.group(1)
        for num in re.findall(r"\d{6,12}", chunk):
            if num not in refs:
                refs.append(num)

    # AK Billing Document refs (MA AK family)
    for rm in re.finditer(r"\b(AK\d{8})\b", text):
        if rm.group(1) not in refs:
            refs.append(rm.group(1))

    if refs:
        h.invoice_refs = ", ".join(refs)

    shipper = _block_after("Shipper", text, max_lines=3)
    if shipper:
        h.shipper = _snip(shipper, 100)
    consignee = _block_after("Consignee", text, max_lines=3)
    if consignee:
        h.consignee = _snip(consignee, 100)
    notify = _block_after("Notify", text, max_lines=2)
    if notify and "SAME AS" not in notify.upper():
        h.notify = _snip(notify, 80)
    elif notify:
        h.notify = "SAME AS CONSIGNEE"

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="milestone_arrival_v1",
            confidence="rules",
            needs_ocr=needs_ocr,
            doc_kind="arrival_notice",
            notes=NOTES if not h.bl_no else None,
        ),
    )
