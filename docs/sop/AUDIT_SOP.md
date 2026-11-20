# AuditSOP（現行）— 全列硬校驗＋抽查

**狀態：現行流程（2026-11-20 起）。** 舊流程保留在 [`AUDIT_REVIEW.md`](AUDIT_REVIEW.md)，當作 legacy／備援。  
**退回方式：** 不跑 `tools/validate_result.py`，直接照 `AUDIT_REVIEW.md` 步驟 1～6 審核即可。本流程是**額外**一步，沒有取代 `hard_check`、既有測試或舊審核步驟；程式也可退回 tag `backup/pre-validate-result`（c0266c6）。

`tools/validate_result.py` 與 `tools/regression_batches.py` 只在原始碼 repo 使用，**刻意不放進 portable**（不在 `src/invoice_extractor/`，PyInstaller spec 不會收）。

---

## 1. 產出同一次抽出的 Excel＋JSON

```bash
cd /workspace/InvoiceExtractor
PYTHONPATH=src python3 -m invoice_extractor <PDF/資料夾…> --out out/audit/Result.xlsx
PYTHONPATH=src python3 -m invoice_extractor <同一批 PDF/資料夾…> --out out/audit/extracts.json
```

（不要加 `--record-run`。）

## 2. 跑全列硬校驗

```bash
python3 tools/validate_result.py out/audit/Result.xlsx --extract-json out/audit/extracts.json --out out/audit/findings.xlsx
# 也可輸出 .md；只有 JSON 時：python3 tools/validate_result.py --extract-json <檔或資料夾> --out findings.md
```

- 每個 finding 一列：`status`（ok／warn／hard）、`rule_id`、`invoice_no`、`row`、`field`、`expected`、`actual`、`page`、`position`（座標框或文字錨點）、`note`；另有 Summary 分頁。
- 有任何 hard → exit code 1。
- 規則（`H_*`＝hard，`W_*`＝warn）：表頭必填（invoice_no／date／currency／amount／pkg／GW）、日期可解析、ISO 4217 幣別、首張 pkg 為正整數、明細料號／qty／amount 不可空、列數＝印的列數且項次連續、qty×單價≈金額（容差＝|qty÷pricing_unit|×單價印出最小位數/2＋金額印出最小位數/2，位數取自印出文字，拿不到用 0.01；差額＞容差才 hard，容差內 ok，Auditor 2026-11-20）、明細加總＝印出的標籤總額（容差維持 0.01，不放寬）、pkg／GW＝印出值（依格式規則）、GW 不可小於或等於 NW 合計、HS 格式（MA／PT／SOE 缺 HS＝hard，BHC／eBike＝warn）、同 BL 的 pkg／GW 合計＝BL、同批發票號不可重複、Result.xlsx 與 JSON 逐格一致（含前導 0、文字型數字、科學記號、Unt 6 位小數）。
- 依既有文件規則編碼的例外（都是 warn，不是放寬）：shipment_first 非首張 0＋附註寫印出值（沒附註＝hard）；BHC PDF／Excel twin（`W_TWIN`、`W_TWIN_PKG_BLANK`，BL 合計 twin 只算一次；兩邊都空或不一致＝hard）；saginomiya 發票無 GW、附註寫用 BL G.W.（`W_GW_FROM_BL`）；sanhua PDF 未印 PN、附註註明（`W_PN_BLANK_PRINTED`）；eBike 單列 NW 大於合計（`W_LINE_NW`）、Copy／NOT VALID（`W_WATERMARK`）、EUR＋HUF（`W_DUAL_CURRENCY`）。
- `needs_gold` 發票照跑；標了 needs_gold 的欄位，發現降為 warn。
- 船名、航次、ETA／ETD、CBM、櫃號一律不檢查。

## 3. Auditor 審核（通過條件）

a. **hard 與 warn 每一列都要看**（依 page／position 裁圖對照）。  
b. **每張發票的合計區截圖**（件數 pkg／毛重 GW／金額 amount）都要看。  
c. **每張發票隨機抽查明細**：至少 3 列或 10%（無條件進位），取較大者；不足 3 列全看。**不可只抽頭尾**。新格式第一批逐列全看。  
d. **腳本 hard＝0（warn 都有解釋）且抽查乾淨才給 pass。** 抽查抓到錯誤時，先在 `tools/validate_result.py` 補一條能抓到它的規則（附測試），重跑再重審。

舊流程的圖文對照、角色分工、反例清單仍適用（見 `AUDIT_REVIEW.md`）。

## 4. 回歸（改任何格式前後）

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_validate_result.py tests/test_gold_regression.py
python3 tools/regression_batches.py --baseline out/regress/baseline --report out/regress/report.md
# 第一次或在已審核通過的版本上重建基線：
python3 tools/regression_batches.py --baseline out/regress/baseline --save-baseline --report out/regress/baseline-report.md
```

- `tests/gold/` 是已審核批次（MA 3rd、PT 4th、BHC 4th～6th、eBike 1st、SOE 2nd、MA AK 74096）凍結的 Result 欄位；不含 needs_gold 及本機無法 OCR 的檔案。差異必須是 0。
- 回歸報告逐列列出（批次、發票、欄位、基線值、現值），非 0 要逐筆說明給 Auditor。
- 本機沒有 tesseract 時，OCR 檔案會跳過，不算回歸。

## 修訂紀錄

| 日期 | 說明 |
|------|------|
| 2026-11-20 | 明細列 qty×單價 容差改依印出位數（AK00074096 110／120／140 印出差 1 TWD → ok）；總額比對不變。 |
| 2026-11-20 | 新增：全列硬校驗 `tools/validate_result.py`＋金標回歸＋抽查規則（Invoice＋Auditor 共同議定）。舊流程保留為 `AUDIT_REVIEW.md`。 |
