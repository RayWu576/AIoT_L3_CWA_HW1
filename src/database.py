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

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS DailyForecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regionName TEXT NOT NULL,
                forecastDate TEXT NOT NULL,
                minT REAL,
                maxT REAL,
                weather TEXT,
                weatherCode TEXT,
                weatherDescription TEXT,
                pop REAL,
                apparentTemperature REAL,
                humidity REAL,
                windDirection TEXT,
                windSpeed TEXT,
                uvIndex REAL,
                uvExposureLevel TEXT,
                updatedAt TEXT NOT NULL,
                UNIQUE(regionName, forecastDate)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS HourlyForecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regionName TEXT NOT NULL,
                forecastTime TEXT NOT NULL,
                temperature REAL,
                apparentTemperature REAL,
                humidity REAL,
                pop REAL,
                weather TEXT,
                weatherCode TEXT,
                weatherDescription TEXT,
                windDirection TEXT,
                windSpeed TEXT,
                updatedAt TEXT NOT NULL,
                UNIQUE(regionName, forecastTime)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS WeatherRefreshes (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                updatedAt TEXT NOT NULL,
                hourlyDataset TEXT NOT NULL,
                dailyDataset TEXT NOT NULL,
                hourlyIntervalHours INTEGER NOT NULL,
                dailyIntervalHours INTEGER NOT NULL
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



def save_weather_forecasts(weather_data: dict):
    """Upsert normalized hourly and daily forecast rows without replacing the DB."""
    updated_at = weather_data["updatedAt"]
    source = weather_data["source"]
    daily_rows = []
    hourly_rows = []
    for region, forecasts in weather_data.get("regions", {}).items():
        for item in forecasts.get("daily", []):
            daily_rows.append((
                region, item.get("date"), item.get("minTemperature"),
                item.get("maxTemperature"), item.get("weather"),
                item.get("weatherCode"), item.get("weatherDescription"),
                item.get("pop"), item.get("apparentTemperature"),
                item.get("humidity"), item.get("windDirection"),
                str(item["windSpeed"]) if item.get("windSpeed") is not None else None,
                item.get("uvIndex"), item.get("uvExposureLevel"), updated_at,
            ))
        for item in forecasts.get("hourly", []):
            hourly_rows.append((
                region, item.get("datetime"), item.get("temperature"),
                item.get("apparentTemperature"), item.get("humidity"),
                item.get("pop"), item.get("weather"), item.get("weatherCode"),
                item.get("weatherDescription"), item.get("windDirection"),
                str(item["windSpeed"]) if item.get("windSpeed") is not None else None,
                updated_at,
            ))
    if not daily_rows:
        raise ValueError("No daily CWA forecasts were parsed; refusing an empty refresh")
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO DailyForecasts (
                regionName, forecastDate, minT, maxT, weather, weatherCode,
                weatherDescription, pop, apparentTemperature, humidity,
                windDirection, windSpeed, uvIndex, uvExposureLevel, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(regionName, forecastDate) DO UPDATE SET
                minT=excluded.minT, maxT=excluded.maxT, weather=excluded.weather,
                weatherCode=excluded.weatherCode, weatherDescription=excluded.weatherDescription,
                pop=excluded.pop, apparentTemperature=excluded.apparentTemperature,
                humidity=excluded.humidity, windDirection=excluded.windDirection,
                windSpeed=excluded.windSpeed, uvIndex=excluded.uvIndex,
                uvExposureLevel=excluded.uvExposureLevel, updatedAt=excluded.updatedAt
            """,
            daily_rows,
        )
        conn.executemany(
            """
            INSERT INTO HourlyForecasts (
                regionName, forecastTime, temperature, apparentTemperature,
                humidity, pop, weather, weatherCode, weatherDescription,
                windDirection, windSpeed, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(regionName, forecastTime) DO UPDATE SET
                temperature=excluded.temperature,
                apparentTemperature=excluded.apparentTemperature,
                humidity=excluded.humidity, pop=excluded.pop,
                weather=excluded.weather, weatherCode=excluded.weatherCode,
                weatherDescription=excluded.weatherDescription,
                windDirection=excluded.windDirection, windSpeed=excluded.windSpeed,
                updatedAt=excluded.updatedAt
            """,
            hourly_rows,
        )
        conn.execute(
            """
            INSERT INTO WeatherRefreshes (
                id, updatedAt, hourlyDataset, dailyDataset,
                hourlyIntervalHours, dailyIntervalHours
            ) VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updatedAt=excluded.updatedAt,
                hourlyDataset=excluded.hourlyDataset,
                dailyDataset=excluded.dailyDataset,
                hourlyIntervalHours=excluded.hourlyIntervalHours,
                dailyIntervalHours=excluded.dailyIntervalHours
            """,
            (updated_at, source["hourlyDataset"], source["dailyDataset"],
             source["hourlyIntervalHours"], source["dailyIntervalHours"]),
        )
    print(f"Upserted {len(hourly_rows)} timed and {len(daily_rows)} daily forecast records.")
