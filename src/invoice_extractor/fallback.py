"""One marker for "this value came from an unanchored fallback rule".

Format modules wrap the value a whole-text guess produced (first ``N PALLETS``
anywhere, largest ``#,###.##``, a bare invoice-number prefix, …)::

    gw = fallback("gross_weight_kg", us_float(m.group(1)), "dunan:first_weight_triple")

``fallback`` returns the value unchanged. When it is not empty, the field and
rule name are remembered for the extraction running right now
(:func:`collecting`) and :func:`record` writes them onto ``Meta``:

* always a note ``fallback[<field>]=<rule>`` (step A, Result values unchanged);
* when :data:`FLAG_FALLBACKS` is on, the field also goes into
  ``meta.needs_gold_fields`` so the checker verdict becomes needs_gold and a
  person checks that one field (step B).

Rule: a fallback that reads a value next to its own label is *not* a fallback
here; only rules that pick a value without a label/position anchor are.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, TypeVar

T = TypeVar("T")

# Step A (note only). Step B turns this on.
FLAG_FALLBACKS = False

_HITS: ContextVar[list[tuple[str, str]] | None] = ContextVar("fallback_hits", default=None)


def fallback(field: str, value: T, rule: str) -> T:
    """Return ``value``; remember ``(field, rule)`` when the value is not empty."""
    if value is None or value == "":
        return value
    hits = _HITS.get()
    if hits is not None and (field, rule) not in hits:
        hits.append((field, rule))
    return value


@contextmanager
def collecting() -> Iterator[list[tuple[str, str]]]:
    """Collect :func:`fallback` hits made inside the ``with`` block."""
    hits: list[tuple[str, str]] = []
    token = _HITS.set(hits)
    try:
        yield hits
    finally:
        _HITS.reset(token)


def record(meta, hits: list[tuple[str, str]]) -> None:
    """Write collected hits onto ``meta`` (note; plus needs_gold_fields in step B)."""
    if not hits:
        return
    extra = "; ".join(f"fallback[{f}]={r}" for f, r in hits)
    note = (meta.notes or "").strip()
    meta.notes = f"{note}; {extra}" if note else extra
    if FLAG_FALLBACKS:
        fields = list(meta.needs_gold_fields or [])
        for f, _ in hits:
            if f not in fields:
                fields.append(f)
        meta.needs_gold_fields = fields
