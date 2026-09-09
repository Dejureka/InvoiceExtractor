"""CLI: ``python -m pdf_layout_text in.pdf [-o out.txt]`` / ``--serve``."""

from __future__ import annotations

import argparse
import html
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from .convert import pdf_to_layout_text


def _write_out(text: str, out_path: Path | None) -> None:
    if out_path:
        out_path.write_text(text, encoding="utf-8")
        print(f"Wrote {out_path} ({len(text)} chars)", file=sys.stderr)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")


def _serve(host: str, port: int) -> int:
    """Tiny stdlib upload page — no Flask required."""

    page = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PDF → Layout Text</title>
<style>
body{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem}
.box{border:1px dashed #888;padding:1.5rem;border-radius:8px}
button{margin-top:1rem;padding:.5rem 1rem}
.meta{color:#555;font-size:.9rem}
</style></head><body>
<h1>PDF → Layout Text</h1>
<p class="meta">上傳 PDF，下載保留版面的 .txt（優先用本機 pdftotext -layout）。</p>
<form class="box" method="POST" enctype="multipart/form-data" action="/convert">
  <input type="file" name="pdf" accept="application/pdf,.pdf" required>
  <br><button type="submit">轉換並下載 .txt</button>
</form>
</body></html>
"""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quieter
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body = page.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path != "/convert":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            ctype = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in ctype:
                self.send_error(400, "multipart/form-data required")
                return
            # Parse boundary
            boundary = None
            for part in ctype.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part.split("=", 1)[1].strip().strip('"')
            if not boundary:
                self.send_error(400, "missing boundary")
                return
            b = boundary.encode("ascii", errors="ignore")
            chunks = raw.split(b"--" + b)
            pdf_bytes = None
            filename = "upload.pdf"
            for chunk in chunks:
                if b"Content-Disposition" not in chunk:
                    continue
                header, _, body = chunk.partition(b"\r\n\r\n")
                if b'name="pdf"' not in header and b"name=pdf" not in header:
                    continue
                # filename
                for line in header.split(b"\r\n"):
                    if b"filename=" in line:
                        try:
                            fn = line.decode("utf-8", errors="replace")
                            if 'filename="' in fn:
                                filename = fn.split('filename="', 1)[1].split('"', 1)[0]
                            elif "filename=" in fn:
                                filename = fn.split("filename=", 1)[1].strip()
                        except Exception:
                            pass
                body = body.rstrip(b"\r\n-")
                if body.endswith(b"--"):
                    body = body[:-2]
                pdf_bytes = body.lstrip(b"\r\n")
                # strip trailing CRLF left by multipart
                while pdf_bytes.endswith(b"\r\n"):
                    pdf_bytes = pdf_bytes[:-2]
                break
            if not pdf_bytes:
                self.send_error(400, "no pdf field")
                return
            with tempfile.TemporaryDirectory() as td:
                pdf_path = Path(td) / (Path(filename).name or "upload.pdf")
                if pdf_path.suffix.lower() != ".pdf":
                    pdf_path = pdf_path.with_suffix(".pdf")
                pdf_path.write_bytes(pdf_bytes)
                try:
                    text, backend = pdf_to_layout_text(pdf_path)
                except Exception as e:
                    msg = f"convert failed: {e}".encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(msg)))
                    self.end_headers()
                    self.wfile.write(msg)
                    return
                out_name = Path(filename).stem + ".txt"
                data = text.encode("utf-8")
                # prepend backend comment
                header_line = f"# backend: {backend}\n".encode("utf-8")
                data = header_line + data
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{out_name}"',
                )
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

    server = HTTPServer((host, port), Handler)
    print(f"Serving PDF→layout upload at http://{host}:{port}/  (Ctrl+C to stop)", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pdf_layout_text",
        description="PDF → layout-preserving text (pdftotext / pymupdf / pdfminer).",
    )
    parser.add_argument("pdf", nargs="?", help="Input PDF path")
    parser.add_argument("-o", "--output", help="Write .txt here (default: stdout)")
    parser.add_argument(
        "--backend-info",
        action="store_true",
        help="Print which backend was used to stderr",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start tiny stdlib upload server (returns .txt download)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    if args.serve:
        return _serve(args.host, args.port)

    if not args.pdf:
        parser.error("pdf path required (or use --serve)")

    try:
        text, backend = pdf_to_layout_text(args.pdf)
    except FileNotFoundError:
        print(f"File not found: {args.pdf}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.backend_info:
        print(f"backend: {backend}", file=sys.stderr)

    out = Path(args.output) if args.output else None
    _write_out(text, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
