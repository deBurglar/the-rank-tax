"""Load any Expedia-schema CSV (synthetic or real train.csv) into SQLite. Usage: python 02_load_db.py [csv]"""
import sqlite3, sys, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
src = sys.argv[1] if len(sys.argv) > 1 else ROOT/"data/sample_expedia.csv"
cols = ["srch_id","prop_id","prop_starrating","prop_review_score","prop_location_score1","price_usd",
        "promotion_flag","srch_length_of_stay","srch_booking_window","random_bool","position","click_bool","booking_bool"]
con = sqlite3.connect(ROOT/"data/expedia.db")
con.executescript("DROP VIEW IF EXISTS v_imp; DROP TABLE IF EXISTS impressions;")
for ch in pd.read_csv(src, usecols=cols, chunksize=500_000):
    ch.to_sql("impressions", con, if_exists="append", index=False)
con.executescript("""CREATE INDEX ix_s ON impressions(srch_id); CREATE INDEX ix_p ON impressions(prop_id);
CREATE INDEX ix_r ON impressions(random_bool, position);
-- cleaning layer: drop absurd prices (real data has $19M rows), positions >40, zero-night stays
CREATE VIEW v_imp AS SELECT * FROM impressions
 WHERE price_usd BETWEEN 10 AND 2000 AND position<=40 AND srch_length_of_stay>0;""")
print(con.execute("SELECT COUNT(*), SUM(random_bool) FROM v_imp").fetchone(), "rows / random rows")
