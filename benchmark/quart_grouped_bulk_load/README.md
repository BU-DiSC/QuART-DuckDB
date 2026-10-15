# Grouped (QuART) bulk loading: CREATE INDEX A/B benchmark

Times `CREATE INDEX` with grouped bulk loading on (`SET art_grouped_bulk_load = true`, the default)
and off (the per-chunk build-and-merge path) over the same tables.

## Workloads

`workloads.txt` lists `name|CREATE TABLE t AS ...` lines. Synthetic workloads are generated in SQL.
BoDS and QuART key files (raw little-endian integer keys) are converted to Parquet first:

```shell
python3 bods_to_parquet.py <keys.bin> WORKLOAD_DIR/bods20M_d100.parquet            # uint32 keys
python3 bods_to_parquet.py <keys.bin> WORKLOAD_DIR/bods20M_d050.parquet --sample-density 0.5
python3 bods_to_parquet.py <vackeys.bin> WORKLOAD_DIR/vac_banded_100M.parquet --dtype u64
```

`--sample-density D` keeps each key with probability `D`, which turns a dense sorted key set into a
sorted-with-gaps set over the same range (density below 1). Replace `WORKLOAD_DIR` in `workloads.txt`
with the directory holding the Parquet files.

## Running

```shell
WORKLOADS=$(cat workloads.txt) bash bench_create_index.sh build/reldebug/duckdb results.csv 3 1 8
python3 summarize.py results.csv      # Markdown table of medians and speedups
```

Arguments: DuckDB binary, output CSV, repeats per cell, then the thread counts to test.

## Paper figure: per-thread, per-key speedup heatmap

`run_paper_heatmap.sh` reproduces the paper's DuckDB figure in one command. It runs the sorted
key-set size sweep in `workloads_sizes.txt` (5M, 20M, 100M, 200M, 500M sorted 32-bit integers,
generated in SQL) for 1, 2, 4, 8, 16 and 24 threads with both loaders, then draws the heatmap:

```shell
GEN=ninja make release                      # from the repo root, once
benchmark/quart_grouped_bulk_load/run_paper_heatmap.sh results/my_run my_heatmap.pdf
benchmark/quart_grouped_bulk_load/run_paper_heatmap.sh --replot results/my_run   # redraw only
```

The cell value is the per-thread, per-key index-build speedup: DuckDB's profiler reports the time
inside the `CREATE_INDEX` operator (the per-thread build, summed over threads); dividing it by the
number of keys gives the cost of an inserted key on its thread, and the heatmap shows that cost with
DuckDB's loader divided by the cost with QuART bulk loading. `paper_figures.py --heatmap-metric
statement` draws the whole-statement wall-clock speedup instead, and the script also prints per-cell
wall times, build and sort cost per key, and LaTeX table rows.

Pieces: `bench_paper.sh` times `CREATE INDEX` (median of `.timer` runs) and captures one profiled run
per cell into `timing.csv` / `profile.csv`; `reparse_logs.py` rebuilds those CSVs from the raw logs;
`paper_figures.py` draws the figure (LaTeX-rendered Libertine text, so a LaTeX install with the
`libertine` package is needed). By default DuckDB is pinned to socket 0 with `numactl`; set `PIN=""`
to disable. Expect about 30 minutes for the sweep; the 500M table needs roughly 20 GB.

## Results

`results/` holds runs from the development machine (2x24-core Xeon Gold 6442Y, 125 GB RAM):
`2026-10-14_reldebug_96core*` (RelWithDebInfo, first A/B over mixed key sets),
`2026-10-14_release_socket0` (Release build, socket 0, five key sets: dense, gapped, random
64-bit, sequential and random strings, with profiler data), and `2026-10-15_release_socket0_sizes`
(Release build, socket 0, the size sweep behind the paper heatmap).
Each `CREATE INDEX` time includes DuckDB's sort and the post-build index verification, so the
whole-statement speedups understate the gain inside the ART build itself.
