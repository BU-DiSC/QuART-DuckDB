# QuART grouped bulk loading in DuckDB

This fork of DuckDB (branch `v2.0-cyanoptera`, the fork's default branch, forked from `v2.0-cyanoptera` at d4355d01c59) is the
DuckDB part of the paper *QuART: Quick Ingestion to ART through Sortedness Awareness*, Section 5.2.
The main artifact, with the QuART implementation and the driver script `experiments/5.2-duckdb/run.sh`
that runs this fork's benchmark, is at https://anonymous.4open.science/r/QuART-53DF.

| Where | What |
|---|---|
| `src/execution/index/art/art_grouped_builder.{hpp,cpp}` | `ARTGroupedBuilder`: QuART's grouped bulk loading for the sorted `CREATE INDEX` build. A group is the run of keys that share every byte up to the divergence byte; each group's leaf-level node is built once at its final size instead of inserting key by key and merging per-chunk trees. |
| `src/execution/index/art/art_index.cpp`, `base_node.hpp`, `node48.hpp`, `node256.hpp` | the hooks that route the sorted build through the grouped builder; DuckDB's parallel sort, partitioning and final merge are unchanged |
| setting `art_grouped_bulk_load` (default `true`) | switches between the grouped builder and DuckDB's loader, so both can be timed on the same table |
| `test/sql/index/art/create_drop/test_art_grouped_bulk_load.test` | sqllogictest of the grouped build |
| `benchmark/quart_grouped_bulk_load/` | the paper's benchmark (Figure 16): `bench_paper.sh` times `CREATE INDEX` with both loaders and records the profiler's per-operator times; `run_paper_heatmap.sh` runs the paper's size sweep and draws the heatmap; `results/` holds the runs behind the paper. See its `README.md`. |

## Building

```sh
GEN=ninja make release          # the usual DuckDB release build; binary: build/release/duckdb (needs ninja; takes a while)
```

Nothing else is needed: the grouped loader is compiled in and switched with the setting
`art_grouped_bulk_load` (`SET art_grouped_bulk_load = false;` gives DuckDB's own loader).

## Running the experiment of Section 5.2 (Figure 16)

Figure 16 is a heatmap of the per-thread, per-key index-build speedup of QuART's grouped bulk
loading over DuckDB's loader, for sorted 32-bit key sets of 5M, 20M, 100M, 200M and 500M keys and
1, 2, 4, 8, 16 and 24 threads. One command runs the sweep and draws it:

```sh
benchmark/quart_grouped_bulk_load/run_paper_heatmap.sh results/my_run my_heatmap.pdf
```

For every (size, threads) cell it creates the table in SQL, times `CREATE INDEX` three times with
each loader (`REPEAT`), and records one profiled run; the cell value is the profiler's
`CREATE_INDEX` operator time per key with DuckDB's loader divided by that with QuART.
Expect about 30 minutes on one socket; the 500M-key table needs roughly 20 GB of RAM.
Knobs: `THREADS="1 2 4 8 16 24"`, `REPEAT=3`, `PIN="numactl --cpunodebind=0 --membind=0"`
(default when `numactl` exists; `PIN=""` disables pinning). `run_paper_heatmap.sh --replot results/my_run`
redraws from existing results. The run behind the paper is in `benchmark/quart_grouped_bulk_load/results/`
(the `*_sizes` directory); `benchmark/quart_grouped_bulk_load/README.md` describes the pieces
(`bench_paper.sh`, `paper_figures.py`, `reparse_logs.py`) and an A/B over mixed key sets
(`bench_create_index.sh`).

The same sweep is driven from the main artifact by `experiments/5.2-duckdb/run.sh`, which builds this
fork, runs `bench_paper.sh` and draws the figure with the artifact's plot script.

---

*The upstream README follows.*

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="logo/DuckDB_Logo-horizontal.svg">
    <source media="(prefers-color-scheme: dark)" srcset="logo/DuckDB_Logo-horizontal-dark-mode.svg">
    <img alt="DuckDB logo" src="logo/DuckDB_Logo-horizontal.svg" height="100">
  </picture>
</div>
<br>

<p align="center">
  <a href="https://github.com/duckdb/duckdb/actions"><img src="https://github.com/duckdb/duckdb/actions/workflows/Main.yml/badge.svg?branch=main" alt="Github Actions Badge"></a>
  <a href="https://discord.gg/tcvwpjfnZx"><img src="https://shields.io/discord/909674491309850675" alt="discord" /></a>
  <a href="https://github.com/duckdb/duckdb/releases/"><img src="https://img.shields.io/github/v/release/duckdb/duckdb?color=brightgreen&display_name=tag&logo=duckdb&logoColor=white" alt="Latest Release"></a>
</p>

## DuckDB

DuckDB is a high-performance analytical database system. It is designed to be fast, reliable, portable, and easy to use. DuckDB provides a rich SQL dialect with support far beyond basic SQL. DuckDB supports arbitrary and nested correlated subqueries, window functions, collations, complex types (arrays, structs, maps), and [several extensions designed to make SQL easier to use](https://duckdb.org/docs/current/sql/dialect/friendly_sql.html).

DuckDB is available as a [standalone CLI application](https://duckdb.org/docs/current/clients/cli/overview) and has clients for [Python](https://duckdb.org/docs/current/clients/python/overview), [R](https://duckdb.org/docs/current/clients/r), [Java](https://duckdb.org/docs/current/clients/java), [Wasm](https://duckdb.org/docs/current/clients/wasm/overview), etc., with deep integrations with packages such as [pandas](https://duckdb.org/docs/guides/python/sql_on_pandas) and [dplyr](https://duckdb.org/docs/current/clients/r#duckplyr-dplyr-api).

For more information on using DuckDB, please refer to the [DuckDB documentation](https://duckdb.org/docs/current/).

## Installation

If you want to install DuckDB, please see [our installation page](https://duckdb.org/docs/installation/) for instructions.

## Data Import

For CSV files and Parquet files, data import is as simple as referencing the file in the FROM clause:

```sql
SELECT * FROM 'myfile.csv';
SELECT * FROM 'myfile.parquet';
```

Refer to our [Data Import](https://duckdb.org/docs/current/data/overview) section for more information.

## SQL Reference

The documentation contains a [SQL introduction and reference](https://duckdb.org/docs/current/sql/introduction).

## Development

For development, DuckDB requires [CMake](https://cmake.org), Python 3 and a `C++17` compliant compiler. In the root directory, run `make` to compile the sources. For development, use `make debug` to build a non-optimized debug version. You should run `make unit` and `make allunit` to verify that your version works properly after making changes. To test performance, you can run `BUILD_BENCHMARK=1 BUILD_TPCH=1 make` and then perform several standard benchmarks from the root directory by executing `./build/release/benchmark/benchmark_runner`. The details of benchmarks are in our [Benchmark Guide](benchmark/README.md).

Please also refer to our [Build Guide](https://duckdb.org/docs/current/dev/building/overview) and [Contribution Guide](CONTRIBUTING.md).

## Support

See the [Support Options](https://ducklabs.com/support/) page and the dedicated [`endoflife.date`](https://endoflife.date/duckdb) page.
