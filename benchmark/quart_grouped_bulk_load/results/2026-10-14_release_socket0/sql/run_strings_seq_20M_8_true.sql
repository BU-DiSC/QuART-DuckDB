SET threads=8;
SET art_grouped_bulk_load=true;
CREATE TABLE t AS SELECT 'key_' || lpad(range::VARCHAR, 10, '0') AS k FROM range(20000000);
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
PRAGMA profiling_output='results/2026-10-14_release_socket0/profiles/strings_seq_20M_8_true.json';
CREATE INDEX idx ON t(k);
PRAGMA disable_profiling;
DROP INDEX idx;
