"""PyInstaller / double-click entry: GUI when no args; CLI when args present."""
from __future__ import annotations

import sys


def main() -> int:
    argv = sys.argv[1:]
    # No args or explicit --gui → GUI (Windows double-click has empty argv)
    if not argv or argv == ["--gui"] or argv == ["gui"]:
        from invoice_extractor.gui import run_gui

        run_gui()
        return 0
    from invoice_extractor.cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
