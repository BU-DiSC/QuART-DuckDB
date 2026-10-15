#!/bin/bash
# Time CREATE INDEX with grouped bulk loading on and off, and record the profiler's per-operator times.
#
# Usage: bench_paper.sh <duckdb-binary> <out-dir> <repeat> <threads...>
# Workloads are read from the WORKLOADS variable: lines of "<name>|<CREATE TABLE t AS ... SQL>".
# For every (workload, threads, grouped) cell the table is loaded once, CREATE INDEX is timed REPEAT
# times (wall time from .timer), and one more CREATE INDEX runs under the JSON profiler to split the
# statement into the sort (ORDER_BY) and the index build (CREATE_INDEX: Sink + Combine, summed over
# threads). Set PIN (e.g. "numactl --cpunodebind=0 --membind=0") to confine DuckDB to one socket.
#
# Output: <out-dir>/timing.csv   workload,grouped,threads,repeat,real_s,user_s,sys_s
#         <out-dir>/profile.csv  workload,grouped,threads,keys,create_index_s,order_by_s,query_total_s,cpu_time_s
set -u
DUCKDB=$1; OUT=$2; REPEAT=$3; shift 3; THREADS="$@"
PIN=${PIN:-}
mkdir -p "$OUT/sql" "$OUT/profiles"
TIMING="$OUT/timing.csv"; PROFILE="$OUT/profile.csv"
[[ -f "$TIMING" ]] || echo "workload,grouped,threads,repeat,real_s,user_s,sys_s" > "$TIMING"
[[ -f "$PROFILE" ]] || echo "workload,grouped,threads,keys,create_index_s,order_by_s,query_total_s,cpu_time_s" > "$PROFILE"

while IFS='|' read -r name create_sql; do
	[[ -z "$name" ]] && continue
	for th in $THREADS; do
		for grouped in false true; do
			tag="${name}_${th}_${grouped}"
			sql="$OUT/sql/run_${tag}.sql"
			json="$OUT/profiles/${tag}.json"
			{
				echo "SET threads=$th;"
				echo "SET art_grouped_bulk_load=$grouped;"
				echo "$create_sql"
				echo "SELECT 'KEYS=' || count(*) FROM t;"
				for ((r = 0; r < REPEAT; r++)); do
					echo ".timer on"
					echo "CREATE INDEX idx ON t(k);"
					echo ".timer off"
					echo "DROP INDEX idx;"
				done
				echo "PRAGMA enable_profiling='json';"
				echo "PRAGMA profiling_output='$json';"
				echo "CREATE INDEX idx ON t(k);"
				echo "PRAGMA disable_profiling;"
				echo "DROP INDEX idx;"
			} > "$sql"
			log="$OUT/sql/run_${tag}.log"
			$PIN "$DUCKDB" -no-agent -csv < "$sql" > "$log" 2>&1
			keys=$(grep -o "^KEYS=[0-9]\+" "$log" | head -1 | cut -d= -f2)
			grep -i "run time" "$log" | awk -v w="$name" -v g="$grouped" -v t="$th" \
				'{r++; print w "," g "," t "," r "," $5 "," $7 "," $9}' >> "$TIMING"
			python3 - "$json" "$name" "$grouped" "$th" "$keys" >> "$PROFILE" <<'PY'
import json, sys
path, name, grouped, th, keys = sys.argv[1:6]
d = json.load(open(path))
times = {}
def walk(n):
    if "type" in n:
        times[n["type"]] = times.get(n["type"], 0.0) + n.get("timing", 0.0)
    for c in n.get("children", []):
        walk(c)
for op in d["operator"]:
    walk(op)
q = d["query"]
print(f'{name},{grouped},{th},{keys},{times.get("CREATE_INDEX", 0):.6f},{times.get("ORDER_BY", 0):.6f},{q["total_time"]:.6f},{q["cpu_time"]:.6f}')
PY
			echo "$(date +%H:%M:%S) done $tag keys=$keys" >&2
		done
	done
done <<< "$WORKLOADS"
