"""Simple tkinter GUI for InvoiceExtractor (drag-drop optional via tkinterdnd2).

Adds INV+PKL+提單 pairing table under Selected files (BHC split-first; MA combined OK).
"""

from __future__ import annotations

import sys
import threading
import traceback
from pathlib import Path
from typing import Any

from invoice_extractor.pairing import (
    STATUS_BL_ONLY,
    STATUS_INV_ONLY,
    STATUS_INV_PKL,
    STATUS_PKL_ONLY,
    STATUS_UNMATCHED,
    PairRow,
    auto_pair,
    extract_pair_row,
)


def _parse_dnd_paths(raw: str) -> list[str]:
    """Parse tkinterdnd2 drop payload (brace-quoted paths with spaces)."""
    parts: list[str] = []
    cur = ""
    in_brace = False
    for ch in raw:
        if ch == "{":
            in_brace = True
            cur = ""
        elif ch == "}":
            in_brace = False
            parts.append(cur)
            cur = ""
        elif ch == " " and not in_brace:
            if cur:
                parts.append(cur)
                cur = ""
        else:
            cur += ch
    if cur:
        parts.append(cur)
    return [p.strip().strip("{}") for p in parts if p.strip()]


def _expand_pdf_inputs(paths: list[str]) -> list[Path]:
    """Turn dropped/selected paths into PDF/Excel files (directories expanded)."""
    from invoice_extractor.cli import collect_pdfs

    files, _errs = collect_pdfs(paths)
    return files


def _extract_one(pdf: Path) -> dict[str, Any]:
    """Run extract + hard check for a single PDF (combined / legacy path)."""
    row = PairRow(pair_id="P1", inv_path=pdf, status=STATUS_INV_ONLY)
    data = extract_pair_row(row)
    if data is None:
        raise RuntimeError(f"Skipped or empty extract: {pdf}")
    return data


def _extract_many(pdfs: list[Path], out: Path | None) -> dict[str, Any]:
    """Legacy: treat each PDF as its own pair (no cross-file merge)."""
    rows = auto_pair(pdfs)
    return _extract_pairs(rows, out)


def _extract_pairs(rows: list[PairRow], out: Path | None) -> dict[str, Any]:
    """Extract pair rows into one Excel (or JSON); surface partial failures / skips."""
    from invoice_extractor.export import (
        default_result_path,
        is_json_out,
        write_extract,
        write_extracts,
    )

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for row in rows:
        if row.skipped:
            skipped.append(
                {
                    "pair_id": row.pair_id,
                    "inv": row.display_inv,
                    "pkl": row.display_pkl,
                    "reason": "skipped by user",
                }
            )
            summaries.append(
                {
                    "ok": False,
                    "skipped": True,
                    "source": str(row.inv_path or row.pkl_path or ""),
                    "pair_status": row.status,
                    "error": "skipped",
                    "mapping_status": "—",
                    "format_id": None,
                    "checker_verdict": None,
                }
            )
            continue
        if row.status == STATUS_PKL_ONLY or (
            row.pkl_path and not row.inv_path and not row.bl_path
        ):
            skipped.append(
                {
                    "pair_id": row.pair_id,
                    "inv": row.display_inv,
                    "pkl": row.display_pkl,
                    "bl": row.display_bl,
                    "reason": "PKL-only (no invoice row)",
                }
            )
            summaries.append(
                {
                    "ok": False,
                    "skipped": True,
                    "source": str(row.pkl_path or ""),
                    "pair_status": STATUS_PKL_ONLY,
                    "error": "僅 PKL — 不寫 Summary／Lines",
                    "mapping_status": "—",
                    "format_id": None,
                    "checker_verdict": None,
                }
            )
            continue

        label = row.inv_path or row.bl_path or row.pkl_path
        try:
            data = extract_pair_row(row)
            if data is None:
                skipped.append(
                    {
                        "pair_id": row.pair_id,
                        "inv": row.display_inv,
                        "pkl": row.display_pkl,
                        "reason": "extract returned None",
                    }
                )
                continue
            hard = data.pop("_hard")
            pair_status = data.pop("_pair_status", None) or row.status
            data.pop("_pair_id", None)
            successes.append(data)
            header = data.get("header") or {}
            meta = data.get("meta") or {}
            from invoice_extractor.mapping_status import mapping_status

            map_label = mapping_status(meta, hard["verdict"])
            summaries.append(
                {
                    "ok": True,
                    "source": str(label),
                    "invoice_no": header.get("invoice_no"),
                    "amount": header.get("amount"),
                    "item_count": len(data.get("items") or []),
                    "format_id": meta.get("format_id"),
                    "checker_verdict": hard["verdict"],
                    "mapping_status": map_label,
                    "pair_status": pair_status or meta.get("pair_status"),
                    "bl_no": header.get("bl_no"),
                    "bl_packages": header.get("bl_packages"),
                    "bl_gross_weight_kg": header.get("bl_gross_weight_kg"),
                    "issues": hard.get("issues") or [],
                    "text_backend": meta.get("text_backend"),
                    "text_backend_warning": meta.get("text_backend_warning"),
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "source_file": str(label),
                    "error": str(exc),
                    "meta": {"source_file": str(label)},
                }
            )
            summaries.append(
                {
                    "ok": False,
                    "source": str(label),
                    "error": str(exc),
                    "mapping_status": "全新／需規則",
                    "pair_status": row.status,
                    "format_id": None,
                    "checker_verdict": None,
                }
            )

    if not successes:
        return {
            "ok": False,
            "written": None,
            "successes": 0,
            "failures": failures,
            "skipped": skipped,
            "summaries": summaries,
            "error": "All files failed or skipped; nothing written.",
        }

    if out is None:
        dest = default_result_path()
    else:
        dest = out

    if is_json_out(dest) and len(successes) == 1 and not failures:
        written = write_extract(successes[0], dest)
    else:
        written = write_extracts(successes, dest, failures=failures)

    return {
        "ok": len(failures) == 0,
        "written": str(written),
        "successes": len(successes),
        "failures": failures,
        "skipped": skipped,
        "summaries": summaries,
    }


def run_gui() -> None:
    """Launch GUI; requires tkinter (optional tkinterdnd2 for drag-drop)."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext, ttk
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "GUI needs tkinter. Use CLI instead:\n"
            "  python -m invoice_extractor path.pdf\n"
            f"Original error: {exc}"
        ) from exc

    has_dnd = False
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD

        has_dnd = True
    except Exception:
        DND_FILES = None  # type: ignore
        TkinterDnD = None  # type: ignore

    class App:
        def __init__(self) -> None:
            self._busy = False
            self._pdfs: list[Path] = []
            self._pairs: list[PairRow] = []
            self._build()

        def _make_root(self):
            if has_dnd:
                root = TkinterDnD.Tk()
            else:
                root = tk.Tk()
            root.title("InvoiceExtractor — Published by Peter Yang")
            root.geometry("820x720")
            root.minsize(560, 520)
            return root

        def _build(self) -> None:
            self.root = self._make_root()
            pad = {"padx": 8, "pady": 4}

            frm_pdf = ttk.LabelFrame(self.root, text="Files (PDF / Excel; multi-select / folders OK)")
            frm_pdf.pack(fill="x", **pad)
            self.pdf_var = tk.StringVar()
            ttk.Entry(frm_pdf, textvariable=self.pdf_var).pack(
                side="left", fill="x", expand=True, padx=4, pady=4
            )
            ttk.Button(frm_pdf, text="Browse…", command=self._browse_pdf).pack(
                side="left", padx=2, pady=4
            )
            ttk.Button(frm_pdf, text="Add folder…", command=self._browse_folder).pack(
                side="left", padx=2, pady=4
            )

            frm_drop = ttk.LabelFrame(
                self.root,
                text="Drop zone (PDF / Excel / folder)"
                + (" — drag-drop on" if has_dnd else " — use Browse"),
            )
            frm_drop.pack(fill="x", **pad)
            self.drop_label = ttk.Label(
                frm_drop,
                text="Drop PDFs/Excel or a folder here, or use Browse",
                anchor="center",
                padding=20,
            )
            self.drop_label.pack(fill="x", padx=8, pady=8)
            if has_dnd:
                try:
                    self.drop_label.drop_target_register(DND_FILES)
                    self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
                except Exception:
                    pass

            frm_list = ttk.LabelFrame(self.root, text="Selected files")
            frm_list.pack(fill="x", **pad)
            self.listbox = tk.Listbox(frm_list, height=4, selectmode="extended")
            self.listbox.pack(fill="x", expand=True, padx=4, pady=4)

            frm_pair = ttk.LabelFrame(
                self.root,
                text="配對 (INV+PKL+提單) — Extract 前可手配 PKL／提單／拆開／略過",
            )
            frm_pair.pack(fill="both", expand=False, **pad)
            cols = ("pair", "inv", "pkl", "bl", "status")
            self.pair_tree = ttk.Treeview(
                frm_pair,
                columns=cols,
                show="headings",
                height=5,
                selectmode="browse",
            )
            self.pair_tree.heading("pair", text="配對")
            self.pair_tree.heading("inv", text="INV")
            self.pair_tree.heading("pkl", text="PKL")
            self.pair_tree.heading("bl", text="提單")
            self.pair_tree.heading("status", text="狀態")
            self.pair_tree.column("pair", width=50, anchor="center")
            self.pair_tree.column("inv", width=200)
            self.pair_tree.column("pkl", width=200)
            self.pair_tree.column("bl", width=180)
            self.pair_tree.column("status", width=110, anchor="center")
            self.pair_tree.pack(fill="x", padx=4, pady=4)

            frm_pair_btns = ttk.Frame(frm_pair)
            frm_pair_btns.pack(fill="x", padx=4, pady=(0, 4))
            ttk.Button(
                frm_pair_btns, text="手配 PKL…", command=self._rematch_pkl
            ).pack(side="left", padx=2)
            ttk.Button(
                frm_pair_btns, text="手配 提單…", command=self._rematch_bl
            ).pack(side="left", padx=2)
            ttk.Button(frm_pair_btns, text="拆開", command=self._split_pair).pack(
                side="left", padx=2
            )
            ttk.Button(frm_pair_btns, text="略過", command=self._skip_pair).pack(
                side="left", padx=2
            )
            ttk.Button(
                frm_pair_btns, text="重新自動配對", command=self._rebuild_pairs
            ).pack(side="left", padx=2)

            from invoice_extractor.export import DEFAULT_RESULT_NAME

            frm_out = ttk.LabelFrame(
                self.root,
                text=f"Output (optional; default: {DEFAULT_RESULT_NAME} at tool root)",
            )
            frm_out.pack(fill="x", **pad)
            self.out_var = tk.StringVar()
            ttk.Entry(frm_out, textvariable=self.out_var).pack(
                side="left", fill="x", expand=True, padx=4, pady=4
            )
            ttk.Button(frm_out, text="Browse…", command=self._browse_out).pack(
                side="left", padx=4, pady=4
            )

            frm_btns = ttk.Frame(self.root)
            frm_btns.pack(fill="x", **pad)
            self.run_btn = ttk.Button(
                frm_btns, text="Extract", command=self._run_extract
            )
            self.run_btn.pack(side="right", padx=4)
            ttk.Button(frm_btns, text="Clear", command=self._clear).pack(
                side="right", padx=4
            )

            frm_ocr = ttk.Frame(self.root)
            frm_ocr.pack(fill="x", **pad)
            self.ocr_btn = ttk.Button(
                frm_ocr,
                text="OCR 成可複製 PDF",
                command=self._run_ocr_pdf,
            )
            self.ocr_btn.pack(side="left", padx=4)
            ttk.Label(
                frm_ocr,
                text="掃描 PDF → ocr_out/{檔名}.ocr.pdf（獨立於 Extract）",
            ).pack(side="left", padx=4)

            frm_sum = ttk.LabelFrame(self.root, text="Summary")
            frm_sum.pack(fill="both", expand=True, **pad)
            self.summary = scrolledtext.ScrolledText(frm_sum, height=10, wrap="word")
            self.summary.pack(fill="both", expand=True, padx=4, pady=4)

            self.author_var = tk.StringVar(value="Published by Peter Yang")
            author = ttk.Label(
                self.root,
                textvariable=self.author_var,
                anchor="e",
                foreground="#555555",
            )
            author.pack(fill="x", side="bottom", padx=8, pady=(0, 2))

            self.status_var = tk.StringVar(
                value="Ready — pairing: INV+PKL / 僅 INV / 僅 PKL / 僅 提單 / 未配對；mapping: audit ok / 已知未審 / 全新／需規則 / hard fail"
            )
            status = ttk.Label(
                self.root, textvariable=self.status_var, relief="sunken", anchor="w"
            )
            status.pack(fill="x", side="bottom", padx=4, pady=2)

            dnd_note = "enabled" if has_dnd else "not installed (Browse still works)"
            self._log(f"Drag-drop: {dnd_note}")
            self._log(
                "INV+PKL+提單: BHC 分檔為主；到貨／HBL 配入 Summary BL 欄。Extract 前可手配 PKL／提單。"
            )
            try:
                from pdf_layout_text.convert import find_pdftotext
                from invoice_extractor.text_layer import backend_warning
                from invoice_extractor.ocr import find_tesseract, tesseract_available

                if find_pdftotext():
                    self._log("Text engine: pdftotext (poppler) available")
                else:
                    self._log(
                        "WARNING: "
                        + (backend_warning("pymupdf/pdfminer fallback") or "")
                    )
                if tesseract_available():
                    self._log(f"OCR fallback: tesseract available ({find_tesseract()})")
                else:
                    self._log(
                        "OCR fallback: tesseract not found "
                        "(empty-text PDFs will stay needs_ocr; "
                        "see README / portable-ocr-test)"
                    )
            except Exception as exc:
                self._log(f"(text engine probe skipped: {exc})")

        def _log(self, msg: str) -> None:
            self.summary.insert("end", msg + "\n")
            self.summary.see("end")

        def _sync_pdf_var(self) -> None:
            self.listbox.delete(0, "end")
            for p in self._pdfs:
                self.listbox.insert("end", str(p))
            if not self._pdfs:
                self.pdf_var.set("")
            elif len(self._pdfs) == 1:
                self.pdf_var.set(str(self._pdfs[0]))
            else:
                self.pdf_var.set(f"{len(self._pdfs)} files selected")
            self._rebuild_pairs()

        def _rebuild_pairs(self) -> None:
            # Preserve manual overrides where possible by path keys
            manual = {
                (str(r.inv_path) if r.inv_path else "", str(r.pkl_path) if r.pkl_path else ""): r
                for r in self._pairs
                if r.manual or r.skipped
            }
            self._pairs = auto_pair(self._pdfs)
            # Re-apply skip/manual rematches that still reference selected files
            selected = {str(p.resolve()) if p.exists() else str(p) for p in self._pdfs}
            for key, old in manual.items():
                inv_s, pkl_s = key
                if old.skipped:
                    for r in self._pairs:
                        if (str(r.inv_path or "") == inv_s) or (
                            str(r.pkl_path or "") == pkl_s
                        ):
                            r.skipped = True
                            r.manual = True
                elif old.manual and old.inv_path and old.pkl_path:
                    inv_ok = str(old.inv_path.resolve()) if old.inv_path.exists() else str(old.inv_path)
                    pkl_ok = str(old.pkl_path.resolve()) if old.pkl_path.exists() else str(old.pkl_path)
                    if inv_ok in selected and pkl_ok in selected:
                        # force this pairing
                        for r in self._pairs:
                            if r.inv_path and str(r.inv_path.resolve()) == inv_ok:
                                r.pkl_path = old.pkl_path
                                r.manual = True
                                r.recompute_status()
                            elif r.pkl_path and str(r.pkl_path.resolve()) == pkl_ok:
                                if not (r.inv_path and str(r.inv_path.resolve()) == inv_ok):
                                    r.pkl_path = None
                                    r.recompute_status()
            self._sync_pair_tree()

        def _sync_pair_tree(self) -> None:
            for iid in self.pair_tree.get_children():
                self.pair_tree.delete(iid)
            for r in self._pairs:
                status = r.status + (" [略過]" if r.skipped else "")
                self.pair_tree.insert(
                    "",
                    "end",
                    iid=r.pair_id,
                    values=(r.pair_id, r.display_inv, r.display_pkl, r.display_bl, status),
                )

        def _selected_pair(self) -> PairRow | None:
            sel = self.pair_tree.selection()
            if not sel:
                return None
            pid = sel[0]
            for r in self._pairs:
                if r.pair_id == pid:
                    return r
            return None

        def _rematch_pkl(self) -> None:
            row = self._selected_pair()
            if not row:
                messagebox.showinfo("手配 PKL", "請先在配對表選一列。")
                return
            if not row.inv_path:
                messagebox.showwarning("手配 PKL", "此列沒有 INV，無法手配。")
                return
            inv_key = str(row.inv_path.resolve()) if row.inv_path.exists() else str(row.inv_path)
            path = filedialog.askopenfilename(
                title="選擇要配給此 INV 的 PKL 檔",
                filetypes=[("PDF/Excel", "*.pdf *.PDF *.xlsx *.xlsm *.xls"), ("PDF", "*.pdf *.PDF"), ("Excel", "*.xlsx *.xlsm *.xls"), ("All", "*.*")],
                initialdir=str(row.inv_path.parent) if row.inv_path else None,
            )
            if not path:
                return
            pkl = Path(path)
            # Add to selection without wiping manual state via full rebuild
            seen = {str(p.resolve()) if p.exists() else str(p) for p in self._pdfs}
            key = str(pkl.resolve()) if pkl.exists() else str(pkl)
            if key not in seen:
                self._pdfs.append(pkl)
                self.listbox.insert("end", str(pkl))
                self.pdf_var.set(f"{len(self._pdfs)} files selected")
            # Detach this PKL from any other pair; bind to this INV
            for r in self._pairs:
                if r.inv_path and (
                    (str(r.inv_path.resolve()) if r.inv_path.exists() else str(r.inv_path))
                    == inv_key
                ):
                    r.pkl_path = pkl
                    r.manual = True
                    r.skipped = False
                    r.recompute_status()
                elif r.pkl_path and r.pkl_path.resolve() == pkl.resolve():
                    if not (
                        r.inv_path
                        and (
                            str(r.inv_path.resolve())
                            if r.inv_path.exists()
                            else str(r.inv_path)
                        )
                        == inv_key
                    ):
                        r.pkl_path = None
                        r.recompute_status()
            # Drop orphan PKL-only rows for this file
            self._pairs = [
                r
                for r in self._pairs
                if not (
                    r.status == STATUS_PKL_ONLY
                    and r.pkl_path
                    and r.pkl_path.resolve() == pkl.resolve()
                )
            ]
            self._sync_pair_tree()
            self._log(f"手配 PKL: INV={Path(inv_key).name} → PKL={pkl.name}")

        def _rematch_bl(self) -> None:
            row = self._selected_pair()
            if not row:
                messagebox.showinfo("手配 提單", "請先在配對表選一列。")
                return
            if not row.inv_path:
                messagebox.showwarning("手配 提單", "此列沒有 INV，無法手配。")
                return
            inv_key = str(row.inv_path.resolve()) if row.inv_path.exists() else str(row.inv_path)
            path = filedialog.askopenfilename(
                title="選擇要配給此 INV 的提單檔",
                filetypes=[("PDF/Excel", "*.pdf *.PDF *.xlsx *.xlsm *.xls"), ("PDF", "*.pdf *.PDF"), ("Excel", "*.xlsx *.xlsm *.xls"), ("All", "*.*")],
                initialdir=str(row.inv_path.parent) if row.inv_path else None,
            )
            if not path:
                return
            bl = Path(path)
            # Add to selection without wiping manual state via full rebuild
            seen = {str(p.resolve()) if p.exists() else str(p) for p in self._pdfs}
            key = str(bl.resolve()) if bl.exists() else str(bl)
            if key not in seen:
                self._pdfs.append(bl)
                self.listbox.insert("end", str(bl))
                self.pdf_var.set(f"{len(self._pdfs)} files selected")
            # Detach this BL from any other pair; bind to this INV
            for r in self._pairs:
                if r.inv_path and (
                    (str(r.inv_path.resolve()) if r.inv_path.exists() else str(r.inv_path))
                    == inv_key
                ):
                    r.bl_path = bl
                    r.manual = True
                    r.skipped = False
                    r.recompute_status()
                elif r.bl_path and r.bl_path.resolve() == bl.resolve():
                    if not (
                        r.inv_path
                        and (
                            str(r.inv_path.resolve())
                            if r.inv_path.exists()
                            else str(r.inv_path)
                        )
                        == inv_key
                    ):
                        r.bl_path = None
                        r.recompute_status()
            # Drop orphan BL-only rows for this file
            self._pairs = [
                r
                for r in self._pairs
                if not (
                    r.status == STATUS_BL_ONLY
                    and r.bl_path
                    and r.bl_path.resolve() == bl.resolve()
                )
            ]
            self._sync_pair_tree()
            self._log(f"手配 提單: INV={Path(inv_key).name} → BL={bl.name}")

        def _split_pair(self) -> None:
            row = self._selected_pair()
            if not row:
                messagebox.showinfo("拆開", "請先在配對表選一列。")
                return
            if not row.pkl_path:
                messagebox.showinfo("拆開", "此列沒有 PKL。")
                return
            pkl = row.pkl_path
            row.pkl_path = None
            row.manual = True
            row.skipped = False
            row.recompute_status()
            # Add PKL-only row if not already present
            exists = any(
                r.pkl_path and r.pkl_path.resolve() == pkl.resolve() and not r.inv_path
                for r in self._pairs
            )
            if not exists:
                n = len(self._pairs) + 1
                self._pairs.append(
                    PairRow(
                        pair_id=f"P{n}",
                        pkl_path=pkl,
                        status=STATUS_PKL_ONLY,
                        manual=True,
                    )
                )
            self._sync_pair_tree()
            self._log(f"拆開: {row.pair_id} → 僅 INV；PKL={pkl.name} 獨立列")

        def _skip_pair(self) -> None:
            row = self._selected_pair()
            if not row:
                messagebox.showinfo("略過", "請先在配對表選一列。")
                return
            row.skipped = not row.skipped
            row.manual = True
            self._sync_pair_tree()
            self._log(
                f"{'略過' if row.skipped else '取消略過'}: {row.pair_id} {row.display_inv}"
            )

        def _set_pdfs(self, paths: list[Path], *, append: bool = False) -> None:
            if not append:
                self._pdfs = []
            seen = {str(p.resolve()) if p.exists() else str(p) for p in self._pdfs}
            for p in paths:
                key = str(p.resolve()) if p.exists() else str(p)
                if key not in seen:
                    seen.add(key)
                    self._pdfs.append(p)
            self._sync_pdf_var()

        def _clear(self) -> None:
            self._pdfs = []
            self._pairs = []
            self.pdf_var.set("")
            self.out_var.set("")
            self.listbox.delete(0, "end")
            self._sync_pair_tree()
            self.summary.delete("1.0", "end")
            if hasattr(self, "status_var"):
                self.status_var.set(
                    "Ready — pairing: INV+PKL / 僅 INV / 僅 PKL / 僅 提單 / 未配對；mapping: audit ok / 已知未審 / 全新／需規則 / hard fail"
                )
            dnd_note = "enabled" if has_dnd else "not installed (Browse still works)"
            self._log(f"Drag-drop: {dnd_note}")

        def _on_drop(self, event) -> None:
            parts = _parse_dnd_paths(event.data)
            if not parts:
                self._log("Drop ignored: empty payload")
                return
            pdfs = _expand_pdf_inputs(parts)
            if not pdfs:
                self._log("Drop ignored: no PDF/Excel inputs found")
                return
            self._set_pdfs(pdfs, append=True)
            self._log(f"Added {len(pdfs)} file(s); total {len(self._pdfs)}")

        def _browse_pdf(self) -> None:
            paths = filedialog.askopenfilenames(
                title="Select invoice PDF/Excel file(s)",
                filetypes=[
                    ("PDF/Excel", "*.pdf *.PDF *.xlsx *.xlsm *.xls"),
                    ("PDF", "*.pdf *.PDF"),
                    ("Excel", "*.xlsx *.xlsm *.xls"),
                    ("All", "*.*"),
                ],
            )
            if paths:
                files = _expand_pdf_inputs(list(paths))
                if not files:
                    messagebox.showwarning(
                        "No inputs",
                        "No usable PDF/Excel files selected "
                        "(tool Result/Template Excel are skipped).",
                    )
                    return
                self._set_pdfs(files, append=True)
                self._log(f"Selected {len(files)} file(s); total {len(self._pdfs)}")

        def _browse_folder(self) -> None:
            folder = filedialog.askdirectory(title="Select folder of invoice PDF/Excel files")
            if folder:
                pdfs = _expand_pdf_inputs([folder])
                if not pdfs:
                    messagebox.showwarning(
                        "No inputs",
                        f"No PDF/Excel files in:\n{folder}\n"
                        "(tool Result/Template Excel and ocr_out/ are skipped)",
                    )
                    return
                self._set_pdfs(pdfs, append=True)
                self._log(f"Added folder ({len(pdfs)} files); total {len(self._pdfs)}")

        def _browse_out(self) -> None:
            path = filedialog.asksaveasfilename(
                title="Save extract as",
                defaultextension=".xlsx",
                initialfile="InvoiceExtract_Result.xlsx",
                filetypes=[
                    ("Excel", "*.xlsx"),
                    ("JSON", "*.json"),
                    ("All", "*.*"),
                ],
            )
            if path:
                self.out_var.set(path)


        def _run_ocr_pdf(self) -> None:
            """Standalone: multi-select scan PDFs → searchable PDFs in ocr_out/."""
            if self._busy:
                return
            paths = filedialog.askopenfilenames(
                title="Select scan PDF(s) for OCR → searchable PDF",
                filetypes=[("PDF", "*.pdf"), ("All", "*.*")],
            )
            if not paths:
                return
            pdfs = []
            skipped = []
            for raw in paths:
                pdf = Path(raw)
                if not pdf.is_file():
                    messagebox.showerror("Not found", f"File not found:\n{pdf}")
                    return
                if pdf.suffix.lower() != ".pdf":
                    skipped.append(pdf.name)
                    continue
                pdfs.append(pdf)
            if skipped:
                messagebox.showwarning(
                    "OCR skips non-PDF",
                    "OCR only accepts PDF. Skipped:\n" + "\n".join(skipped),
                )
            if not pdfs:
                return

            from invoice_extractor.ocr import (
                default_ocr_out_dir,
                find_tesseract,
                pdfs_to_searchable_pdfs,
                resolve_ocr_lang,
                tesseract_available,
            )

            if not tesseract_available():
                messagebox.showerror(
                    "OCR unavailable",
                    "tesseract not found.\n"
                    "Install Tesseract OCR, set TESSERACT_CMD, "
                    "or place portable tesseract/ next to the app.",
                )
                return

            out_dir = default_ocr_out_dir()
            lang = resolve_ocr_lang(find_tesseract())
            self._busy = True
            self.ocr_btn.configure(state="disabled")
            # Keep Extract usable? Spec says don't block Extract — only disable OCR btn
            # but _busy is shared; allow Extract by not using shared busy for OCR,
            # or use separate flag. Use _ocr_busy to avoid blocking Extract.
            self._busy = False
            self._ocr_busy = True
            self._log(
                f"OCR → searchable PDF: {len(pdfs)} file(s) → {out_dir} (lang={lang}) …"
            )

            def work() -> None:
                try:
                    written, failures = pdfs_to_searchable_pdfs(pdfs, out_dir, lang=lang)

                    def ok() -> None:
                        lines = [f"OCR output dir: {out_dir}", f"lang: {lang}", "—"]
                        for w in written:
                            lines.append(f"OK  {w}")
                        for src, err in failures:
                            lines.append(f"FAIL {src}: {err}")
                        self._log("\n".join(lines))
                        msg = (
                            f"Wrote {len(written)} file(s) under:\n{out_dir}\n\n"
                            + "\n".join(str(w.name) for w in written)
                        )
                        if failures:
                            msg += "\n\nFailures:\n" + "\n".join(
                                f"- {s.name}: {e}" for s, e in failures
                            )
                            messagebox.showwarning("OCR done (with failures)", msg)
                        else:
                            open_folder = messagebox.askyesno(
                                "OCR done",
                                msg + "\n\nOpen ocr_out folder?",
                            )
                            if open_folder:
                                try:
                                    import os
                                    import subprocess

                                    if hasattr(os, "startfile"):
                                        os.startfile(str(out_dir))  # type: ignore[attr-defined]
                                    elif sys.platform == "darwin":
                                        subprocess.Popen(["open", str(out_dir)])
                                    else:
                                        subprocess.Popen(["xdg-open", str(out_dir)])
                                except Exception as exc:
                                    self._log(f"(open folder failed: {exc})")

                    self.root.after(0, ok)
                except Exception:
                    err = traceback.format_exc()

                    def fail() -> None:
                        self._log("OCR ERROR:\n" + err)
                        messagebox.showerror("OCR failed", err[-800:])

                    self.root.after(0, fail)
                finally:

                    def done() -> None:
                        self._ocr_busy = False
                        self.ocr_btn.configure(state="normal")

                    self.root.after(0, done)

            threading.Thread(target=work, daemon=True).start()

        def _run_extract(self) -> None:
            if self._busy:
                return
            typed = self.pdf_var.get().strip().strip('"')
            if typed and not typed.endswith("files selected") and not typed.endswith("PDFs selected") and Path(typed).is_file():
                if not self._pdfs or str(self._pdfs[0]) != typed:
                    self._set_pdfs([Path(typed)], append=False)

            if not self._pdfs:
                messagebox.showwarning(
                    "Missing PDF", "Select or drop one or more PDFs first."
                )
                return
            for pdf in self._pdfs:
                if not pdf.is_file():
                    messagebox.showerror("Not found", f"File not found:\n{pdf}")
                    return
            out_s = self.out_var.get().strip().strip('"')
            out = Path(out_s) if out_s else None

            if not self._pairs:
                self._rebuild_pairs()
            pairs = list(self._pairs)

            self._busy = True
            self.run_btn.configure(state="disabled")
            active = sum(
                1 for r in pairs
                if not r.skipped and r.status != STATUS_PKL_ONLY
            )
            self._log(f"Extracting {active} pair(s) from {len(self._pdfs)} file(s) …")

            def work() -> None:
                try:
                    result = _extract_pairs(pairs, out)

                    def ok() -> None:
                        self._show_batch(result)
                        fails = result.get("failures") or []
                        skips = result.get("skipped") or []
                        msg = (
                            f"Wrote:\n{result.get('written')}\n\n"
                            f"OK: {result.get('successes', 0)}\n"
                            f"Failed: {len(fails)}\n"
                            f"Skipped: {len(skips)}"
                        )
                        if fails:
                            msg += "\n\nFailures:\n" + "\n".join(
                                f"- {f.get('source_file')}: {f.get('error')}"
                                for f in fails
                            )
                            messagebox.showwarning("Done (with failures)", msg)
                        else:
                            messagebox.showinfo("Done", msg)

                    self.root.after(0, ok)
                except Exception:
                    err = traceback.format_exc()

                    def fail() -> None:
                        self._log("ERROR:\n" + err)
                        messagebox.showerror("Extract failed", err[-800:])

                    self.root.after(0, fail)
                finally:

                    def done() -> None:
                        self._busy = False
                        self.run_btn.configure(state="normal")

                    self.root.after(0, done)

            threading.Thread(target=work, daemon=True).start()

        def _show_batch(self, result: dict[str, Any]) -> None:
            from invoice_extractor.mapping_status import (
                count_mapping_statuses,
                format_status_line,
            )

            lines = [
                f"Wrote: {result.get('written')}",
                f"successes: {result.get('successes')}",
                f"failures: {len(result.get('failures') or [])}",
                f"skipped: {len(result.get('skipped') or [])}",
                "—",
            ]
            map_labels: list[str] = []
            for s in result.get("summaries") or []:
                if s.get("ok"):
                    mlab = s.get("mapping_status") or "—"
                    map_labels.append(mlab)
                    lines.append(
                        format_status_line(
                            invoice_no=s.get("invoice_no"),
                            format_id=s.get("format_id"),
                            mapping=mlab,
                            checker_verdict=s.get("checker_verdict"),
                            pair_status=s.get("pair_status"),
                        )
                    )
                    detail = (
                        f"    file={Path(s.get('source') or '').name} "
                        f"amount={s.get('amount')} items={s.get('item_count')}"
                    )
                    lines.append(detail)
                    from invoice_extractor.ocr import is_ocr_backend

                    tb = s.get("text_backend") or ""
                    if is_ocr_backend(tb):
                        lines.append(f"    OCR used: {tb}")
                    if s.get("text_backend_warning"):
                        warn = s["text_backend_warning"]
                        if is_ocr_backend(tb):
                            lines.append("    NOTE: " + warn)
                        else:
                            lines.append("    WARNING: " + warn)
                else:
                    mlab = s.get("mapping_status") or "全新／需規則"
                    if not s.get("skipped"):
                        map_labels.append(mlab)
                    pst = s.get("pair_status") or "—"
                    lines.append(
                        f"— | — | {pst} | "
                        f"{'SKIP' if s.get('skipped') else 'FAIL'} "
                        f"{Path(s.get('source') or '').name}: {s.get('error')}"
                    )
            counts = count_mapping_statuses(map_labels)
            footer_parts = [f"{k}={v}" for k, v in counts.items() if v]
            footer = "Batch mapping: " + (", ".join(footer_parts) if footer_parts else "none")
            lines.append("—")
            lines.append(footer)
            self._log("\n".join(lines))
            if hasattr(self, "status_var"):
                self.status_var.set(
                    f"Last run — OK {result.get('successes', 0)} / "
                    f"fail {len(result.get('failures') or [])} / "
                    f"skip {len(result.get('skipped') or [])} | {footer}"
                )

        def run(self) -> None:
            self.root.mainloop()

    App().run()


if __name__ == "__main__":
    run_gui()
