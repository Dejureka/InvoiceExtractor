# BHC cases 1/3/6/8 — FormatSOP audit pack

**Date:** 2026-09-13 (Asia/Taipei)  
**Scope:** text-layer only (no OCR). Skip .msg / 到貨 / HBL-only / scan / gift-xlsx-as-source.

| case | format_id | invoice_no | amount | currency | lines | pkg | GW | source | hard |
|------|-----------|------------|--------|----------|-------|-----|-----|--------|------|
| 1 | `hisense_qingdao_v1` **NEW** | CIHT-TW-26080473 | 361115 | USD | 7 | 169 | 45986 | combined | pass |
| 3 | `aichi_electric_v1` **NEW** | AETW26012 | 7530464 | JPY | 17 | 12 | 7217 | combined | pass |
| 6 | `bhc_my_hub_v1` (hyphen PN fix) | 9027519666 | 12026.90 | USD | 4 | 3 | 867 | split INV+PKL | pass |
| 8 | `bhc_my_hub_v1` + PKL overlay | 9027666020 | 119636.08 | USD | 20 | 326 | 3469.5 | split INV+PKL | pass |

## Materials

- JSON: `docs/review_shots/bhc_cases_1368/*.json` (also `out/bhc_cases_1368/json/`)
- Shots: same folder `*_p1.png` (+ packing p2 / PKL p1)

## Notes for Auditor

- **case1**: xlsx is gold hint only (not extract source). PN = SELLER'S MODEL; HS soft-missing OK.
- **case3**: Total FOB Nagoya labeled amount; HS soft-missing OK.
- **case6/8**: MY-HUB; packing/GW from paired PKL. Case6 PNs include hyphens / internal space (`RPK-GP80K3M B`).
- Hard pass ≠ final accept — please confirm figure vs JSON (invoice_no, labeled total, LINE/qty, Gross GW, Incoterm, currency).

## Skipped in folders

- case1: `.msg`, gift xlsx as source, jpg
- case3: HBL draft + `.msg`
- case6: 到貨 298.pdf + `.msg`
- case8: scan `20260904232648-0001.pdf` + `.msg` + xlsx as source
