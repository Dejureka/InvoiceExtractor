"""BL / arrival-notice / HBL extract schema (parallel to invoice ExtractResult)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

BLConfidence = Literal["gold", "rules", "high", "conflict", "needs_gold"]


@dataclass
class BLHeader:
    """Key fields for later INV↔BL reconcile."""

    bl_no: Optional[str] = None  # B/L or HBL number (primary)
    hbl_no: Optional[str] = None  # when distinct from bl_no
    mbl_no: Optional[str] = None  # master bill
    vessel: Optional[str] = None
    voyage: Optional[str] = None
    etd: Optional[str] = None  # YYYY-MM-DD
    eta: Optional[str] = None  # YYYY-MM-DD
    pol: Optional[str] = None  # port of loading
    pod: Optional[str] = None  # port of discharge
    packages: Optional[float] = None
    package_unit: Optional[str] = None
    gross_weight_kg: Optional[float] = None
    measurement_cbm: Optional[float] = None
    load_type: Optional[str] = None  # FCL / LCL
    shipper: Optional[str] = None
    consignee: Optional[str] = None
    notify: Optional[str] = None
    invoice_refs: Optional[str] = None  # related commercial invoice nos
    container_nos: Optional[str] = None
    forwarder: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BLMeta:
    source_file: str = ""
    text_backend: str = ""
    format_id: Optional[str] = None
    confidence: BLConfidence = "rules"
    needs_ocr: bool = False
    needs_gold: bool = False
    notes: Optional[str] = None
    doc_kind: str = "bl"  # bl | arrival_notice | hbl
    checker_verdict: Optional[str] = None
    checker_issues: Optional[list[str]] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BLExtractResult:
    header: BLHeader = field(default_factory=BLHeader)
    meta: BLMeta = field(default_factory=BLMeta)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_type": "bl",
            "header": self.header.to_dict(),
            "meta": self.meta.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BLExtractResult":
        h = data.get("header") or {}
        m = data.get("meta") or {}
        hk = {k: h.get(k) for k in BLHeader.__dataclass_fields__}
        mk = {k: m[k] for k in BLMeta.__dataclass_fields__ if k in m}
        return cls(header=BLHeader(**hk), meta=BLMeta(**mk))


def us_mdy_to_iso(d: str) -> str | None:
    """``8/15/2026`` / ``08/15/2026`` → ``YYYY-MM-DD``."""
    import re

    s = (d or "").strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if not m:
        return None
    mm, dd, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None
    return f"{yyyy:04d}-{mm:02d}-{dd:02d}"


def loose_date_to_iso(d: str) -> str | None:
    """Accept ISO, US M/D/Y, or ``2026-8-18``."""
    import re

    from invoice_extractor.schema import en_date_to_iso

    s = (d or "").strip()
    if not s:
        return None
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    iso = us_mdy_to_iso(s)
    if iso:
        return iso
    return en_date_to_iso(s)
