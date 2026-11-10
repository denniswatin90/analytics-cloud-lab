-- 04_analysis.sql — experiment analysis views (the queries clients ask for)
USE ROLE LAB_ENGINEER;
USE WAREHOUSE LAB_WH;
USE SCHEMA MAC_LAB.ANALYTICS;

-- 1. Duplicates check: why QUALIFY is needed
SELECT session_id, experience_id, COUNT(*) AS rows_per_session
FROM MAC_LAB.RAW.OFFERS
GROUP BY 1, 2
HAVING COUNT(*) > 1
ORDER BY 3 DESC
LIMIT 10;

-- 2. First qualification per session and experience
CREATE OR REPLACE VIEW FIRST_OFFER AS
SELECT client_id, session_id, experience_id, variant_id, first_qualified_ts
FROM MAC_LAB.RAW.OFFERS
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY session_id, experience_id ORDER BY first_qualified_ts) = 1;

-- 3. Session-level outcome: only conversions AT/AFTER first qualification count
CREATE OR REPLACE VIEW EXPERIMENT_SESSIONS AS
SELECT f.client_id, f.experience_id, f.variant_id, f.session_id,
       IFF(COUNT(c.order_id) > 0, 1, 0) AS converted,
       COALESCE(SUM(c.revenue), 0)      AS revenue
FROM FIRST_OFFER f
LEFT JOIN MAC_LAB.RAW.CONVERSIONS c
  ON c.session_id = f.session_id
 AND c.conversion_ts >= f.first_qualified_ts
GROUP BY 1, 2, 3, 4;

-- 4. Variant summary (read by analytics_cloud_lab.report)
CREATE OR REPLACE VIEW VARIANT_SUMMARY AS
SELECT client_id, experience_id, variant_id,
       COUNT(*)                       AS sessions,
       SUM(converted)                 AS conversions,
       SUM(revenue)                   AS total_revenue,
       SUM(converted) / COUNT(*)      AS conversion_rate,
       SUM(revenue) / COUNT(*)        AS revenue_per_session
FROM EXPERIMENT_SESSIONS
GROUP BY 1, 2, 3;

-- 5. Lift vs control with a window function
SELECT experience_id, variant_id, sessions, conversions,
       ROUND(conversion_rate, 4) AS conversion_rate,
       ROUND(conversion_rate /
             MAX(IFF(variant_id = 'control', conversion_rate, NULL))
               OVER (PARTITION BY experience_id) - 1, 4) AS relative_lift
FROM VARIANT_SUMMARY
ORDER BY experience_id, variant_id;

-- 6. Segment cut: lift by device (clients always ask "does it work on mobile?")
SELECT es.experience_id, s.device_type, es.variant_id,
       COUNT(*) AS sessions, AVG(es.converted) AS conversion_rate
FROM EXPERIMENT_SESSIONS es
JOIN MAC_LAB.RAW.SESSIONS s USING (session_id)
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

-- 7. Funnel by page type
SELECT s.client_id,
       COUNT(DISTINCT pv.session_id) AS sessions,
       COUNT(DISTINCT IFF(pv.page_type = 'product',  pv.session_id, NULL)) AS reached_product,
       COUNT(DISTINCT IFF(pv.page_type = 'cart',     pv.session_id, NULL)) AS reached_cart,
       COUNT(DISTINCT IFF(pv.page_type = 'checkout', pv.session_id, NULL)) AS reached_checkout
FROM MAC_LAB.RAW.PAGE_VIEWS pv
JOIN MAC_LAB.RAW.SESSIONS s USING (session_id)
GROUP BY 1;

-- 8. Path analysis: sessions that went product -> cart -> checkout (MATCH_RECOGNIZE)
SELECT *
FROM MAC_LAB.RAW.PAGE_VIEWS
MATCH_RECOGNIZE (
  PARTITION BY session_id
  ORDER BY page_view_ts
  MEASURES FIRST(prod.page_view_ts) AS first_product_ts,
           LAST(chk.page_view_ts)   AS checkout_ts,
           COUNT(prod.*)            AS product_views
  ONE ROW PER MATCH
  PATTERN (prod+ anypage* cart anypage* chk)
  DEFINE prod AS page_type = 'product',
         cart AS page_type = 'cart',
         chk  AS page_type = 'checkout'
         -- 'anypage' is not defined, so it matches any row
)
LIMIT 20;
