"""INV / PKL / BL role tagging, auto-pairing, and merge helpers.

Primary split case today is **BHC** (Bosch Home Comfort / MY-HUB): separate
``*_INV_*`` and ``*_PKL_*`` PDFs, plus optional 到貨通知／HBL. MA invoices are
usually a **combined** PDF (invoice + packing in one file).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

from invoice_extractor.formats.ma_common import parse_rb_packages
from invoice_extractor.schema import ExtractResult, Header, Meta, eu_float, us_float

Role = Literal["inv", "pkl", "combined", "bl", "unknown"]

STATUS_INV_PKL = "INV+PKL"
STATUS_INV_ONLY = "僅 INV"
STATUS_PKL_ONLY = "僅 PKL"
STATUS_BL_ONLY = "僅 提單"
STATUS_UNMATCHED = "未配對／需確認"

# --- filename / text anchors -------------------------------------------------

# BHC-first filename role markers (tokenized on _ - . space).
_FN_COMBINED_HINT = re.compile(r"合訂|combined|inv.?pkl|invoice.?pack", re.I)
_INV_TOKENS = frozenset({"INV", "INVOICE", "IV"})  # IV = invoice abbr (e.g. "IV PL.pdf")
_PKL_TOKENS = frozenset({"PKL", "PL", "PACKING", "PACK", "PACKLIST"})


def _filename_tokens(name: str) -> set[str]:
    stem = Path(name).stem.upper()
    return {t for t in re.split(r"[_\-\s.,]+", stem) if t}

# Shared pairing tokens
# BHC invoice nos often 9027xxxxxx; MA Document No. 2000xxxxxx / 2120xxxxxx
# Underscore-friendly (filenames like 002_2000262902_RBTW); prefer known prefixes
_INV_NO = re.compile(
    r"(?<![A-Za-z0-9])(9027\d{6}|2000\d{6}|2120\d{6}|\d{10})(?![A-Za-z0-9])"
)
# BHC shipment / booking fragments e.g. TA2608B2-3253
_BHC_TA = re.compile(r"(?<![A-Za-z0-9])(TA\d{4}B\d?[-\d]*)(?![A-Za-z0-9])", re.I)
# MA batch folder / filename e.g. 90-S-26MA-024, 90-KWE-26MA-041
_MA_BATCH = re.compile(r"(?<![A-Za-z0-9])(90-[A-Z]+-\d{2}MA-\d{3})(?![A-Za-z0-9])", re.I)

_TEXT_INV = re.compile(
    r"\b(?:COMMERCIAL\s+INVOICE|INVOICE\s+NUMBER|INVOICE\s+NO\.?|DOCUMENT\s+NO\.?|"
    r"GOODS\s+VALUE|TOTALS:|PART\s+NO|NET\s+INVOICED\s+VALUE)\b",
    re.I,
)
_TEXT_PKL = re.compile(
    r"\b(?:PACKING\s+LIST|PACKING\s+DETAILS|LADELISTE|GESAMTGEWICHT|"
    r"PACKING\s+SET|\bRB\s+\d{6,})\b",
    re.I,
)


@dataclass
class FileRole:
    path: Path
    role: Role
    keys: set[str] = field(default_factory=set)
    confidence: float = 0.0
    notes: str = ""


@dataclass
class PairRow:
    """One GUI / extract unit (INV+PKL±BL, INV-only, PKL-only, BL-only, unmatched)."""

    pair_id: str
    inv_path: Optional[Path] = None
    pkl_path: Optional[Path] = None
    bl_path: Optional[Path] = None
    status: str = STATUS_UNMATCHED
    skipped: bool = False
    # User override flag (manual rematch / split)
    manual: bool = False

    @property
    def display_inv(self) -> str:
        return self.inv_path.name if self.inv_path else "—"

    @property
    def display_pkl(self) -> str:
        return self.pkl_path.name if self.pkl_path else "—"

    @property
    def display_bl(self) -> str:
        return self.bl_path.name if self.bl_path else "—"

    def recompute_status(self) -> None:
        if self.skipped:
            return
        if self.inv_path and self.pkl_path:
            self.status = STATUS_INV_PKL
        elif self.inv_path and not self.pkl_path:
            self.status = STATUS_INV_ONLY
        elif self.pkl_path and not self.inv_path:
            self.status = STATUS_PKL_ONLY
        elif self.bl_path and not self.inv_path and not self.pkl_path:
            self.status = STATUS_BL_ONLY
        else:
            self.status = STATUS_UNMATCHED


# BL / HBL / arrival tokens (filename + soft match to INV invoice refs)
_BL_NO = re.compile(
    r"(?<![A-Za-z0-9])(WEB\d{9}|HBL\d{5,}|HB\d{8}|NGOA\d{5,}|NBT\d{3,}|SHAKEL\d+)(?![A-Za-z0-9])",
    re.I,
)
# Soft invoice-ref style tokens e.g. JCH26-08M1 / AETW26012
_SOFT_REF = re.compile(
    r"(?<![A-Za-z0-9])([A-Z]{2,6}\d{2}[-]?\d{2,6}[A-Z]?)(?![A-Za-z0-9])",
    re.I,
)


def pairing_keys_from_path(path: Path) -> set[str]:
    """Tokens used to match INV↔PKL↔BL (BHC-first, then MA batch / invoice no / BL)."""
    keys: set[str] = set()
    name = path.name
    parent = path.parent.name if path.parent else ""
    blob = f"{parent}/{name}"

    for m in _INV_NO.finditer(blob):
        keys.add(f"inv:{m.group(1)}")
    for m in re.finditer(r"(?<![A-Za-z0-9])(AK\d{8})(?![A-Za-z0-9])", blob, re.I):
        keys.add(f"inv:{m.group(1).upper()}")
    for m in _BHC_TA.finditer(blob):
        keys.add(f"ta:{m.group(1).upper()}")
    for m in _MA_BATCH.finditer(blob):
        keys.add(f"batch:{m.group(1).upper()}")
    for m in _BL_NO.finditer(blob):
        keys.add(f"bl:{m.group(1).upper()}")
    for m in _SOFT_REF.finditer(blob):
        tok = m.group(1).upper().replace("-", "")
        if len(tok) >= 6:
            keys.add(f"ref:{tok}")

    # Same-folder soft key (lower priority — used as tie-break / same-dir prefer)
    try:
        keys.add(f"dir:{path.parent.resolve()}")
    except Exception:
        keys.add(f"dir:{path.parent}")

    # Stem without role tokens — helps TA2608…_INV_9027… ↔ …_PKL_9027…
    stem = path.stem
    parts = [t for t in re.split(r"[_\-\s.,]+", stem) if t]
    parts = [t for t in parts if t.upper() not in (_INV_TOKENS | _PKL_TOKENS)]
    stem_norm = "_".join(parts).upper()
    if len(stem_norm) >= 6:
        keys.add(f"stem:{stem_norm}")

    return keys


def classify_role(
    path: Path,
    text: str | None = None,
    *,
    filename_only: bool = False,
) -> FileRole:
    """Tag a PDF as inv / pkl / combined / bl / unknown.

    Filename markers (BHC ``_INV_`` / ``_PKL_`` / 到貨／HBL) win when unambiguous.
    Text anchors refine combined vs inv-only when the file has both sections.
    """
    from invoice_extractor.bl_rules_engine import looks_like_bl_filename

    name = path.name
    keys = pairing_keys_from_path(path)
    tokens = _filename_tokens(name)
    fn_inv = bool(tokens & _INV_TOKENS)
    fn_pkl = bool(tokens & _PKL_TOKENS)
    fn_combined = bool(_FN_COMBINED_HINT.search(name))

    # BL / arrival / HBL first (avoid mistaking "HBL draft …" as unknown)
    if looks_like_bl_filename(name) and not (fn_inv or fn_pkl):
        return FileRole(path, "bl", keys, 0.9, "filename BL/arrival")

    # Strong filename signals (BHC split; also …_INV.PDF / …_PKL.PDF stems)
    if fn_inv and not fn_pkl:
        return FileRole(path, "inv", keys, 0.9, "filename INV")
    if fn_pkl and not fn_inv:
        return FileRole(path, "pkl", keys, 0.9, "filename PKL")
    if fn_inv and fn_pkl:
        return FileRole(path, "combined", keys, 0.85, "filename INV+PKL")
    if fn_combined:
        return FileRole(path, "combined", keys, 0.8, "filename combined hint")

    if filename_only or text is None:
        # MA-style single PDF (no INV/PKL tag) — treat as combined/inv candidate
        if _MA_BATCH.search(name) or re.search(r"RBTW|INVOICE\s+\d{10}", name, re.I):
            return FileRole(path, "combined", keys, 0.55, "MA-like filename")
        if re.search(r"BITZER|Versanddokument|Ladeliste", name, re.I):
            return FileRole(path, "combined", keys, 0.55, "BITZER-like filename")
        return FileRole(path, "unknown", keys, 0.2, "no filename role")

    t_inv = bool(_TEXT_INV.search(text))
    t_pkl = bool(_TEXT_PKL.search(text))
    if t_inv and t_pkl:
        return FileRole(path, "combined", keys, 0.75, "text INV+packing")
    if t_inv and not t_pkl:
        return FileRole(path, "inv", keys, 0.65, "text invoice")
    if t_pkl and not t_inv:
        return FileRole(path, "pkl", keys, 0.65, "text packing")
    return FileRole(path, "unknown", keys, 0.25, "text inconclusive")


def _shared_match_score(a: set[str], b: set[str], *, same_dir: bool) -> float:
    """Higher = better INV↔PKL/BL match. Prefer invoice-no / TA / batch / BL over dir-only."""
    inter = a & b
    score = 0.0
    for k in inter:
        if k.startswith("inv:"):
            score += 5.0
        elif k.startswith("bl:"):
            score += 5.0
        elif k.startswith("ta:"):
            score += 4.0
        elif k.startswith("batch:"):
            score += 4.0
        elif k.startswith("ref:"):
            score += 3.5
        elif k.startswith("stem:"):
            score += 3.0
        elif k.startswith("dir:"):
            score += 0.5
    if same_dir:
        score += 1.0
    return score


def auto_pair(paths: Iterable[Path], *, roles: list[FileRole] | None = None) -> list[PairRow]:
    """Build pair rows from selected PDFs (filename roles; no PDF I/O).

    Strategy (BHC-optimized):
    1. Classify each file by filename (INV / PKL / BL / combined).
    2. Match inv↔pkl by shared invoice no / TA / batch; **same folder preferred**.
    3. Attach BL to INV-bearing rows (shared bl:/ref: keys, or same-folder N:1 share).
    4. Leftover inv → 僅 INV; leftover pkl → 僅 PKL; leftover bl → 僅 提單;
       unknown alone → 未配對／需確認.
    5. ``combined`` / unknown-with-MA-like → single-file row (INV side, no PKL).
    """
    paths = [Path(p) for p in paths]
    if roles is None:
        roles = [classify_role(p, filename_only=True) for p in paths]
    by_path = {r.path.resolve(): r for r in roles}

    invs = [r for r in roles if r.role in ("inv",)]
    pkls = [r for r in roles if r.role == "pkl"]
    bls = [r for r in roles if r.role == "bl"]
    singles = [r for r in roles if r.role in ("combined", "unknown")]

    used_inv: set[Path] = set()
    used_pkl: set[Path] = set()
    rows: list[PairRow] = []
    n = 0

    # Greedy best matches: same-folder first via score bonus
    candidates: list[tuple[float, FileRole, FileRole]] = []
    for inv in invs:
        for pkl in pkls:
            try:
                same_dir = inv.path.parent.resolve() == pkl.path.parent.resolve()
            except Exception:
                same_dir = inv.path.parent == pkl.path.parent
            sc = _shared_match_score(inv.keys, pkl.keys, same_dir=same_dir)
            if sc >= 4.0 or (same_dir and sc >= 1.5):
                candidates.append((sc, inv, pkl))
    candidates.sort(key=lambda t: (-t[0], t[1].path.name, t[2].path.name))

    for sc, inv, pkl in candidates:
        if inv.path in used_inv or pkl.path in used_pkl:
            continue
        # Require at least one strong key unless unique same-folder pair later
        strong = any(
            k.startswith(("inv:", "ta:", "batch:", "stem:"))
            for k in (inv.keys & pkl.keys)
        )
        try:
            same_dir = inv.path.parent.resolve() == pkl.path.parent.resolve()
        except Exception:
            same_dir = inv.path.parent == pkl.path.parent
        if not strong and not same_dir:
            continue
        if not strong and same_dir:
            # same-folder weak pair only if both have no other strong candidates
            pass
        used_inv.add(inv.path)
        used_pkl.add(pkl.path)
        n += 1
        row = PairRow(
            pair_id=f"P{n}",
            inv_path=inv.path,
            pkl_path=pkl.path,
            status=STATUS_INV_PKL,
        )
        rows.append(row)

    # Same-folder 1:1 leftover matching (BHC drop-folder UX)
    remaining_inv = [r for r in invs if r.path not in used_inv]
    remaining_pkl = [r for r in pkls if r.path not in used_pkl]
    by_dir_inv: dict[str, list[FileRole]] = {}
    by_dir_pkl: dict[str, list[FileRole]] = {}
    for r in remaining_inv:
        by_dir_inv.setdefault(str(r.path.parent.resolve()), []).append(r)
    for r in remaining_pkl:
        by_dir_pkl.setdefault(str(r.path.parent.resolve()), []).append(r)
    for d, di in by_dir_inv.items():
        dp = by_dir_pkl.get(d) or []
        if len(di) == 1 and len(dp) == 1:
            inv, pkl = di[0], dp[0]
            if inv.path in used_inv or pkl.path in used_pkl:
                continue
            used_inv.add(inv.path)
            used_pkl.add(pkl.path)
            n += 1
            rows.append(
                PairRow(
                    pair_id=f"P{n}",
                    inv_path=inv.path,
                    pkl_path=pkl.path,
                    status=STATUS_INV_PKL,
                )
            )

    for r in invs:
        if r.path in used_inv:
            continue
        n += 1
        rows.append(
            PairRow(pair_id=f"P{n}", inv_path=r.path, status=STATUS_INV_ONLY)
        )
    for r in pkls:
        if r.path in used_pkl:
            continue
        n += 1
        rows.append(
            PairRow(pair_id=f"P{n}", pkl_path=r.path, status=STATUS_PKL_ONLY)
        )

    for r in singles:
        n += 1
        # Combined / MA-like → extract as single INV/combined file
        if r.role == "combined" or r.confidence >= 0.5:
            rows.append(
                PairRow(
                    pair_id=f"P{n}",
                    inv_path=r.path,
                    status=STATUS_INV_ONLY,  # no separate PKL; extract treats as combined
                )
            )
        else:
            rows.append(
                PairRow(
                    pair_id=f"P{n}",
                    inv_path=r.path,
                    status=STATUS_UNMATCHED,
                )
            )

    # --- Attach BL to INV-bearing rows, then leftover → 僅 提單 ---
    used_bl: set[Path] = set()
    inv_rows = [r for r in rows if r.inv_path]
    bl_roles = {r.path.resolve(): r for r in bls}

    # Score BL ↔ INV-row (keys from INV and optional PKL paths)
    bl_candidates: list[tuple[float, PairRow, FileRole]] = []
    for row in inv_rows:
        keys: set[str] = set()
        if row.inv_path:
            keys |= pairing_keys_from_path(row.inv_path)
        if row.pkl_path:
            keys |= pairing_keys_from_path(row.pkl_path)
        for br in bls:
            try:
                same_dir = (
                    row.inv_path is not None
                    and row.inv_path.parent.resolve() == br.path.parent.resolve()
                )
            except Exception:
                same_dir = (
                    row.inv_path is not None
                    and row.inv_path.parent == br.path.parent
                )
            sc = _shared_match_score(keys, br.keys, same_dir=same_dir)
            # Require a real signal beyond dir-only, unless same-folder alone is unique later
            if sc >= 4.0 or (same_dir and sc >= 1.0):
                bl_candidates.append((sc, row, br))
    bl_candidates.sort(key=lambda t: (-t[0], t[1].pair_id, t[2].path.name))

    for sc, row, br in bl_candidates:
        if br.path in used_bl or row.bl_path is not None:
            continue
        row_keys: set[str] = set()
        if row.inv_path:
            row_keys |= pairing_keys_from_path(row.inv_path)
        if row.pkl_path:
            row_keys |= pairing_keys_from_path(row.pkl_path)
        strong = any(
            k.startswith(("inv:", "bl:", "ta:", "batch:", "ref:", "stem:"))
            for k in (br.keys & row_keys)
        )
        try:
            same_dir = (
                row.inv_path is not None
                and row.inv_path.parent.resolve() == br.path.parent.resolve()
            )
        except Exception:
            same_dir = (
                row.inv_path is not None
                and row.inv_path.parent == br.path.parent
            )
        if not strong and not same_dir:
            continue
        used_bl.add(br.path)
        row.bl_path = br.path
        row.recompute_status()

    # Same-folder N:1 — exactly one BL in a folder is shared by every INV row there
    # (MA multi-INV packs 548/616: each INV Summary row repeats shared BL No./pkg/GW).
    by_dir_inv_rows: dict[str, list[PairRow]] = {}
    for row in inv_rows:
        if not row.inv_path:
            continue
        try:
            d = str(row.inv_path.parent.resolve())
        except Exception:
            d = str(row.inv_path.parent)
        by_dir_inv_rows.setdefault(d, []).append(row)
    by_dir_bl_all: dict[str, list[FileRole]] = {}
    for br in bls:
        try:
            d = str(br.path.parent.resolve())
        except Exception:
            d = str(br.path.parent)
        by_dir_bl_all.setdefault(d, []).append(br)
    for d, di in by_dir_inv_rows.items():
        db = by_dir_bl_all.get(d) or []
        if len(db) != 1:
            continue
        br = db[0]
        for row in di:
            if row.bl_path is None:
                row.bl_path = br.path
                row.recompute_status()
        used_bl.add(br.path)

    for br in bls:
        if br.path in used_bl:
            continue
        n += 1
        rows.append(
            PairRow(
                pair_id=f"P{n}",
                bl_path=br.path,
                status=STATUS_BL_ONLY,
            )
        )

    rows.sort(
        key=lambda r: (
            r.status not in (STATUS_INV_PKL, STATUS_INV_ONLY),
            r.display_inv,
            r.display_pkl,
            r.display_bl,
        )
    )
    # renumber
    for i, r in enumerate(rows, 1):
        r.pair_id = f"P{i}"
    return rows


def parse_packing_pkg_gw(text: str) -> tuple[float | None, float | None]:
    """Packages + gross weight from a PKL (or packing section).

    Order: MA ``parse_rb_packages`` → BITZER Gesamtgewicht → BHC PKL TOTAL rows
    → generic Gross/Packages.
    """
    pkg, gw = parse_rb_packages(text)
    if pkg is not None or gw is not None:
        return pkg, gw

    m = re.search(r"Gesamtgewicht\s+(\d+)\s+([\d.,]+)\s*KG", text, re.I)
    if m:
        return float(m.group(1)), eu_float(m.group(2))

    # BHC Supply (M) packing list: TOTAL {ctns} {nw} {gw} {m3}
    m = re.search(
        r"(?im)^\s*TOTAL\s+(\d+)\s+[\d.,]+\s+([\d.,]+)\s+[\d.,]+\s*$",
        text,
    )
    if m:
        return float(m.group(1)), us_float(m.group(2))

    # Bosch Home Comfort Malaysia factory PKL:
    # "1-3   3   TOTAL   52   715.5   867   7.863" → pkg=3, gw=867
    m = re.search(
        r"(?im)^\s*\S+\s+(\d+)\s+TOTAL\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)\s+[\d.,]+\s*$",
        text,
    )
    if m:
        return float(m.group(1)), us_float(m.group(2))

    # Qingdao Hisense combined PL TOTAL row:
    # TOTAL  209  0  169  169  45986.00  43101.00  294.52 → pkg=169, gw=45986
    m = re.search(
        r"(?im)^\s*TOTAL\s+[\d.,]+\s+[\d.,]+\s+(\d+)\s+\1\s+([\d.,]+)\s+[\d.,]+\s+[\d.,]+\s*$",
        text,
    )
    if m:
        return float(m.group(1)), us_float(m.group(2))

    # Aichi packing sheet footer: "12 PALLETS ... 7,217 KG"
    m = re.search(
        r"(?im)^\s*(\d+)\s+PALLETS?\b[^\n]*?([\d,]+)\s*KG\s*$",
        text,
    )
    if m:
        return float(m.group(1)), us_float(m.group(2))

    gw_val: float | None = None
    m = re.search(
        r"(?:Gross\s*(?:weight|wt\.?)|G\.?\s*W\.?)\s*[:=]?\s*([\d.,]+)\s*K?G?",
        text,
        re.I,
    )
    if m:
        try:
            gw_val = us_float(m.group(1)) if "," in m.group(1) and "." in m.group(1) else (
                eu_float(m.group(1)) if "," in m.group(1) else us_float(m.group(1))
            )
        except ValueError:
            try:
                gw_val = eu_float(m.group(1))
            except ValueError:
                gw_val = None

    pkg_val: float | None = None
    m = re.search(
        r"(?:Total\s+)?(?:Packages?|Cartons?|Pkgs?|Cases?)\s*[:=]?\s*(\d+)\b",
        text,
        re.I,
    )
    if m:
        pkg_val = float(m.group(1))

    return pkg_val, gw_val


def merge_pkl_onto_inv(
    inv_result: ExtractResult,
    *,
    pkl_text: str,
    pkl_path: Path | str | None,
    inv_path: Path | str | None = None,
    source: str = "split",
) -> ExtractResult:
    """Copy INV extract; overlay total_pkg / gross_weight_kg from PKL text."""
    pkg, gw = parse_packing_pkg_gw(pkl_text)
    header = replace(inv_result.header)
    pkl_used = False
    if pkg is not None:
        header.total_pkg = pkg
        pkl_used = True
    if gw is not None:
        header.gross_weight_kg = gw
        pkl_used = True

    meta = replace(inv_result.meta)
    meta.source = source
    inv_p = str(inv_path or meta.source_file or "")
    pkl_p = str(pkl_path or "")
    meta.inv_file = inv_p or None
    meta.pkl_file = pkl_p or None
    meta.pkl_used = pkl_used
    meta.pair_status = STATUS_INV_PKL if pkl_used or pkl_p else STATUS_INV_ONLY
    if inv_p:
        meta.source_file = inv_p
    note = (meta.notes or "").strip()
    extra = f"source={source}; pkl_used={'yes' if pkl_used else 'no'}"
    meta.notes = f"{note}; {extra}".strip("; ") if note else extra

    return ExtractResult(header=header, items=list(inv_result.items), meta=meta)


def merge_bl_onto_inv(
    inv_result: ExtractResult,
    *,
    bl_header: dict[str, Any] | None,
    bl_path: Path | str | None,
    bl_format_id: str | None = None,
) -> ExtractResult:
    """Overlay BL No. / BL Packages / BL G.W. onto invoice header.

    Never overwrites invoice ``total_pkg`` / ``gross_weight_kg``.
    """
    header = replace(inv_result.header)
    meta = replace(inv_result.meta)
    bl_used = False
    bh = dict(bl_header or {})
    bl_no = bh.get("bl_no") or bh.get("hbl_no")
    if bl_no:
        header.bl_no = str(bl_no)
        bl_used = True
    if bh.get("packages") is not None:
        try:
            header.bl_packages = float(bh["packages"])
            bl_used = True
        except (TypeError, ValueError):
            pass
    if bh.get("gross_weight_kg") is not None:
        try:
            header.bl_gross_weight_kg = float(bh["gross_weight_kg"])
            bl_used = True
        except (TypeError, ValueError):
            pass
    bl_p = str(bl_path or "") or None
    meta.bl_file = bl_p
    meta.bl_used = bl_used
    if bl_format_id:
        meta.bl_format_id = bl_format_id
    note = (meta.notes or "").strip()
    extra = f"bl_used={'yes' if bl_used else 'no'}"
    if bl_p:
        extra += f"; bl_file={Path(bl_p).name}"
    meta.notes = f"{note}; {extra}".strip("; ") if note else extra
    return ExtractResult(header=header, items=list(inv_result.items), meta=meta)


def bl_only_extract(
    *,
    bl_header: dict[str, Any] | None,
    bl_path: Path | str,
    bl_format_id: str | None = None,
    bl_meta: dict[str, Any] | None = None,
) -> ExtractResult:
    """Summary-only row for unpaired BL (invoice fields blank; BL columns filled)."""
    header = Header()
    bh = dict(bl_header or {})
    bl_no = bh.get("bl_no") or bh.get("hbl_no")
    if bl_no:
        header.bl_no = str(bl_no)
    if bh.get("packages") is not None:
        try:
            header.bl_packages = float(bh["packages"])
        except (TypeError, ValueError):
            pass
    if bh.get("gross_weight_kg") is not None:
        try:
            header.bl_gross_weight_kg = float(bh["gross_weight_kg"])
        except (TypeError, ValueError):
            pass
    bm = dict(bl_meta or {})
    meta = Meta(
        source_file=str(bl_path),
        text_backend=str(bm.get("text_backend") or ""),
        format_id=bl_format_id or bm.get("format_id"),
        confidence=bm.get("confidence") or "rules",
        needs_ocr=bool(bm.get("needs_ocr")),
        needs_gold=bool(bm.get("needs_gold")),
        notes=bm.get("notes"),
        source="bl_only",
        bl_file=str(bl_path),
        bl_used=True,
        bl_format_id=bl_format_id or bm.get("format_id"),
        pair_status=STATUS_BL_ONLY,
    )
    return ExtractResult(header=header, items=[], meta=meta)


def annotate_combined_meta(result: ExtractResult, path: Path | str) -> ExtractResult:
    """Mark a single-file (合訂本) extract in meta."""
    meta = replace(result.meta)
    meta.source = "combined"
    meta.inv_file = str(path)
    meta.pkl_file = str(path)
    meta.pkl_used = True
    meta.pair_status = STATUS_INV_PKL
    note = (meta.notes or "").strip()
    extra = "source=combined; pkl_used=yes"
    meta.notes = f"{note}; {extra}".strip("; ") if note else extra
    return ExtractResult(header=result.header, items=list(result.items), meta=meta)


def annotate_inv_only_meta(result: ExtractResult, path: Path | str) -> ExtractResult:
    meta = replace(result.meta)
    meta.source = "split"
    meta.inv_file = str(path)
    meta.pkl_file = None
    meta.pkl_used = False
    meta.pair_status = STATUS_INV_ONLY
    note = (meta.notes or "").strip()
    if "缺 PKL" not in (note or ""):
        extra = "source=split; pkl_used=no; 缺 PKL"
        meta.notes = f"{note}; {extra}".strip("; ") if note else extra
    return ExtractResult(header=result.header, items=list(result.items), meta=meta)


def pair_status_for_result(meta: dict[str, Any] | None) -> str:
    meta = meta or {}
    ps = meta.get("pair_status")
    if ps:
        return str(ps)
    src = meta.get("source")
    if src == "combined":
        return STATUS_INV_PKL
    if meta.get("pkl_used"):
        return STATUS_INV_PKL
    if meta.get("pkl_file"):
        return STATUS_INV_PKL
    if meta.get("inv_file") and not meta.get("pkl_file"):
        return STATUS_INV_ONLY
    if meta.get("bl_file") and not meta.get("inv_file"):
        return STATUS_BL_ONLY
    return "—"



def extract_pair_row(
    row: PairRow,
    *,
    format_id: str | None = None,
) -> dict[str, Any] | None:
    """Extract one pair row → data dict (with ``_hard``), or None if skipped / PKL-only.

    - INV+PKL (split): INV extract + PKL packing overlay; ``source=split``.
    - Combined single PDF: normal extract; ``source=combined``.
    - INV-only: normal extract; ``缺 PKL``; pkg/GW may be empty.
    - +BL: merge BL No./Packages/G.W. into Summary columns (never overwrite INV pkg/GW).
    - BL-only: Summary row with BL columns only.
    - PKL-only / skipped: return None (caller lists as skipped).
    """
    from invoice_extractor.bl_rules_engine import extract_bl
    from invoice_extractor.checker import hard_check
    from invoice_extractor.checker_bl import hard_check_bl
    from invoice_extractor.rules_engine import extract_invoice
    from invoice_extractor.text_layer import backend_warning, extract_layout_text

    if row.skipped:
        return None

    # PKL-only (no INV, no BL-only path)
    if row.status == STATUS_PKL_ONLY or (
        row.pkl_path and not row.inv_path and not row.bl_path
    ):
        return None

    # BL-only → Summary BL columns, no Lines
    if (row.status == STATUS_BL_ONLY or (row.bl_path and not row.inv_path)) and row.bl_path:
        bl_path = Path(row.bl_path)
        bl_result = extract_bl(bl_path)
        bl_data = bl_result.to_dict()
        bl_hard = hard_check_bl(bl_data)
        result = bl_only_extract(
            bl_header=bl_data.get("header"),
            bl_path=bl_path,
            bl_format_id=(bl_data.get("meta") or {}).get("format_id"),
            bl_meta=bl_data.get("meta"),
        )
        data = result.to_dict()
        data["meta"]["checker_verdict"] = bl_hard["verdict"]
        data["meta"]["checker_issues"] = bl_hard.get("issues")
        data["meta"]["checker_details"] = bl_hard.get("details")
        if bl_hard["verdict"] == "pass" and data["meta"].get("confidence") == "rules":
            data["meta"]["confidence"] = "high"
        warn = backend_warning(data["meta"].get("text_backend"))
        if warn:
            data["meta"]["text_backend_warning"] = warn
        data["_hard"] = bl_hard
        data["_pair_status"] = STATUS_BL_ONLY
        data["_pair_id"] = row.pair_id
        return data

    if not row.inv_path:
        return None

    inv_path = Path(row.inv_path)
    result = extract_invoice(inv_path, format_id=format_id)

    # Refine role with text when we have a lone file (合訂本 vs INV-only)
    if row.pkl_path:
        pkl_path = Path(row.pkl_path)
        pkl_text, _b, _o = extract_layout_text(pkl_path)
        result = merge_pkl_onto_inv(
            result,
            pkl_text=pkl_text,
            pkl_path=pkl_path,
            inv_path=inv_path,
            source="split",
        )
    else:
        # Peek text already used by extract; re-read cheap enough for meta
        try:
            text_layer, _b, _o = extract_layout_text(inv_path)
        except Exception:
            text_layer = ""
        role = classify_role(inv_path, text_layer)
        if role.role == "combined" or (
            result.header.total_pkg is not None and result.header.gross_weight_kg is not None
            and _TEXT_PKL.search(text_layer or "")
        ):
            result = annotate_combined_meta(result, inv_path)
        else:
            result = annotate_inv_only_meta(result, inv_path)

    # Optional BL overlay (does not touch invoice Packages / G.W.)
    if row.bl_path:
        bl_path = Path(row.bl_path)
        bl_result = extract_bl(bl_path)
        bl_data = bl_result.to_dict()
        result = merge_bl_onto_inv(
            result,
            bl_header=bl_data.get("header"),
            bl_path=bl_path,
            bl_format_id=(bl_data.get("meta") or {}).get("format_id"),
        )

    data = result.to_dict()
    hard = hard_check(data)
    data["meta"]["checker_verdict"] = hard["verdict"]
    if hard["verdict"] == "pass" and data["meta"].get("confidence") == "rules":
        data["meta"]["confidence"] = "high"
    elif hard["verdict"] == "conflict":
        data["meta"]["confidence"] = "conflict"
    data["meta"]["checker_issues"] = hard.get("issues")
    data["meta"]["checker_details"] = hard.get("details")
    warn = backend_warning(data["meta"].get("text_backend"))
    if warn:
        data["meta"]["text_backend_warning"] = warn
    data["_hard"] = hard
    data["_pair_status"] = data["meta"].get("pair_status") or row.status
    data["_pair_id"] = row.pair_id
    return data
