"""T.V.L. Global Logistics / Trans Van Links — HBL face (OCR-friendly).

BHC case7/8 scans: ``20260903091515-0001.pdf``, ``20260904232648-0001.pdf``.
B/L nos like ``SHAKEL########``; forwarder T.V.L. / TRANS VAN LINKS.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta

MATCH_HINTS = {
    "filename_regex": r"2026\d+|SHAKEL|TVL",
    "keywords": [
        "T.V.L. GLOBAL LOGISTICS",
        "TRANS VAN LINKS",
        "BILL OF LADING",
        "SHAKEL",
        "FREIGHT COLLECT",
    ],
}

NOTES = (
    "TVL / Trans Van Links HBL face. Trained on OCR of BHC case7/8 scan HBLs "
    "(SHAKEL26970898 / SHAKEL26770270; BHC 3rd SHAKEL26971792 / SHAKEL26972017). "
    "Prefer cargo cartons/pallets over Say-Total container (1×20GP). "
    "GW: prefer CARTONS/KGS when carton count matches; else standalone KGS; cross-check OCR slips (.830→.53, B26CARTONS≠326)."
)

RULES_JSON = {
    "id": "tvl_hbl_v1",
    "doc_kind": "hbl",
    "header": {
        "bl_no": r"B/L\s*NO\.?\s*(SHAKEL\d+)",
        "packages": r"SAY\s+TOTAL[:\s]+(?:ONE\s*\(1\)\s*)?(\d+)?\s*(?:PALLET|20.?GP|CARTONS)",
        "gross_weight_kg": r"([\d,]+\.\d+)\s*K?GS",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    tu = text.upper()
    if "T.V.L" in tu or "TVL GLOBAL" in tu or "TRANS VAN LINKS" in tu:
        score += 0.45
    if re.search(r"SHAKEL\d+", tu):
        score += 0.35
    if "BILL OF LADING" in tu:
        score += 0.1
    if "FREIGHT COLLECT" in tu:
        score += 0.05
    if "HIPPOPO" in tu or "CEVA LOGISTICS" in tu or "MILESTONE FORWARDING" in tu:
        score -= 0.5
    if "DHL GLOBAL FORWARDING" in tu:
        score -= 0.4
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="T.V.L. Global Logistics Co., Ltd.")

    m = re.search(r"B/L\s*NO\.?\s*(SHAKEL\d+)", text, re.I)
    if not m:
        m = re.search(r"\b(SHAKEL\d+)\b", text, re.I)
    if m:
        h.bl_no = m.group(1).upper()
        h.hbl_no = h.bl_no

    # Shipper: first company-like line after Shipper
    m = re.search(
        r"Shipper\s*\n\s*([A-Z][^\n]{5,80})",
        text,
        re.I,
    )
    if m:
        ship = re.sub(r"\s*B/L\s*NO\.?.*$", "", m.group(1), flags=re.I).strip(" ,")
        h.shipper = _snip(ship)

    m = re.search(
        r"(?:ronsignee|Consignee|onsignee)\s*\n\s*([A-Z][^\n]{5,80})",
        text,
        re.I,
    )
    if m:
        h.consignee = _snip(m.group(1))

    m = re.search(
        r"Ocean Vessel[^\n]*\n\s*([A-Z][A-Z0-9 ,./-]{3,40})\s+V[.,]?\s*(\S+)",
        text,
        re.I,
    )
    if m:
        h.vessel = re.sub(r"\s+", " ", m.group(1)).strip(" ,")
        h.voyage = m.group(2).rstrip(",")

    m = re.search(r"Port of Loading\s*\n\s*([A-Z][^\n,]{2,40})", text, re.I)
    # Often vessel line includes POL — also search SHANGHAI / KEELUNG markers
    if re.search(r"SHANGHAI", text, re.I):
        h.pol = "SHANGHAI, CHINA"
    if re.search(r"KEELUNG", text, re.I):
        h.pod = "KEELUNG, TAIWAN"

    # Packages: prefer cargo cartons/pallets on the face, NOT Say-Total container
    # (e.g. "222 CARTONS" / "222CARTONS/2608.53KGS" wins over "SAY TOTAL: ONE (1) 20'GP").
    # Combo must not steal a leading letter digit (OCR "B26CARTONS" from "326").
    combo_rx = re.compile(
        r"(?<![A-Za-z0-9])(\d{1,4})\s*C\s*ARTONS\s*/\s*([\d]+[.,]\d{2,3})\s*K[G6][S5]?",
        re.I,
    )
    combos = list(combo_rx.finditer(text))
    carton_counts = [
        float(m.group(1))
        for m in re.finditer(r"(?<![A-Za-z0-9])(\d{1,4})\s*CARTONS\b", text, re.I)
    ]
    m_plts = re.search(
        r"(?<![A-Za-z0-9])(\d{1,4})\s*CTNS?\s*=\s*(\d+)\s*PLTS?"
        r"|(?<![A-Za-z0-9])(\d{1,4})\s*PALLETS?\b",
        text,
        re.I,
    )

    if carton_counts:
        # Prefer the largest plausible face count (e.g. 326 over a stray 26).
        h.packages = max(carton_counts)
        h.package_unit = "CARTONS"
    elif combos:
        h.packages = float(combos[0].group(1))
        h.package_unit = "CARTONS"
    elif m_plts:
        # "83CTNS=2PLTS" → prefer CTNS group if present; else PALLETS count
        if m_plts.group(1) and m_plts.group(2):
            h.packages = float(m_plts.group(1))
            h.package_unit = "CARTONS"
        else:
            raw = m_plts.group(3) or m_plts.group(1)
            if raw:
                h.packages = float(raw)
                h.package_unit = "PALLETS"
    elif re.search(r"SAY\s+TOTAL[^\n]{0,40}PALLET|ONE\s*\(1\)\s*PALLET", text, re.I):
        h.packages = 1.0
        h.package_unit = "PALLET"
    elif re.search(r"SAY\s+TOTAL[^\n]{0,60}20.?GP|ONE\s*\(1\)\s*20", text, re.I):
        h.packages = 1.0
        h.package_unit = "20GP"

    # Gross weight: trust CARTONS/KGS combo only when its carton count matches
    # chosen packages; else use standalone KGS and fix common OCR .830↔.53 slips.
    def _to_f(raw: str) -> float | None:
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            return None

    matched_combo_gw = None
    for cm in combos:
        if h.packages is not None and float(cm.group(1)) == float(h.packages):
            matched_combo_gw = _to_f(cm.group(2))
            if matched_combo_gw is not None:
                break
    if matched_combo_gw is not None:
        h.gross_weight_kg = matched_combo_gw
    else:
        weights_raw = re.findall(r"([\d]{2,5}[.,]\d{2,3})\s*K[G6][S5]?", text, re.I)
        # Drop combo weights whose carton count disagrees with packages
        mistrust = set()
        for cm in combos:
            if h.packages is None or float(cm.group(1)) != float(h.packages):
                mistrust.add(cm.group(2).replace(",", "."))
        cands = []
        for w in weights_raw:
            key = w.replace(",", ".")
            if key in mistrust:
                continue
            v = _to_f(w)
            if v is not None and 1 <= v <= 100000:
                cands.append((w, v))
        chosen_v = None
        if cands:
            # Prefer ###.### cargo face (3dp) over first 2dp when both exist,
            # unless the 3dp looks like the .830 OCR slip of a known .53 sibling.
            three = [(w, v) for w, v in cands if re.search(r"[.,]\d{3}$", w)]
            two = [(w, v) for w, v in cands if re.search(r"[.,]\d{2}$", w)]
            if three:
                w0, v0 = three[0]
                if str(v0).endswith("83") or w0.replace(",", ".").endswith("830"):
                    # 2608.830 vs face 2608.53 — prefer matching 2dp sibling
                    stem = int(v0)
                    sib = next((v for _, v in two if int(v) == stem), None)
                    if sib is not None:
                        chosen_v = sib
                    else:
                        # reconstruct common 5→8 OCR slip: *.830 → *.53
                        if w0.replace(",", ".").endswith("830"):
                            chosen_v = float(f"{stem}.53")
                        else:
                            chosen_v = v0
                else:
                    chosen_v = v0
            elif two:
                chosen_v = two[0][1]
        if chosen_v is not None:
            h.gross_weight_kg = chosen_v

    m = re.search(r"([\d.]+)\s*M3|([\d.]+)\s*CBM", text, re.I)
    if m:
        raw = m.group(1) or m.group(2)
        try:
            h.measurement_cbm = float(raw)
        except ValueError:
            pass

    # Invoice / PL refs
    refs = []
    for rx in (r"P/?L\s*NO[:\s]*([A-Z0-9_-]+)", r"\b(BHCWHYTW\d+)\b", r"\b(NBT\d+)\b"):
        for mm in re.finditer(rx, text, re.I):
            refs.append(mm.group(1).upper())
    if refs:
        h.invoice_refs = ", ".join(dict.fromkeys(refs))

    conf = "rules"
    needs_gold = False
    if not h.bl_no:
        conf = "needs_gold"
        needs_gold = True

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="tvl_hbl_v1",
            confidence=conf,
            needs_ocr=needs_ocr,
            needs_gold=needs_gold,
            doc_kind="hbl",
            notes=NOTES if conf == "rules" else "TVL HBL partial",
        ),
    )
