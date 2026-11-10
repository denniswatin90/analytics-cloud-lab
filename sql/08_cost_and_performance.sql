-- 08_cost_and_performance.sql — answer "why is this slow / expensive?"
-- ACCOUNT_USAGE views lag by up to ~45 min–3 h; INFORMATION_SCHEMA is near real time.
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE LAB_WH;

-- Slowest queries in the last 7 days
SELECT query_id, user_name, warehouse_name,
       total_elapsed_time / 1000 AS seconds,
       bytes_scanned / POWER(1024, 3) AS gb_scanned,
       partitions_scanned, partitions_total,
       LEFT(query_text, 120) AS query_start
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
ORDER BY total_elapsed_time DESC
LIMIT 20;

-- Credits per warehouse per day
SELECT warehouse_name, start_time::DATE AS day, SUM(credits_used) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2 ORDER BY 2 DESC, 3 DESC;

-- Queries that spilled to disk (warehouse too small or query too heavy)
SELECT query_id, warehouse_size,
       bytes_spilled_to_local_storage, bytes_spilled_to_remote_storage
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE bytes_spilled_to_local_storage > 0 OR bytes_spilled_to_remote_storage > 0
ORDER BY start_time DESC LIMIT 20;

-- Pruning experiment: compare partitions scanned with and without a filter
USE ROLE LAB_ENGINEER;
SELECT COUNT(*) FROM MAC_LAB.RAW.PAGE_VIEWS;
SELECT COUNT(*) FROM MAC_LAB.RAW.PAGE_VIEWS
WHERE page_view_ts >= '2026-10-25'::TIMESTAMP_NTZ;
-- Open Query Profile for each (Monitoring > Query History) and compare
-- "Partitions scanned" vs "Partitions total".

-- Result cache: run the same query twice; the second is free and instant
ALTER SESSION SET USE_CACHED_RESULT = TRUE;
SELECT * FROM MAC_LAB.ANALYTICS.VARIANT_SUMMARY;
SELECT * FROM MAC_LAB.ANALYTICS.VARIANT_SUMMARY;
