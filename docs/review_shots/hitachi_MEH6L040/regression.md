# 回歸 — fix/hitachi-gls-meh6l040 vs main (839bc53)

```
# main worktree
python3 tools/regression_batches.py --baseline /tmp/meh/baseline_main.json --save-baseline
# branch
python3 tools/regression_batches.py --baseline /tmp/meh/baseline_main.json --report regression_report.md
```

| Batch | Invoices | hard | warn | diff vs main | OCR skips | failures |
| --- | --- | --- | --- | --- | --- | --- |
| ma3 | 184 | 0 | 14 | **0** | 20 | 0 |
| pt4 | 23 | 0 | 0 | **0** | 0 | 0 |
| bhc4 | 14 | 0 | 108 | **0** | 11 | 0 |
| bhc5 | 2 | 0 | 1 | **0** | 5 | 0 |
| bhc6 | 19 | 0 | 126 | **0** | 11 | 0 |
| ebike1 | 18 | 0 | 22 | **0** | 0 | 0 |
| soe2 | 10 | 0 | 0 | **0** | 5 | 0 |
| maak | 3 | 0 | 0 | **0** | 0 | 0 |

Baseline differences：0 列。Auditor snapshot differences：0 列。（hard/warn/OCR skip 數與 main 完全相同。）

## 已審 hitachi_gls_v1 樣本逐筆比對（bhc4/5/6 snapshot，main vs branch）

| Batch | 樣本 | main == branch |
| --- | --- | --- |
| bhc4 | MEH6J044（7 列，16 pkg，1,998 kg，18,143,405 JPY） | 相同 |
| bhc5 | （本批沒有 hitachi_gls_v1） | — |
| bhc6 | MEH6K018（2 列，1 pkg，50 kg，294,030 JPY；Co MY/CN） | 相同 |

bhc4/5/6 整批 snapshot 也是逐欄完全相同。另外 fixture 測試 MEH6A036（舊 detail-sheet 版面，16 列，2 pkg，359 kg）照過。

## pytest

522 passed、20 skipped、3 failed —— 3 筆是既有 `tests/test_gui_smoke.py`（本箱沒有 `tkinter`）。新增 7 筆都在 `tests/test_hitachi_gls_meh6l040.py`。
