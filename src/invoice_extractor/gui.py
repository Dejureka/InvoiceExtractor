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


def _extract_one(pdf: Path, out: Path | None) -> dict[str, Any]:
    """Run extract + hard check + write Excel/JSON; return summary dict."""
    from invoice_extractor.checker import hard_check
    from invoice_extractor.export import default_out_path, write_extract
    from invoice_extractor.rules_engine import extract_invoice

    result = extract_invoice(pdf)
    data = result.to_dict()
    hard = hard_check(data)
    data["meta"]["checker_verdict"] = hard["verdict"]
    if hard["verdict"] == "pass" and data["meta"].get("confidence") == "rules":
        data["meta"]["confidence"] = "high"
    elif hard["verdict"] == "conflict":
        data["meta"]["confidence"] = "conflict"
    data["meta"]["checker_issues"] = hard.get("issues")

    dest = out if out else default_out_path(pdf)
    written = write_extract(data, dest)
    header = data.get("header") or {}
    return {
        "ok": True,
        "written": str(written),
        "invoice_no": header.get("invoice_no"),
        "amount": header.get("amount"),
        "item_count": len(data.get("items") or []),
        "format_id": (data.get("meta") or {}).get("format_id"),
        "checker_verdict": hard["verdict"],
        "issues": hard.get("issues") or [],
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
            self._build()

        def _make_root(self):
            if has_dnd:
                root = TkinterDnD.Tk()
            else:
                root = tk.Tk()
            root.title("InvoiceExtractor")
            root.geometry("640x520")
            root.minsize(480, 400)
            return root

        def _build(self) -> None:
            self.root = self._make_root()
            pad = {"padx": 8, "pady": 4}

            frm_pdf = ttk.LabelFrame(self.root, text="PDF")
            frm_pdf.pack(fill="x", **pad)
            self.pdf_var = tk.StringVar()
            ttk.Entry(frm_pdf, textvariable=self.pdf_var).pack(
                side="left", fill="x", expand=True, padx=4, pady=4
            )
            ttk.Button(frm_pdf, text="Browse…", command=self._browse_pdf).pack(
                side="left", padx=4, pady=4
            )

            frm_drop = ttk.LabelFrame(
                self.root,
                text="Drop zone (PDF)" + (" — drag-drop on" if has_dnd else " — use Browse"),
            )
            frm_drop.pack(fill="x", **pad)
            self.drop_label = ttk.Label(
                frm_drop,
                text="Drop a PDF here, or use Browse",
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

            frm_out = ttk.LabelFrame(
                self.root, text="Output (optional; default: <pdf>.extract.xlsx)"
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

        def _log(self, msg: str) -> None:
            self.summary.insert("end", msg + "\n")
            self.summary.see("end")

        def _clear(self) -> None:
            self.pdf_var.set("")
            self.out_var.set("")
            self.summary.delete("1.0", "end")
            dnd_note = "enabled" if has_dnd else "not installed (Browse still works)"
            self._log(f"Drag-drop: {dnd_note}")

        def _on_drop(self, event) -> None:
            parts = _parse_dnd_paths(event.data)
            pdfs = [p for p in parts if p.lower().endswith(".pdf")]
            if not pdfs:
                self._log("Drop ignored: no PDF in payload")
                return
            self.pdf_var.set(pdfs[0])
            if len(pdfs) > 1:
                self._log(f"Multiple PDFs dropped; using first: {pdfs[0]}")
            else:
                self._log(f"PDF set: {pdfs[0]}")

        def _browse_pdf(self) -> None:
            path = filedialog.askopenfilename(
                title="Select invoice PDF",
                filetypes=[("PDF", "*.pdf *.PDF"), ("All", "*.*")],
            )
            if path:
                self.pdf_var.set(path)

        def _browse_out(self) -> None:
            path = filedialog.asksaveasfilename(
                title="Save extract as",
                defaultextension=".xlsx",
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
            pdf_s = self.pdf_var.get().strip().strip('"')
            if not pdf_s:
                messagebox.showwarning("Missing PDF", "Select or drop a PDF first.")
                return
            pdf = Path(pdf_s)
            if not pdf.is_file():
                messagebox.showerror("Not found", f"File not found:\n{pdf}")
                return
            out_s = self.out_var.get().strip().strip('"')
            out = Path(out_s) if out_s else None

            self._busy = True
            self.run_btn.configure(state="disabled")
            self._log(f"Extracting: {pdf} …")

            def work() -> None:
                try:
                    summary = _extract_one(pdf, out)
                    def ok() -> None:
                        self._show_summary(summary)
                        messagebox.showinfo(
                            "Done",
                            f"Wrote:\n{summary['written']}\n\n"
                            f"invoice_no={summary['invoice_no']}\n"
                            f"amount={summary['amount']}\n"
                            f"items={summary['item_count']}\n"
                            f"format={summary['format_id']}\n"
                            f"verdict={summary['checker_verdict']}",
                        )
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

        def _show_summary(self, s: dict[str, Any]) -> None:
            lines = [
                f"Wrote: {s['written']}",
                f"invoice_no: {s['invoice_no']}",
                f"amount: {s['amount']}",
                f"item_count: {s['item_count']}",
                f"format_id: {s['format_id']}",
                f"checker_verdict: {s['checker_verdict']}",
            ]
            issues = s.get("issues") or []
            if issues:
                lines.append("issues:")
                for iss in issues:
                    lines.append(f"  - {iss}")
            self._log("\n".join(lines))

        def run(self) -> None:
            self.root.mainloop()

    App().run()


if __name__ == "__main__":
    run_gui()
