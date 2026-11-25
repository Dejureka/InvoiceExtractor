"""English count words → int (ONE … NINETY-NINE), for "PACKED IN THIRTY-FOUR PALLETS"."""

from __future__ import annotations

import re

_UNITS = {
    "ZERO": 0, "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7,
    "EIGHT": 8, "NINE": 9, "TEN": 10, "ELEVEN": 11, "TWELVE": 12, "THIRTEEN": 13,
    "FOURTEEN": 14, "FIFTEEN": 15, "SIXTEEN": 16, "SEVENTEEN": 17, "EIGHTEEN": 18,
    "NINETEEN": 19,
}
_TENS = {
    "TWENTY": 20, "THIRTY": 30, "FORTY": 40, "FOURTY": 40, "FIFTY": 50, "SIXTY": 60,
    "SEVENTY": 70, "EIGHTY": 80, "NINETY": 90,
}

# One count word, e.g. "EIGHT", "TWENTY-TWO", "THIRTY FOUR" (use inside a larger regex).
WORD_RE = (
    r"(?:(?:" + "|".join(_TENS) + r")(?:[\s-]+(?:" + "|".join(k for k in _UNITS if _UNITS[k] < 10 and k != "ZERO") + r"))?"
    r"|" + "|".join(sorted(_UNITS, key=len, reverse=True)) + r")"
)


def en_count(word: str) -> int | None:
    """``"twenty-two"`` → 22; ``None`` when it is not a count word 0–99."""
    parts = [p for p in re.split(r"[\s-]+", word.strip().upper()) if p]
    if len(parts) == 1:
        p = parts[0]
        return _UNITS.get(p, _TENS.get(p))
    if len(parts) == 2 and parts[0] in _TENS and parts[1] in _UNITS and 0 < _UNITS[parts[1]] < 10:
        return _TENS[parts[0]] + _UNITS[parts[1]]
    return None
