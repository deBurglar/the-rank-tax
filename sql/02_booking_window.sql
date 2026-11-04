-- Cohorts by lead time x length of stay x position tier x relative price (random searches only = no rank confounding).
WITH s AS (
  SELECT *, AVG(price_usd) OVER (PARTITION BY srch_id) AS srch_avg_price
  FROM v_imp WHERE random_bool = 1
)
SELECT
  CASE WHEN srch_booking_window<=1 THEN '1) 0-1d' WHEN srch_booking_window<=7 THEN '2) 2-7d'
       WHEN srch_booking_window<=30 THEN '3) 8-30d' WHEN srch_booking_window<=90 THEN '4) 31-90d' ELSE '5) 90d+' END AS bw_bucket,
  CASE WHEN srch_length_of_stay<=2 THEN 'short (1-2n)' WHEN srch_length_of_stay<=5 THEN 'mid (3-5n)' ELSE 'long (6n+)' END AS los_bucket,
  CASE WHEN position<=5 THEN 'top5' WHEN position<=15 THEN '6-15' ELSE '16+' END AS pos_tier,
  CASE WHEN price_usd>srch_avg_price THEN 'above_avg' ELSE 'at_or_below_avg' END AS price_tier,
  COUNT(*) AS imps, ROUND(AVG(click_bool),5) AS ctr, ROUND(AVG(booking_bool),5) AS cvr
FROM s GROUP BY 1,2,3,4 ORDER BY 1,2,3,4;
