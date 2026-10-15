#!/usr/bin/env python3
"""Rebuild timing.csv and profile.csv of a bench_paper.sh results directory from its raw logs.

Usage: reparse_logs.py <results-dir>
Reads <results-dir>/sql/run_<workload>_<threads>_<grouped>.log (shell output with .timer lines and the
KEYS= row) and <results-dir>/profiles/<workload>_<threads>_<grouped>.json (profiler output).
"""
import glob
import json
import os
import re
import sys

d = sys.argv[1]
timing, profile = [], []
for log in sorted(glob.glob(f"{d}/sql/run_*.log")):
    m = re.match(r"run_(.+)_(\d+)_(true|false)\.log$", os.path.basename(log))
    name, th, grouped = m.group(1), int(m.group(2)), m.group(3)
    text = open(log).read()
    keys = re.search(r"^KEYS=(\d+)$", text, re.M)
    keys = int(keys.group(1)) if keys else 0
    for r, t in enumerate(re.findall(r"Run Time \(s\): real ([\d.]+) user ([\d.]+) sys ([\d.]+)", text), 1):
        timing.append((name, grouped, th, r, *t))
    jpath = f"{d}/profiles/{name}_{th}_{grouped}.json"
    if os.path.exists(jpath):
        j = json.load(open(jpath))
        times = {}
        def walk(n):
            if "type" in n:
                times[n["type"]] = times.get(n["type"], 0.0) + n.get("timing", 0.0)
            for c in n.get("children", []):
                walk(c)
        for op in j["operator"]:
            walk(op)
        q = j["query"]
        profile.append((name, grouped, th, keys, f'{times.get("CREATE_INDEX", 0):.6f}', f'{times.get("ORDER_BY", 0):.6f}',
                        f'{q["total_time"]:.6f}', f'{q["cpu_time"]:.6f}'))

order = {"false": 0, "true": 1}
timing.sort(key=lambda r: (r[0], r[2], order[r[1]], r[3]))
profile.sort(key=lambda r: (r[0], r[2], order[r[1]]))
with open(f"{d}/timing.csv", "w") as f:
    f.write("workload,grouped,threads,repeat,real_s,user_s,sys_s\n")
    for r in timing:
        f.write(",".join(map(str, r)) + "\n")
with open(f"{d}/profile.csv", "w") as f:
    f.write("workload,grouped,threads,keys,create_index_s,order_by_s,query_total_s,cpu_time_s\n")
    for r in profile:
        f.write(",".join(map(str, r)) + "\n")
print(f"{len(timing)} timing rows, {len(profile)} profile rows")
