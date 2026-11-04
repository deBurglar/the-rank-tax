-- SQL-only first-cut gem screen. Appeal comes from RANDOM searches (position-free, shrunk toward the global mean);
-- rank comes from NORMAL searches. Gem = top-3 appeal decile but bottom-3 rank decile, 4+ stars. Python refines it with a GBM.
WITH glob AS (SELECT 1.0*SUM(click_bool)/COUNT(*) AS p0 FROM v_imp WHERE random_bool=1),
rnd AS (SELECT prop_id, COUNT(*) AS r_imps, SUM(click_bool) AS r_clicks FROM v_imp WHERE random_bool=1 GROUP BY prop_id),
nrm_rows AS (
  SELECT prop_id, prop_starrating, prop_review_score, price_usd,
         1.0*position/COUNT(*) OVER (PARTITION BY srch_id) AS pos_pct
  FROM v_imp WHERE random_bool=0
), nrm AS (
  SELECT prop_id, MAX(prop_starrating) AS stars, AVG(prop_review_score) AS review, AVG(price_usd) AS avg_price,
         AVG(pos_pct) AS avg_pos_pct, COUNT(*) AS n_imps
  FROM nrm_rows GROUP BY prop_id HAVING COUNT(*) >= 30
), scored AS (
  SELECT n.*, r.r_imps, (r.r_clicks + 50*g.p0)/(r.r_imps + 50.0) AS appeal_shrunk
  FROM nrm n JOIN rnd r USING(prop_id) CROSS JOIN glob g
), ranked AS (
  SELECT *, NTILE(10) OVER (ORDER BY appeal_shrunk) AS appeal_decile,          -- 10 = most appealing
            NTILE(10) OVER (ORDER BY avg_pos_pct DESC) AS rank_decile           -- 1 = worst ranked
  FROM scored
)
SELECT *, (appeal_decile>=8 AND rank_decile<=3 AND stars>=4) AS is_gem_sql
FROM ranked ORDER BY (appeal_decile - rank_decile) DESC;
