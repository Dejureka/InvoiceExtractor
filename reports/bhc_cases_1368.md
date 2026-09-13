# BHC cases 1/3/6/8 — FormatSOP

**Date:** 2026-09-13 (Asia/Taipei)

## Result

| case | format_id | new family? | hard | notes |
|------|-----------|-------------|------|-------|
| 1 | hisense_qingdao_v1 | **yes** | pass | Qingdao Hisense Bosch combined INV+PL |
| 3 | aichi_electric_v1 | **yes** | pass | Aichi Electric combined INV+packing sheet |
| 6 | bhc_my_hub_v1 | no (hyphen PN + PKL TOTAL) | pass | INV+PKL split; pkg=3 GW=867 |
| 8 | bhc_my_hub_v1 | no (PKL overlay) | pass | INV+PKL split; pkg=326 GW=3469.5 |

## Code

- New: `formats/hisense_qingdao_v1.py`, `formats/aichi_electric_v1.py`
- Fix: MY-HUB PN regex allows `-` / internal space; `parse_packing_pkg_gw` BHC TOTAL rows
- Seeded BUILTIN + DB

## Audit pack

`docs/review_shots/bhc_cases_1368/` + `out/bhc_cases_1368/`
