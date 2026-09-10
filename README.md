## 審核 SOP

規則抽出後必經人工／Auditor：見 [`docs/sop/AUDIT_REVIEW.md`](docs/sop/AUDIT_REVIEW.md)。

# InvoiceExtractor

本地可攜的發票 PDF → JSON 抽取器（規則庫 + 硬校驗）。公司電腦拷資料夾就能跑；沒網路也能用已學會的 format。

## 裝起來

```bash
# 依賴 layout 文字層
pip install -e /workspace/PDF_LayoutText
pip install -e /workspace/InvoiceExtractor
# 或
pip install -r requirements.txt
```

初始化規則庫（會寫入 `data/invoice_formats.db`，含 BITZER + PT Gloria 種子）：

```bash
python -m invoice_extractor --init-db
```

## 用法

```bash
# 抽一張 → 旁輸出 JSON
python -m invoice_extractor path.pdf --out out.json

# 跟金標比（離線，走 checker）
python -m invoice_extractor path.pdf --gold gold.json

# 強制格式
python -m invoice_extractor path.pdf --format bitzer_v1 --out out.json
python -m invoice_extractor path.pdf --format pt_gloria_v1 --out out.json
```

輸出 schema 見 `DESIGN.md`（header / items / meta）。金額會轉成小數（歐式 `6.052,400` → 6052.4）。

## 內建格式

| format_id | 廠商 | 備註 |
|-----------|------|------|
| `bitzer_v1` | BITZER / BHC Versanddokument | 從 BHC_HeaderExtract 移植，樣本 3000214469 |
| `pt_gloria_v1` | Robert Bosch Power Tools GmbH（PT/Gloria） | 用 `pdftotext -layout` 真輸出訓練 |

未命中或文字層空 → `meta.needs_gold` / `needs_ocr`，並寫 placeholder 給人補金標。

## 測試

```bash
pytest -q
```

## Auditor

對帳／語意檢查可丟給 Auditor bot（獨立服務）。本套件本地只做硬校驗。

## 授權

內部工具；樣本發票勿公開推送。
