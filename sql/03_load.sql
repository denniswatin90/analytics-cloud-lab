-- 03_load.sql — file formats, internal stage, PUT and COPY INTO
USE ROLE LAB_ENGINEER;
USE WAREHOUSE LAB_WH;
USE SCHEMA MAC_LAB.RAW;

CREATE OR REPLACE FILE FORMAT CSV_FF
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS'
  NULL_IF = ('', 'NULL');

CREATE OR REPLACE FILE FORMAT JSON_FF TYPE = JSON;

CREATE OR REPLACE STAGE LAB_STAGE COMMENT = 'Landing zone for lab files';

-- ---------------------------------------------------------------------------
-- Upload files. PUT does NOT run in a Snowsight worksheet. Choose one:
--   a) python -m analytics_cloud_lab.loader --data-dir data      (does PUT + COPY for you)
--   b) SnowSQL / Snowflake CLI:
--        PUT file://data/sessions.csv @LAB_STAGE/sessions/ AUTO_COMPRESS=TRUE;
--   c) Snowsight UI: Data > Databases > MAC_LAB > RAW > Stages > LAB_STAGE > + Files
-- ---------------------------------------------------------------------------
LIST @LAB_STAGE;

-- Preview a staged file before loading (great for debugging client files)
SELECT $1, $2, $3, METADATA$FILENAME
FROM @LAB_STAGE/sessions/ (FILE_FORMAT => 'CSV_FF')
LIMIT 5;

-- Dry run: report errors without loading
COPY INTO SESSIONS FROM @LAB_STAGE/sessions/
  FILE_FORMAT = (FORMAT_NAME = 'CSV_FF')
  VALIDATION_MODE = RETURN_ERRORS;

-- Real loads
COPY INTO EXPERIENCES FROM @LAB_STAGE/experiences/ FILE_FORMAT = (FORMAT_NAME = 'CSV_FF');
COPY INTO SESSIONS    FROM @LAB_STAGE/sessions/    FILE_FORMAT = (FORMAT_NAME = 'CSV_FF');
COPY INTO PAGE_VIEWS  FROM @LAB_STAGE/page_views/  FILE_FORMAT = (FORMAT_NAME = 'CSV_FF');
COPY INTO OFFERS      FROM @LAB_STAGE/offers/      FILE_FORMAT = (FORMAT_NAME = 'CSV_FF');
COPY INTO CONVERSIONS FROM @LAB_STAGE/conversions/ FILE_FORMAT = (FORMAT_NAME = 'CSV_FF');

COPY INTO EVENTS_RAW (payload, file_name)
  FROM (SELECT $1, METADATA$FILENAME FROM @LAB_STAGE/events/)
  FILE_FORMAT = (FORMAT_NAME = 'JSON_FF');

-- Load history (what loaded, from which file, any errors)
SELECT table_name, file_name, row_count, error_count, status
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'SESSIONS', START_TIME => DATEADD(hour, -24, CURRENT_TIMESTAMP())));

-- Row counts
SELECT 'sessions' t, COUNT(*) n FROM SESSIONS UNION ALL
SELECT 'page_views', COUNT(*) FROM PAGE_VIEWS UNION ALL
SELECT 'offers', COUNT(*) FROM OFFERS UNION ALL
SELECT 'conversions', COUNT(*) FROM CONVERSIONS UNION ALL
SELECT 'events', COUNT(*) FROM EVENTS_RAW;
