# Historical false-pass fixtures

These JSONs are projections of the extracts in `out/prefix_repro/`, with
invoice headers, line arithmetic, HS codes, and printed totals preserved.

- `2000263342.json` is the MA extract from `3b41cfb`. Items 2 and 5 lack HS
  codes. `2120411708.json` is the HS negative control from the same revision.
- The five `506*.json` files are PT Gloria extracts from `672f427` with
  `header.total_pkg` set to null.

All seven recorded a checker verdict of `pass` in their historical snapshots.
