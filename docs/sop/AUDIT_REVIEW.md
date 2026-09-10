# SOP：規則抽出後的人工／Auditor 審核

硬校驗 pass **不等于**結案。每批（或重要單張）都要過這段。

## 何時跑

- 新 format 種子後
- 全樣本／回歸批次後
- 使用者實測前
- 規則大改後

## 步驟

1. **本地抽出**  
   `InvoiceExtractor.exe 某.pdf --out out.json`（或 `python -m invoice_extractor`）  
   確認 `meta.checker_verdict` 與 `out/` JSON。

2. **丟給 Auditor（發票對帳檢查）**  
   - 單張：貼完整 JSON（規則輸出；有 gold 就一併附）  
   - 批次：附 `out/auditor_batch_summary.md`＋點名抽查檔  
   - 請它回：`pass`／`conflict`／`needs_gold`、硬校驗、欄位疑點

3. **人眼抽查（你）**  
   對照 invoice 畫面（或首頁截圖）與 JSON：invoice_no、金額、件數、毛重、Incoterm、明細列數。

4. **收斂**  
   - Auditor **accept 批次 pass** 且你抽查 OK → 可標「待實測／可釋出」  
   - `conflict`／缺關鍵欄 → 改規則或補金標，再從步驟 1 重跑  
   - 僅缺 origin／hs／date 等非擋項 → 記待辦，可不擋批次，但要寫進 summary

5. **紀錄**  
   把 Auditor 結論摘要寫進 `reports/` 或 release note；不要只留聊天紀錄。

## 反例（不要這樣）

- 只看 13/13 hard_check pass 就當完成、沒叫 Auditor  
- JSON 訊息貼空、叫 Auditor 自己猜路徑（可附路徑但最好貼 JSON）  
- 自動改規則寫進庫、沒經人／Auditor 過目

## 角色

| 誰 | 做什麼 |
|----|--------|
| Tools／本機 exe | 抽字、規則、硬校驗、產出 JSON |
| Auditor | 審 JSON（＋可選金標）、回 verdict |
| 你 | 實測 portable、最終收件 |
