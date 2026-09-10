# AuditSOP — 規則抽出後的人工／Auditor 審核（含看圖）

**溝通名稱：`AuditSOP`**  
路徑：`docs/sop/AUDIT_REVIEW.md`  
相關：**FormatSOP**（`ADD_INVOICE_FORMAT.md`）、**RunSOP**（`USER_RUN.md`）。

硬校驗 pass **不等於**結案。每批（或重要單張）都要過這段。  
**Auditor 除了審 JSON，也要看 invoice 圖面，對照匯出數字**（避免只信 pdftotext／規則字串）。

---

## 為何一定要有圖

文字層（poppler／後備）可能：

- 抓到非預期字串、欄位錯位
- 把單價／淨重當成總額／毛重
- 明細列數與畫面不一致

因此審核包必須同時有：**結構化結果（JSON，必要時 Excel 摘要）＋ invoice 頁面圖**。人與 Auditor 都用同一套材料。

---

## 何時跑

- 新 format 種子後
- 全樣本／回歸批次後
- 使用者實測前
- 規則大改後

---

## 步驟

### 1. 本地抽出

- GUI／CLI 跑 PDF（可多檔）→ Excel；審核另存／再出 **JSON**（`--out out.json` 或現行參數）。
- 確認 `meta.checker_verdict`、format_id、文字層 backend。

### 2. 產出審核包（Tools 必做：結果＋圖）

同一輪準備給 Auditor／人眼的材料：

| 材料 | 說明 |
|------|------|
| 規則 JSON | 完整抽出（有 gold 一併附） |
| Excel 摘要（可選） | `Summary`／`Lines` 重點列，或截圖 |
| **Invoice 圖** | 至少首頁；金額／GW／Packing totals／明細密集頁一併產出（`pdftoppm` 等）。路徑例：`out/review_shots/<stem>-p1.png` |

> **是：步驟 2 就要出圖**，不要等到步驟 3 才臨時截。步驟 3～4（人眼＋收斂）與 Auditor 共用同一批圖。

批次可再附 `out/auditor_batch_summary.md`＋點名抽查檔。

### 3. 丟給 Auditor（發票對帳檢查）

一次丟齊：

1. 規則 JSON（＋可選 gold）
2. Invoice 圖（至少關鍵頁）
3. （可選）Excel Summary／Lines 摘要或截圖

請它回：`pass`／`conflict`／`needs_gold`，並明確寫：

- 硬校驗／金標 diff
- **圖面 vs JSON**（invoice_no、金額、LINE／明細列數、G.W. Gross、Incoterm、幣別等）是否一致
- 缺圖或缺 JSON 時不要判 pass

### 4. 人眼抽查（你）

用**同一步驟 2 的圖**對照 JSON／Excel（不必重截，除非圖不夠清楚）：

- 金額是否為畫面上的 Final／Net invoiced 等標籤總額（不是單價）
- G.W. 是否為 Gross（不是 Net）
- 明細列數／數量是否對得上畫面

### 5. 收斂

- Auditor **accept** 且你抽查 OK → 可標「待實測／可釋出」
- `conflict`／圖文不符／缺關鍵欄 → 改規則或補金標，從步驟 1 重跑
- 僅缺 origin／hs／date 等非擋項 → 記待辦，可不擋批次，但要寫進 summary

### 6. 紀錄

把 Auditor 結論＋「已對圖」註記寫進 `reports/` 或 release note；不要只留聊天紀錄。

---

## 反例（不要這樣）

- 只看 hard_check pass 就當完成、沒叫 Auditor
- 只丟 JSON、不附圖，卻要求 Auditor「對畫面」
- 叫 Auditor 自己去開 PDF 抽字或猜路徑
- 圖與金額明顯不符仍標 pass
- 自動改規則寫進庫、沒經人／Auditor 過目

---

## 角色

| 誰 | 做什麼 |
|----|--------|
| Tools／本機 exe | 抽字、規則、硬校驗、產出 Excel／JSON、**產出 invoice 審核用圖** |
| Auditor | 審 JSON（＋可選金標）**＋看圖對照**，回 verdict 與圖文疑點 |
| 你 | 用同批圖抽查、實測、最終收件 |

---

## 修訂紀錄

| 日期 | 說明 |
|------|------|
| 2026-09-10 | 初版（僅 JSON） |
| 2026-09-10 | 改為必看圖；步驟 2 產出 invoice 圖供 3～4 共用；同步 Auditor 職責 |
