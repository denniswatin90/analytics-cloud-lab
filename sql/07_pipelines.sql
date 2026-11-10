-- 07_pipelines.sql — streams + tasks, dynamic tables, time travel
USE ROLE LAB_ENGINEER;
USE WAREHOUSE LAB_WH;
USE SCHEMA MAC_LAB.ANALYTICS;

-- ===== A. Stream + task: incremental daily revenue ==========================
CREATE OR REPLACE TABLE DAILY_REVENUE (
  client_id STRING, order_date DATE, orders INTEGER, revenue NUMBER(14,2));

CREATE OR REPLACE STREAM CONVERSIONS_STREAM ON TABLE MAC_LAB.RAW.CONVERSIONS;

CREATE OR REPLACE TASK MERGE_DAILY_REVENUE
  WAREHOUSE = LAB_WH
  SCHEDULE = '60 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('MAC_LAB.ANALYTICS.CONVERSIONS_STREAM')
AS
MERGE INTO DAILY_REVENUE t
USING (
  SELECT client_id, conversion_ts::DATE AS order_date,
         COUNT(*) AS orders, SUM(revenue) AS revenue
  FROM CONVERSIONS_STREAM
  WHERE METADATA$ACTION = 'INSERT'
  GROUP BY 1, 2
) s
ON t.client_id = s.client_id AND t.order_date = s.order_date
WHEN MATCHED THEN UPDATE SET t.orders = t.orders + s.orders, t.revenue = t.revenue + s.revenue
WHEN NOT MATCHED THEN INSERT (client_id, order_date, orders, revenue)
                      VALUES (s.client_id, s.order_date, s.orders, s.revenue);

-- Tasks start suspended. Resuming needs EXECUTE TASK (granted by ACCOUNTADMIN):
--   USE ROLE ACCOUNTADMIN; GRANT EXECUTE TASK ON ACCOUNT TO ROLE LAB_ENGINEER;
ALTER TASK MERGE_DAILY_REVENUE RESUME;

-- Test: insert a new order, then run the task now instead of waiting
INSERT INTO MAC_LAB.RAW.CONVERSIONS
VALUES ('O9999999', 'S0000001', 'RETAILER_A', CURRENT_TIMESTAMP()::TIMESTAMP_NTZ, 99.50, 2);
SELECT * FROM CONVERSIONS_STREAM;          -- the new row with METADATA$ columns
EXECUTE TASK MERGE_DAILY_REVENUE;
SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(TASK_NAME => 'MERGE_DAILY_REVENUE'))
ORDER BY scheduled_time DESC LIMIT 5;
SELECT * FROM DAILY_REVENUE ORDER BY order_date DESC LIMIT 5;
ALTER TASK MERGE_DAILY_REVENUE SUSPEND;   -- save credits when not practising

-- ===== B. Dynamic table: declarative alternative ============================
CREATE OR REPLACE DYNAMIC TABLE VARIANT_SUMMARY_DT
  TARGET_LAG = '1 hour'
  WAREHOUSE = LAB_WH
AS
SELECT client_id, experience_id, variant_id,
       COUNT(*) AS sessions, SUM(converted) AS conversions, SUM(revenue) AS total_revenue
FROM MAC_LAB.ANALYTICS.EXPERIMENT_SESSIONS
GROUP BY 1, 2, 3;

SELECT * FROM VARIANT_SUMMARY_DT;
SELECT name, state, refresh_action, refresh_start_time
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY())
ORDER BY refresh_start_time DESC LIMIT 5;
ALTER DYNAMIC TABLE VARIANT_SUMMARY_DT SUSPEND;

-- ===== C. Time travel: recover from mistakes ================================
DELETE FROM MAC_LAB.RAW.CONVERSIONS WHERE order_id = 'O9999999';
SELECT COUNT(*) FROM MAC_LAB.RAW.CONVERSIONS AT (OFFSET => -60);  -- 60 seconds ago
DROP TABLE DAILY_REVENUE;
UNDROP TABLE DAILY_REVENUE;
-- Clone a table as it was 5 minutes ago (zero-copy)
CREATE OR REPLACE TABLE MAC_LAB.RAW.CONVERSIONS_BACKUP CLONE MAC_LAB.RAW.CONVERSIONS AT (OFFSET => -300);
