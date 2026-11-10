-- 02_tables.sql — RAW tables matching the generated files
USE ROLE LAB_ENGINEER;
USE WAREHOUSE LAB_WH;
USE SCHEMA MAC_LAB.RAW;

CREATE OR REPLACE TABLE EXPERIENCES (
  experience_id   STRING NOT NULL,
  client_id       STRING NOT NULL,
  experience_name STRING
);

CREATE OR REPLACE TABLE SESSIONS (
  session_id    STRING NOT NULL,
  visitor_id    STRING,
  client_id     STRING NOT NULL,
  session_start TIMESTAMP_NTZ,
  device_type   STRING,
  browser       STRING,
  country       STRING
);

CREATE OR REPLACE TABLE PAGE_VIEWS (
  session_id   STRING NOT NULL,
  page_view_ts TIMESTAMP_NTZ,
  page_type    STRING
);

-- One row per (session, experience) qualification; duplicates exist on purpose
CREATE OR REPLACE TABLE OFFERS (
  client_id          STRING NOT NULL,
  session_id         STRING NOT NULL,
  experience_id      STRING NOT NULL,
  variant_id         STRING NOT NULL,
  first_qualified_ts TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE CONVERSIONS (
  order_id      STRING NOT NULL,
  session_id    STRING NOT NULL,
  client_id     STRING NOT NULL,
  conversion_ts TIMESTAMP_NTZ,
  revenue       NUMBER(12,2),
  items         INTEGER
);

-- Raw JSON events (semi-structured practice)
CREATE OR REPLACE TABLE EVENTS_RAW (
  payload   VARIANT,
  file_name STRING,
  loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

SHOW TABLES IN SCHEMA MAC_LAB.RAW;
