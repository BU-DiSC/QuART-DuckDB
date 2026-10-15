#!/usr/bin/env python3
"""Paper figure and table for the DuckDB CREATE INDEX A/B (grouped bulk loading on vs off).

Usage: paper_figures.py <results-dir> [--fig OUT.pdf] [--quart-ns NS]
Reads <results-dir>/timing.csv and profile.csv written by bench_paper.sh. Prints a summary with
per-key costs (index-build operator time / keys, whole CREATE INDEX / keys) and the LaTeX rows for
the paper table, and draws CREATE INDEX time versus threads for both loaders.
"""
import argparse
import csv
import statistics
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument("dir")
p.add_argument("--fig", default=None)
p.add_argument("--fig-workloads", default="dense_int32_100M,gapped_int32_100M")
p.add_argument("--quart-ns", type=float, default=None, help="QuART standalone bulk load ns/key (dense)")
p.add_argument("--heatmap", default=None, help="write a speedup heatmap (key-set size x threads) to this PDF")
p.add_argument("--heatmap-metric", default="build", choices=("build", "statement"),
               help="build: per-thread cost per inserted key inside the index-build operator (profiler), DuckDB loader / QuART bulk loading; statement: whole CREATE INDEX wall time ratio")
args = p.parse_args()

wall = defaultdict(list)  # (workload, grouped, threads) -> [real_s]
order = []
with open(f"{args.dir}/timing.csv") as f:
    for r in csv.DictReader(f):
        wall[(r["workload"], r["grouped"], int(r["threads"]))].append(float(r["real_s"]))
        if r["workload"] not in order:
            order.append(r["workload"])
prof = {}
with open(f"{args.dir}/profile.csv") as f:
    for r in csv.DictReader(f):
        prof[(r["workload"], r["grouped"], int(r["threads"]))] = r

threads = sorted({k[2] for k in wall})


def med(w, g, t):
    v = wall.get((w, g, t))
    return statistics.median(v) if v else None


print("== per-cell medians (s) and index-build operator CPU ns/key ==")
for w in order:
    for t in threads:
        row = []
        for g in ("false", "true"):
            m = med(w, g, t)
            pr = prof.get((w, g, t))
            if m is None or pr is None:
                row.append(f"{g}: n/a")
                continue
            keys = int(pr["keys"])
            build_ns = float(pr["create_index_s"]) * 1e9 / keys
            sort_ns = float(pr["order_by_s"]) * 1e9 / keys
            row.append(f"{g}: wall {m:.2f}s ({m*1e9/keys:.1f} ns/key) build {build_ns:.1f} ns/key sort {sort_ns:.1f} ns/key")
        o, g_ = med(w, "false", t), med(w, "true", t)
        sp = f" speedup {o/g_:.2f}x" if o and g_ else ""
        print(f"{w:20s} T={t:2d} | " + " | ".join(row) + sp)

print("\n== LaTeX table rows (1 thread build ns/key old/grouped/x, CREATE INDEX x at 1, 8 and max threads) ==")
tmax = threads[-1]
for w in order:
    pr_o, pr_g = prof.get((w, "false", 1)), prof.get((w, "true", 1))
    if not pr_o or not pr_g:
        continue
    keys = int(pr_o["keys"])
    bo = float(pr_o["create_index_s"]) * 1e9 / keys
    bg = float(pr_g["create_index_s"]) * 1e9 / keys
    sp = {t: med(w, "false", t) / med(w, "true", t) for t in (1, 8, tmax) if med(w, "false", t) and med(w, "true", t)}
    cols = " & ".join(f"{sp[t]:.2f}$\\times$" for t in sp)
    print(f"{w} & {keys/1e6:.0f}M & {bo:.0f} & {bg:.0f} & {bo/bg:.1f}$\\times$ & {cols} \\\\")

print("\n== fixed (non-scaling) part of the statement: wall - (build+sort CPU)/threads ==")
for w in order:
    for t in threads:
        row = []
        for g in ("false", "true"):
            pr = prof.get((w, g, t)); m = med(w, g, t)
            if pr and m:
                fixed = m - (float(pr["create_index_s"]) + float(pr["order_by_s"])) / t
                row.append(f"{g}: {fixed:.2f}s")
        print(f"{w:20s} T={t:2d} | " + " | ".join(row))

if args.fig:
    # Same style as the paper's Fig. 15 (conc_ycsb.pdf): LaTeX Libertine text, axes only, dotted y-grid,
    # purple solid circles for QuART, green dashed squares for the baseline, legend above the panels.
    w = args.fig_workloads.split(",")[0]
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = ["Linux Libertine O", "Linux Libertine", "Libertine"]
    plt.rcParams["text.usetex"] = True
    plt.rcParams["text.latex.preamble"] = r"\usepackage{libertine}"
    plt.rcParams.update({"font.size": 13, "axes.titlesize": 14, "axes.labelsize": 14,
                         "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 13})
    fig, axes = plt.subplots(1, 2, figsize=(6.95, 3.2))
    styles = (("false", "DuckDB loader", "#55a868", "s", "--"), ("true", "+ QuART bulk loading", "#6a0dad", "o", "-"))
    ax = axes[0]
    for g, label, color, marker, ls in styles:
        ax.plot(threads, [med(w, g, t) for t in threads], ls=ls, marker=marker, ms=7, lw=2.4, color=color, label=label)
    ax.set_ylabel("CREATE INDEX time (s)")
    ax.set_title("(a) statement time")
    ax = axes[1]
    for g, label, color, marker, ls in styles:
        ys = []
        for t in threads:
            pr = prof.get((w, g, t))
            ys.append(float(pr["create_index_s"]) * 1e9 / int(pr["keys"]) if pr else None)
        ax.plot(threads, ys, ls=ls, marker=marker, ms=7, lw=2.4, color=color, label=label)
    ax.set_ylabel("index build (ns per key)")
    ax.set_title("(b) per-key build cost")
    for ax in axes:
        ax.set_xscale("log", base=2)
        ax.set_xticks(threads)
        ax.set_xticklabels([str(t) for t in threads])
        ax.set_xlabel("Threads")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", ls=":", lw=0.8, color="#bbbbbb")
        ax.set_axisbelow(True)
        ax.minorticks_off()
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.02), handlelength=2.2)
    fig.tight_layout(rect=(0, 0, 1, 0.9), w_pad=1.5)
    fig.savefig(args.fig, bbox_inches="tight")
    print(f"\nwrote {args.fig}")


if args.heatmap:
    # Same style as the paper's K-L heatmaps (Figs. 10/11): viridis, annotated cells, white cell borders, colorbar,
    # LaTeX Libertine text. Rows = key-set sizes (sorted 32-bit keys), columns = thread counts.
    import re
    import numpy as np
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = ["Linux Libertine O", "Linux Libertine", "Libertine"]
    plt.rcParams["text.usetex"] = True
    plt.rcParams["text.latex.preamble"] = r"\usepackage{libertine}"
    plt.rcParams.update({"font.size": 15, "axes.labelsize": 16, "xtick.labelsize": 15, "ytick.labelsize": 15})

    def size_of(w):
        m = re.search(r"_(\d+)M$", w)
        return int(m.group(1)) if m else 0
    sizes = sorted((w for w in order if size_of(w)), key=size_of)
    grid = np.full((len(sizes), len(threads)), np.nan)
    for i, w in enumerate(sizes):
        for j, t in enumerate(threads):
            if args.heatmap_metric == "statement":
                o, g = med(w, "false", t), med(w, "true", t)
                if o and g:
                    grid[i, j] = o / g
            else:
                po, pg = prof.get((w, "false", t)), prof.get((w, "true", t))
                if po and pg:
                    # cost per inserted key on its thread = operator CPU time (summed over threads) / keys
                    grid[i, j] = (float(po["create_index_s"]) / int(po["keys"])) / (float(pg["create_index_s"]) / int(pg["keys"]))
    fig, ax = plt.subplots(figsize=(6.6, 3.3))
    # anchor the color scale at parity (1x) so a flat grid reads as flat instead of amplifying noise
    vmin, vmax = 1.0, max(np.nanmax(grid), 1.5)
    im = ax.imshow(grid, cmap="viridis", aspect="auto", origin="lower", vmin=vmin, vmax=vmax)
    for i in range(len(sizes)):
        for j in range(len(threads)):
            v = grid[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, f"{v:.2f}$\\times$", ha="center", va="center", fontsize=15,
                    color="black" if (v - vmin) / max(vmax - vmin, 1e-9) > 0.6 else "white")
    ax.set_xticks(range(len(threads)))
    ax.set_xticklabels([str(t) for t in threads])
    ax.set_yticks(range(len(sizes)))
    ax.set_yticklabels([f"{size_of(w)}M" for w in sizes])
    ax.set_xticks(np.arange(-0.5, len(threads), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(sizes), 1), minor=True)
    ax.grid(which="minor", color="white", lw=2)
    ax.tick_params(which="minor", length=0)
    ax.tick_params(which="major", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel("Threads")
    ax.set_ylabel("Sorted keys")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.ax.tick_params(labelsize=14)
    fig.tight_layout(pad=0.3)
    fig.savefig(args.heatmap, bbox_inches="tight")
    print(f"\n== heatmap grid, metric={args.heatmap_metric} (rows = sizes, cols = threads); min {np.nanmin(grid):.2f} max {np.nanmax(grid):.2f} ==")
    for i, w in enumerate(sizes):
        print(f"  {size_of(w):>4}M: " + "  ".join("  n/a" if np.isnan(v) else f"{v:.2f}x" for v in grid[i]))
    print(f"wrote {args.heatmap}")
