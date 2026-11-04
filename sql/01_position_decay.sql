-- Position-decay table: click & booking rate by position, random vs normally-ranked searches.
WITH pos AS (
  SELECT random_bool, position, COUNT(*) AS impressions, SUM(click_bool) AS clicks, SUM(booking_bool) AS bookings
  FROM v_imp GROUP BY random_bool, position
), rates AS (
  SELECT *, 1.0*clicks/impressions AS ctr, 1.0*bookings/impressions AS cvr FROM pos
), w AS (
  SELECT *,
    AVG(ctr) OVER (PARTITION BY random_bool ORDER BY position ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING) AS ctr_smooth,
    FIRST_VALUE(ctr) OVER (PARTITION BY random_bool ORDER BY position) AS ctr_pos1,
    LAG(ctr) OVER (PARTITION BY random_bool ORDER BY position) AS ctr_prev
  FROM rates
)
SELECT random_bool, position, impressions, clicks, bookings,
       ROUND(ctr,5) AS ctr, ROUND(cvr,5) AS cvr, ROUND(ctr_smooth,5) AS ctr_smooth,
       ROUND(ctr/ctr_pos1,3) AS ctr_index_vs_pos1, ROUND(ctr-ctr_prev,5) AS marginal_ctr_drop
FROM w ORDER BY random_bool, position;
