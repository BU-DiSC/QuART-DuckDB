SET threads=4;
SET art_grouped_bulk_load=false;
CREATE TABLE t AS SELECT range::INTEGER AS k FROM range(200000000);
SELECT 'KEYS=' || count(*) FROM t;
.timer on
CREATE INDEX idx ON t(k);
.timer off
DROP INDEX idx;
.timer on
CREATE INDEX idx ON t(k);
.timer off
DROP INDEX idx;
.timer on
CREATE INDEX idx ON t(k);
.timer off
DROP INDEX idx;
PRAGMA enable_profiling='json';
PRAGMA profiling_output='results/2026-10-15_release_socket0_sizes/profiles/sorted_int32_200M_4_false.json';
CREATE INDEX idx ON t(k);
PRAGMA disable_profiling;
DROP INDEX idx;
