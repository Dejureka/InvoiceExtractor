"""Every fixed look-ahead / gap limit used by the format rules, in one place.

Formats read these as ``windows.NAME`` *at call time* (never ``from … import``)
so ``tests/test_window_margin.py`` can shrink each one to 80 % and check that
no audited output changes. A limit that fails that test is sitting too close
to what real documents need; replace it with a structural stop (next item,
Marking, totals row) rather than raising the number.

Each entry: value, then the formats that use it, then what it bounds.
"""

from __future__ import annotations

# --- MA (ma_common / ma_no_period / ma_with_period / ma_ak_billing) ---------
MA_HS_LINES_AFTER_ITEM = 55     # ma_no_period, ma_with_period: lines after an item row to find its HS CODE (also stops at next item)
MA_AK_GROSS_LINES_AFTER_HU = 25  # ma_ak_billing: lines after an HU id to find its Gross
MA_AK_LINES_AFTER_ITEM = 45     # ma_ak_billing: lines after an item for desc / HS / origin (stops at next item / Marking)
MA_WP_COO_INDEX_CHARS = 5000    # ma_with_period: max length of the "Country of origin Index" table
MA_NP_COO_BLOCK_CHARS = 5000    # ma_no_period: COO index block when no end marker is found

# --- eBike / PT ---------------------------------------------------------------
EBIKE_LINES_AFTER_ITEM = 45     # ebike_ax_billing: lines after an item (stops at next item)
PT_H3_LINES_AFTER_ITEM = 45     # pt_dremel_head3: lines after an item
PT_H5_LINES_AFTER_ITEM = 12     # pt_dremel_head5: lines after an item
PT_GLORIA_ORIGIN_HS_LINES = 4   # pt_gloria: range end (i + N) for "CC 12345678" origin + HS under an item

# --- SOE / BITZER -------------------------------------------------------------
SOE_ITEM_WINDOW_CHARS = 450     # soe_rb_gmbh: chars after an item for desc / origin / HS
SOE_PALLETS_GAP_CHARS = 40      # soe_rb_gmbh: OCR cargo-list "N Pallets … <weight>" gap
BITZER_INVNO_GAP_CHARS = 200    # bitzer: label → "no / date" gap
BITZER_PRICE_TAIL_CHARS = 120   # bitzer: chars after unit price to find the line value
BITZER_FINAL_AMOUNT_CHARS = 400  # bitzer: chars after "Final amount"

# --- BHC ----------------------------------------------------------------------
HITACHI_GLS_PKG_LINES = 8       # hitachi_gls: lines after TOTAL to find "N PACKAGES"
HITACHI_GLS_DESC_LINES = 3      # hitachi_gls: range end (i + N) for the description under a row
HITACHI_GLS_PN_LINES = 3        # hitachi_gls (packing block): range end (i + N) for the part no.
HITACHI_GLS_BLOCK_CHARS = 8000  # hitachi_gls: item block when no GRAND TOTAL stop is found
HITACHI_ASIA_BHC_NO_LINES = 8   # hitachi_asia_hitt: range end (i + N) for "BHC NO"
NIDEC_DATE_CHARS = 30           # nidec: chars after "Date"

# --- pairing (generic PKL parser) ---------------------------------------------
PKL_TOTAL_PALLETS_GAP = 20      # "TOTAL … N PALLETS" gap (also blocks wrong picks: 5 PLs grab another number when wider)
PKL_GW_LABEL_GAP = 20           # "G.W. … ####.##" gap

ALL = {k: v for k, v in dict(globals()).items() if k.isupper() and isinstance(v, int)}
