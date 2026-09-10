"""Pure CLI entry (console). Portable Windows exe uses run_gui.py instead."""
from invoice_extractor.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
