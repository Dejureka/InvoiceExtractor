"""Simple tkinter GUI for InvoiceExtractor (drag-drop optional via tkinterdnd2)."""

from __future__ import annotations

import threading
import traceback
from pathlib import Path
from typing import Any


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
    """Turn dropped/selected paths into PDF files (directories expanded)."""
    from invoice_extractor.cli import collect_pdfs

    pdfs, _errs = collect_pdfs(paths)
    return pdfs


def _extract_one(pdf: Path) -> dict[str, Any]:
    """Run extract + hard check; return data dict (no write)."""
    from invoice_extractor.checker import hard_check
    from invoice_extractor.rules_engine import extract_invoice
    from invoice_extractor.text_layer import backend_warning

    result = extract_invoice(pdf)
    data = result.to_dict()
    hard = hard_check(data)
    data["meta"]["checker_verdict"] = hard["verdict"]
    if hard["verdict"] == "pass" and data["meta"].get("confidence") == "rules":
        data["meta"]["confidence"] = "high"
    elif hard["verdict"] == "conflict":
        data["meta"]["confidence"] = "conflict"
    data["meta"]["checker_issues"] = hard.get("issues")
    data["meta"]["checker_details"] = hard.get("details")
    warn = backend_warning(data["meta"].get("text_backend"))
    if warn:
        data["meta"]["text_backend_warning"] = warn
    data["_hard"] = hard
    return data


def _extract_many(pdfs: list[Path], out: Path | None) -> dict[str, Any]:
    """Extract multiple PDFs into one Excel (or JSON); surface partial failures."""
    from invoice_extractor.export import (
        default_out_path,
        default_result_path,
        is_json_out,
        write_extract,
        write_extracts,
    )

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for pdf in pdfs:
        try:
            data = _extract_one(pdf)
            hard = data.pop("_hard")
            successes.append(data)
            header = data.get("header") or {}
            meta = data.get("meta") or {}
            summaries.append(
                {
                    "ok": True,
                    "source": str(pdf),
                    "invoice_no": header.get("invoice_no"),
                    "amount": header.get("amount"),
                    "item_count": len(data.get("items") or []),
                    "format_id": meta.get("format_id"),
                    "checker_verdict": hard["verdict"],
                    "issues": hard.get("issues") or [],
                    "text_backend": meta.get("text_backend"),
                    "text_backend_warning": meta.get("text_backend_warning"),
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "source_file": str(pdf),
                    "error": str(exc),
                    "meta": {"source_file": str(pdf)},
                }
            )
            summaries.append({"ok": False, "source": str(pdf), "error": str(exc)})

    if not successes:
        return {
            "ok": False,
            "written": None,
            "successes": 0,
            "failures": failures,
            "summaries": summaries,
            "error": "All files failed; nothing written.",
        }

    if out is None:
        dest = default_result_path() if len(pdfs) > 1 else default_out_path(pdfs[0])
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
            self._build()

        def _make_root(self):
            if has_dnd:
                root = TkinterDnD.Tk()
            else:
                root = tk.Tk()
            root.title("InvoiceExtractor")
            root.geometry("720x580")
            root.minsize(520, 440)
            return root

        def _build(self) -> None:
            self.root = self._make_root()
            pad = {"padx": 8, "pady": 4}

            frm_pdf = ttk.LabelFrame(self.root, text="PDFs (multi-select / folders OK)")
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
                text="Drop zone (PDF / folder)"
                + (" — drag-drop on" if has_dnd else " — use Browse"),
            )
            frm_drop.pack(fill="x", **pad)
            self.drop_label = ttk.Label(
                frm_drop,
                text="Drop PDFs or a folder here, or use Browse",
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
            self.listbox = tk.Listbox(frm_list, height=5, selectmode="extended")
            self.listbox.pack(fill="x", expand=True, padx=4, pady=4)

            from invoice_extractor.export import DEFAULT_RESULT_NAME

            frm_out = ttk.LabelFrame(
                self.root,
                text=f"Output (optional; default: {DEFAULT_RESULT_NAME} / <pdf>.extract.xlsx)",
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

            frm_sum = ttk.LabelFrame(self.root, text="Summary")
            frm_sum.pack(fill="both", expand=True, **pad)
            self.summary = scrolledtext.ScrolledText(frm_sum, height=12, wrap="word")
            self.summary.pack(fill="both", expand=True, padx=4, pady=4)

            dnd_note = "enabled" if has_dnd else "not installed (Browse still works)"
            self._log(f"Drag-drop: {dnd_note}")
            try:
                from pdf_layout_text.convert import find_pdftotext
                from invoice_extractor.text_layer import backend_warning

                if find_pdftotext():
                    self._log("Text engine: pdftotext (poppler) available")
                else:
                    self._log(
                        "WARNING: "
                        + (backend_warning("pymupdf/pdfminer fallback") or "")
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
                self.pdf_var.set(f"{len(self._pdfs)} PDFs selected")

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
            self.pdf_var.set("")
            self.out_var.set("")
            self.listbox.delete(0, "end")
            self.summary.delete("1.0", "end")
            dnd_note = "enabled" if has_dnd else "not installed (Browse still works)"
            self._log(f"Drag-drop: {dnd_note}")

        def _on_drop(self, event) -> None:
            parts = _parse_dnd_paths(event.data)
            if not parts:
                self._log("Drop ignored: empty payload")
                return
            pdfs = _expand_pdf_inputs(parts)
            if not pdfs:
                self._log("Drop ignored: no PDFs found")
                return
            self._set_pdfs(pdfs, append=True)
            self._log(f"Added {len(pdfs)} PDF(s); total {len(self._pdfs)}")

        def _browse_pdf(self) -> None:
            paths = filedialog.askopenfilenames(
                title="Select invoice PDF(s)",
                filetypes=[("PDF", "*.pdf *.PDF"), ("All", "*.*")],
            )
            if paths:
                self._set_pdfs([Path(p) for p in paths], append=True)
                self._log(f"Selected {len(paths)} file(s); total {len(self._pdfs)}")

        def _browse_folder(self) -> None:
            folder = filedialog.askdirectory(title="Select folder of invoice PDFs")
            if folder:
                pdfs = _expand_pdf_inputs([folder])
                if not pdfs:
                    messagebox.showwarning("No PDFs", f"No PDF files in:\n{folder}")
                    return
                self._set_pdfs(pdfs, append=True)
                self._log(f"Added folder ({len(pdfs)} PDFs); total {len(self._pdfs)}")

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

        def _run_extract(self) -> None:
            if self._busy:
                return
            typed = self.pdf_var.get().strip().strip('"')
            if typed and not typed.endswith("PDFs selected") and Path(typed).is_file():
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

            self._busy = True
            self.run_btn.configure(state="disabled")
            self._log(f"Extracting {len(self._pdfs)} file(s) …")
            pdfs = list(self._pdfs)

            def work() -> None:
                try:
                    result = _extract_many(pdfs, out)

                    def ok() -> None:
                        self._show_batch(result)
                        fails = result.get("failures") or []
                        msg = (
                            f"Wrote:\n{result.get('written')}\n\n"
                            f"OK: {result.get('successes', 0)}\n"
                            f"Failed: {len(fails)}"
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
            lines = [
                f"Wrote: {result.get('written')}",
                f"successes: {result.get('successes')}",
                f"failures: {len(result.get('failures') or [])}",
            ]
            for s in result.get("summaries") or []:
                if s.get("ok"):
                    lines.append(
                        f"  OK {s.get('source')}: invoice_no={s.get('invoice_no')} "
                        f"amount={s.get('amount')} items={s.get('item_count')} "
                        f"format={s.get('format_id')} verdict={s.get('checker_verdict')}"
                    )
                    if s.get("text_backend_warning"):
                        lines.append("    WARNING: " + s["text_backend_warning"])
                else:
                    lines.append(f"  FAIL {s.get('source')}: {s.get('error')}")
            self._log("\n".join(lines))

        def run(self) -> None:
            self.root.mainloop()

    App().run()


if __name__ == "__main__":
    run_gui()
