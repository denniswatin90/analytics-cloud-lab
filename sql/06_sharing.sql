-- 06_sharing.sql — secure views, row-level filtering per client, shares, reader accounts
-- Provider side = you acting as Monetate. Run as ACCOUNTADMIN where noted.
USE ROLE LAB_ENGINEER;
USE WAREHOUSE LAB_WH;
USE SCHEMA MAC_LAB.SHARED;

-- 1. Which Snowflake account belongs to which client
CREATE OR REPLACE TABLE CLIENT_ACCOUNT_MAP (
  client_id        STRING,
  account_locator  STRING   -- consumer's CURRENT_ACCOUNT() value
);
-- Put your own locator here to test as provider; add the reader account's locator later.
INSERT INTO CLIENT_ACCOUNT_MAP SELECT 'RETAILER_A', CURRENT_ACCOUNT();

-- 2. Secure views: each consumer sees ONLY their own client's rows
CREATE OR REPLACE SECURE VIEW VARIANT_SUMMARY_SV AS
SELECT v.*
FROM MAC_LAB.ANALYTICS.VARIANT_SUMMARY v
JOIN MAC_LAB.SHARED.CLIENT_ACCOUNT_MAP m
  ON m.client_id = v.client_id
WHERE m.account_locator = CURRENT_ACCOUNT();

CREATE OR REPLACE SECURE VIEW EXPERIMENT_SESSIONS_SV AS
SELECT es.*
FROM MAC_LAB.ANALYTICS.EXPERIMENT_SESSIONS es
JOIN MAC_LAB.SHARED.CLIENT_ACCOUNT_MAP m
  ON m.client_id = es.client_id
WHERE m.account_locator = CURRENT_ACCOUNT();

-- Test as provider: should return RETAILER_A rows only
SELECT DISTINCT client_id FROM VARIANT_SUMMARY_SV;

-- Simulate what another account would see
ALTER SESSION SET SIMULATED_DATA_SHARING_CONSUMER = 'NOT_A_REAL_ACCOUNT';
SELECT COUNT(*) FROM VARIANT_SUMMARY_SV;   -- expect 0
ALTER SESSION UNSET SIMULATED_DATA_SHARING_CONSUMER;

-- 3. Create the share (ACCOUNTADMIN, or a role granted CREATE SHARE)
USE ROLE ACCOUNTADMIN;
CREATE OR REPLACE SHARE MAC_LAB_SHARE COMMENT = 'Experience data for clients';
GRANT USAGE ON DATABASE MAC_LAB TO SHARE MAC_LAB_SHARE;
GRANT USAGE ON SCHEMA MAC_LAB.SHARED TO SHARE MAC_LAB_SHARE;
GRANT SELECT ON VIEW MAC_LAB.SHARED.VARIANT_SUMMARY_SV TO SHARE MAC_LAB_SHARE;
GRANT SELECT ON VIEW MAC_LAB.SHARED.EXPERIMENT_SESSIONS_SV TO SHARE MAC_LAB_SHARE;
SHOW GRANTS TO SHARE MAC_LAB_SHARE;

-- 4. Reader account = a consumer account you create and pay for (clients without Snowflake)
--    Some trial accounts restrict this; if so, use a second free trial as the consumer.
CREATE MANAGED ACCOUNT CLIENT_READER
  ADMIN_NAME = 'client_admin',
  ADMIN_PASSWORD = 'Change-Me-Str0ng-Passw0rd!',
  TYPE = READER;
SHOW MANAGED ACCOUNTS;   -- note the locator and URL

-- 5. Add the consumer and map it to a client
-- ALTER SHARE MAC_LAB_SHARE ADD ACCOUNTS = <consumer_locator>;
-- INSERT INTO MAC_LAB.SHARED.CLIENT_ACCOUNT_MAP VALUES ('RETAILER_B', '<consumer_locator>');

-- ===========================================================================
-- CONSUMER SIDE (log in to the reader / second account):
--   USE ROLE ACCOUNTADMIN;
--   SHOW SHARES;                                       -- see the inbound share
--   CREATE DATABASE MONETATE_DATA FROM SHARE <provider_locator>.MAC_LAB_SHARE;
--   GRANT IMPORTED PRIVILEGES ON DATABASE MONETATE_DATA TO ROLE SYSADMIN;
--   CREATE WAREHOUSE IF NOT EXISTS READER_WH WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60;
--   SELECT * FROM MONETATE_DATA.SHARED.VARIANT_SUMMARY_SV;   -- only RETAILER_B rows
-- ===========================================================================
