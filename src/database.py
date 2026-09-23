from pathlib import Path
import sqlite3
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "data.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    return conn


def init_db():
    conn = get_connection()

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regionName TEXT NOT NULL,
                dataDate TEXT NOT NULL,
                minT REAL,
                maxT REAL,
                UNIQUE(regionName, dataDate)
            );
            """
        )

        conn.commit()

    finally:
        conn.close()


def save_forecasts(df: pd.DataFrame):
    if df.empty:
        print("DataFrame is empty. Nothing to save.")
        return

    required_columns = {
        "regionName",
        "dataDate",
        "minT",
        "maxT",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    conn = get_connection()

    try:
        cursor = conn.cursor()

        sql = """
        INSERT INTO TemperatureForecasts (
            regionName,
            dataDate,
            minT,
            maxT
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(regionName, dataDate)
        DO UPDATE SET
            minT = excluded.minT,
            maxT = excluded.maxT;
        """

        records = []

        for _, row in df.iterrows():
            records.append(
                (
                    row["regionName"],
                    row["dataDate"],
                    row["minT"],
                    row["maxT"],
                )
            )

        cursor.executemany(sql, records)

        conn.commit()

        print(
            f"Saved {len(records)} forecast records to {DB_PATH}"
        )

    finally:
        conn.close()
