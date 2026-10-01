"""Fetch CWA forecasts, normalize them, and safely upsert the local SQLite DB."""
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

from src.database import init_db, save_forecasts, save_weather_forecasts
from src.weather_parser import (
    DAILY_DATASET_ID,
    HOURLY_DATASET_ID,
    normalize_forecasts,
    parse_daily_forecasts,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

CWA_DATASET_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/{}"


def _api_key(api_key=None):
    load_dotenv(Path(__file__).resolve().parent / ".env")
    value = api_key or os.getenv("CWA_API_KEY")
    if not value:
        raise ValueError("CWA_API_KEY is missing. Set it in the local .env file.")
    return value


def fetch_cwa_data(api_key=None, dataset_id=DAILY_DATASET_ID):
    """Fetch one CWA nationwide forecast dataset; never log the authorization key."""
    response = requests.get(
        CWA_DATASET_URL.format(dataset_id),
        params={"Authorization": _api_key(api_key), "format": "JSON"},
        timeout=40,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("success") is False:
        raise RuntimeError(f"CWA rejected dataset {dataset_id}")
    return payload


def parse_forecast_data(data):
    """Keep the original minT/maxT DataFrame contract for existing consumers."""
    parsed = parse_daily_forecasts(data)
    rows = []
    for region, daily in parsed.items():
        for item in daily:
            low, high = item.get("minTemperature"), item.get("maxTemperature")
            if low is None or high is None:
                continue
            rows.append({
                "regionName": region,
                "dataDate": item["date"],
                "minT": low,
                "maxT": high,
            })
    frame = pd.DataFrame(rows, columns=["regionName", "dataDate", "minT", "maxT"])
    if not frame.empty:
        frame["minT"] = pd.to_numeric(frame["minT"], errors="coerce")
        frame["maxT"] = pd.to_numeric(frame["maxT"], errors="coerce")
        frame = frame.dropna(subset=["minT", "maxT"])
        frame = frame[frame["minT"] <= frame["maxT"]]
        frame = frame.sort_values(["regionName", "dataDate"]).reset_index(drop=True)
    return frame


def print_data_checkpoint(weather_data):
    """Print one real location/time sample and clearly label missing CWA fields."""
    regions = weather_data.get("regions", {})
    if not regions:
        print("No locations were parsed from the CWA response.")
        return
    region = next(iter(regions))
    forecast = regions[region]
    point = forecast["hourly"][0] if forecast["hourly"] else {}
    day = forecast["daily"][0] if forecast["daily"] else {}

    def show(value, suffix=""):
        return f"{value}{suffix}" if value is not None else "Not available from current dataset"

    print("\nCWA data checkpoint (forecast data, not current observations)")
    print("Location:", region)
    print("Time:", point.get("datetime", "Not available from current dataset"))
    print("Temperature:", show(point.get("temperature"), " ?C"))
    print("Apparent temperature:", show(point.get("apparentTemperature"), " ?C"))
    print("Relative humidity:", show(point.get("humidity"), "%"))
    print("Probability of precipitation:", show(point.get("pop"), "%"))
    print("Weather:", show(point.get("weather")))
    print("Wind direction:", show(point.get("windDirection")))
    print("Wind speed:", show(point.get("windSpeed"), " m/s"))
    print("UV index:", show(day.get("uvIndex")))
    print("Actual 3-hourly periods:", len(forecast["hourly"]))
    print("Actual 12-hour daily periods:", len(forecast["daily"]))


def main():
    print(f"Fetching CWA datasets {HOURLY_DATASET_ID} and {DAILY_DATASET_ID}...")
    hourly_payload = fetch_cwa_data(dataset_id=HOURLY_DATASET_ID)
    daily_payload = fetch_cwa_data(dataset_id=DAILY_DATASET_ID)
    updated_at = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    weather_data = normalize_forecasts(hourly_payload, daily_payload, updated_at)
    daily_frame = parse_forecast_data(daily_payload)
    if daily_frame.empty:
        raise RuntimeError("CWA returned no valid daily temperature ranges; database not changed")
    print("Parsed daily rows:", len(daily_frame))
    print("Parsed regions:", daily_frame["regionName"].nunique())
    print("DataFrame columns:", ", ".join(daily_frame.columns))
    print_data_checkpoint(weather_data)
    init_db()
    save_forecasts(daily_frame)
    save_weather_forecasts(weather_data)
    print("CWA snapshot updated at:", updated_at)


if __name__ == "__main__":
    main()
