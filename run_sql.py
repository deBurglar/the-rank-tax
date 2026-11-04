
import sqlite3
import pandas as pd
from pathlib import Path

conn = sqlite3.connect("data/expedia.db")

output_dir = Path("outputs/sql")
output_dir.mkdir(parents=True, exist_ok=True)

queries = [
    "01_position_decay",
    "02_booking_window",
    "03_hidden_gems_screen",
]

for name in queries:
    sql_file = Path("sql") / f"{name}.sql"
    sql = sql_file.read_text(encoding="utf-8")

    try:
        df = pd.read_sql_query(sql, conn)

        csv_file = output_dir / f"{name}.csv"
        df.to_csv(csv_file, index=False)

        print(f"\nSUCCESS: {name}")
        print(f"Rows returned: {len(df)}")
        print(f"Saved to: {csv_file}")
        print(df.head(3).to_string(index=False))

    except Exception as error:
        print(f"\nERROR in {name}: {error}")

conn.close()
