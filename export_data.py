import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "data.db"
OUTPUT_PATH = BASE_DIR / "weather.json"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    """
    SELECT regionName, dataDate, minT, maxT
    FROM TemperatureForecasts
    ORDER BY regionName, dataDate
    """
).fetchall()

data = [dict(row) for row in rows]
conn.close()

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Export completed: {OUTPUT_PATH}")
print(f"Total records: {len(data)}")
