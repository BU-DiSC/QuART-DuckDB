#!/bin/bash
# Reproduce the paper's DuckDB figure: per-thread, per-key index-build speedup of QuART bulk loading over
# DuckDB's loader, as a heatmap of sorted key-set size (5M-500M) x thread count (1-24).
#
# Usage: run_paper_heatmap.sh [results-dir] [heatmap.pdf]
#        run_paper_heatmap.sh --replot <results-dir> [heatmap.pdf]   # only redraw from existing results
#
# Needs a Release build of DuckDB (from the repo root: CMAKE_BUILD_PARALLEL_LEVEL=48 GEN=ninja make release),
# python3 with matplotlib and numpy, and a LaTeX installation with the libertine package (the figure text is
# rendered by LaTeX). Set PIN to override the numactl pinning (default: socket 0 if numactl exists), THREADS
# to change the thread counts, REPEAT for the number of timed runs per cell (default 3).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)

if [[ "${1:-}" == "--replot" ]]; then
	OUT=${2:?results dir}; FIG=${3:-$OUT/duckdb_speedup_heatmap.pdf}
else
	OUT=${1:-$HERE/results/$(date +%F)_heatmap}; FIG=${2:-$OUT/duckdb_speedup_heatmap.pdf}
	DUCKDB=$ROOT/build/release/duckdb
	[[ -x "$DUCKDB" ]] || { echo "missing $DUCKDB: build it with 'GEN=ninja make release' in $ROOT" >&2; exit 1; }
	if [[ -z "${PIN+x}" ]]; then
		PIN=""; command -v numactl >/dev/null && PIN="numactl --cpunodebind=0 --membind=0"
	fi
	mkdir -p "$OUT"
	echo "running the size sweep into $OUT (this takes about 30 minutes)" >&2
	WORKLOADS=$(cat "$HERE/workloads_sizes.txt") PIN="$PIN" \
		bash "$HERE/bench_paper.sh" "$DUCKDB" "$OUT" "${REPEAT:-3}" ${THREADS:-1 2 4 8 16 24}
fi

python3 "$HERE/paper_figures.py" "$OUT" --heatmap "$FIG" --heatmap-metric build
echo "heatmap written to $FIG" >&2
