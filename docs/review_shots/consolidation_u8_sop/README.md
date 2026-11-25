# Consolidation U8 — FormatSOP: needs_gold triage + where samples live

Branch `consolidate/u8-sop-needs-gold-triage` (on top of U7g). Docs only.

## What changed
- `docs/sop/ADD_INVOICE_FORMAT.md` (FormatSOP):
  - New section **needs_gold 分流（BHC 人工補值 → Invoice）**, written from the user's decision: two tiers (BHC bot decides obvious document problems; unclear cause or a clean document still extracted wrong = rule defect → Invoice); BHC scans never go into the extractor (人工判讀); supported layout wrong → fix on first occurrence; new layout → FormatSOP at about the 3rd sample; before a new format is live the manually filled shipment still gets a delta marked 人工判讀／待新格式, the user decides on the master file; one row per field in `/workspace/bhc-plan/manual_fill_log.md`, which Invoice reads into the needs_gold list.
  - New section **樣本與 gold 放哪裡**: private sample store + manifest, `private_samples` marker (local fail / CI skip), private gold with `excluded`, review packs without real screenshots.
  - New section **規則寫法的兩條硬規定**: wrap unanchored fallbacks in `fallback()`; fixed windows go in `windows.py` and must pass the 80 % test (fix with a structural boundary, not a bigger number).
  - Step 8 commands updated (`samples.py --check`, baseline default now in the private store); 修訂紀錄 row.
- `docs/sop/AUDIT_SOP.md` §4: same command update + note that missing samples fail.

No code change; tests unaffected.
