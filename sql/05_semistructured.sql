-- 05_semistructured.sql — VARIANT, path notation, LATERAL FLATTEN
USE ROLE LAB_ENGINEER;
USE WAREHOUSE LAB_WH;
USE SCHEMA MAC_LAB.RAW;

-- Look at raw JSON
SELECT payload FROM EVENTS_RAW LIMIT 5;

-- Path notation + casting
SELECT payload:event_type::STRING          AS event_type,
       payload:session_id::STRING          AS session_id,
       payload:ts::TIMESTAMP_NTZ           AS event_ts,
       payload:properties:page_type::STRING AS page_type
FROM EVENTS_RAW
LIMIT 10;

-- Count by event type
SELECT payload:event_type::STRING AS event_type, COUNT(*) AS events
FROM EVENTS_RAW GROUP BY 1;

-- Explode the products array in purchase events: one row per product
SELECT e.payload:properties:order_id::STRING AS order_id,
       p.index                               AS line_no,
       p.value:sku::STRING                   AS sku,
       p.value:price::NUMBER(10,2)           AS price
FROM EVENTS_RAW e,
     LATERAL FLATTEN(INPUT => e.payload:properties:products) p
WHERE e.payload:event_type::STRING = 'purchase'
LIMIT 20;

-- Top products by purchases
SELECT p.value:sku::STRING AS sku, COUNT(*) AS times_purchased
FROM EVENTS_RAW e,
     LATERAL FLATTEN(INPUT => e.payload:properties:products) p
WHERE e.payload:event_type::STRING = 'purchase'
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;

-- Typed view over JSON (what you'd hand a client analyst)
CREATE OR REPLACE VIEW MAC_LAB.ANALYTICS.PURCHASE_LINES AS
SELECT e.payload:client_id::STRING           AS client_id,
       e.payload:session_id::STRING          AS session_id,
       e.payload:properties:order_id::STRING AS order_id,
       e.payload:ts::TIMESTAMP_NTZ           AS purchase_ts,
       p.value:sku::STRING                   AS sku,
       p.value:price::NUMBER(10,2)           AS price
FROM EVENTS_RAW e,
     LATERAL FLATTEN(INPUT => e.payload:properties:products) p
WHERE e.payload:event_type::STRING = 'purchase';
