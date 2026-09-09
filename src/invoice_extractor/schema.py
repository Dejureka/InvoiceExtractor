"""Canonical extract.json schema (header + items + meta)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional


Confidence = Literal["gold", "rules", "high", "conflict", "needs_gold"]


@dataclass
class Header:
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None  # YYYY-MM-DD
    total_pkg: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    incoterm: Optional[str] = None
    item_line_count: Optional[int] = None
    total_quantity: Optional[float] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    vendor: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Item:
    invoice_no: Optional[str] = None
    part_no: Optional[str] = None
    description: Optional[str] = None
    qty: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    origin: Optional[str] = None
    hs_code: Optional[str] = None
    currency: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Meta:
    source_file: str = ""
    text_backend: str = ""
    format_id: Optional[str] = None
    confidence: Confidence = "rules"
    needs_ocr: bool = False
    needs_gold: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractResult:
    header: Header = field(default_factory=Header)
    items: list[Item] = field(default_factory=list)
    meta: Meta = field(default_factory=Meta)

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "items": [i.to_dict() for i in self.items],
            "meta": self.meta.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExtractResult":
        h = data.get("header") or {}
        items_raw = data.get("items") or []
        m = data.get("meta") or {}
        hk = {k: h.get(k) for k in Header.__dataclass_fields__}
        mk = {k: m[k] for k in Meta.__dataclass_fields__ if k in m}
        return cls(
            header=Header(**hk),
            items=[
                Item(**{k: it.get(k) for k in Item.__dataclass_fields__})
                for it in items_raw
            ],
            meta=Meta(**mk),
        )


def eu_float(s: str) -> float:
    """Normalize EU ``6.052,400`` / US ``1,003.28`` → float."""
    s = (s or "").strip().replace(" ", "").replace("\u00a0", "")
    if not s:
        raise ValueError("empty number")
    if "," in s and "." in s:
        # decide: last separator is decimal
        if s.rfind(",") > s.rfind("."):
            return float(s.replace(".", "").replace(",", "."))
        return float(s.replace(",", ""))
    if "," in s:
        # either EU decimal or US thousands — if exactly 3 digits after comma → thousands?
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit():
            # ambiguous: treat as EU decimal if left side has dots OR typical EU weight
            return float(s.replace(",", "."))
        if len(parts[-1]) == 3 and all(p.isdigit() for p in parts):
            return float(s.replace(",", ""))
        return float(s.replace(",", "."))
    return float(s)


def us_float(s: str) -> float:
    """US-style ``1,003.28`` or ``10091.68``."""
    s = (s or "").strip().replace(" ", "").replace("\u00a0", "")
    return float(s.replace(",", ""))


def de_date_to_iso(d: str) -> str:
    """``04.12.2025`` / ``08.07.2026`` → ``YYYY-MM-DD``."""
    import re

    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})$", (d or "").strip())
    if not m:
        return (d or "").strip()
    dd, mm, yyyy = m.groups()
    return f"{yyyy}-{mm}-{dd}"
