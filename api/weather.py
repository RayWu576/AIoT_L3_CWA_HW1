"""Read-only Vercel API for the latest normalized CWA forecast snapshot."""
import json
import re
from datetime import date
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

DATA_PATH = Path(__file__).resolve().parent.parent / "public" / "weather-data.json"
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_weather_response(data, region=None, forecast_date=None):
    regions = data.get("regions", {})
    if region and region not in regions:
        return 404, {"error": "Unknown region"}
    if forecast_date:
        if not _DATE_PATTERN.fullmatch(forecast_date):
            return 400, {"error": "Date must use YYYY-MM-DD"}
        try:
            date.fromisoformat(forecast_date)
        except ValueError:
            return 400, {"error": "Date is not a valid calendar date"}
    if not region:
        if not forecast_date:
            return 200, data
        filtered = {}
        for name, forecasts in regions.items():
            filtered[name] = {
                **forecasts,
                "hourly": [row for row in forecasts.get("hourly", [])
                           if row.get("datetime", "")[:10] == forecast_date],
                "daily": [row for row in forecasts.get("daily", [])
                          if row.get("date") == forecast_date],
            }
        return 200, {**data, "regions": filtered}
    forecasts = regions[region]
    hourly = forecasts.get("hourly", [])
    daily = forecasts.get("daily", [])
    if forecast_date:
        hourly = [row for row in hourly if row.get("datetime", "")[:10] == forecast_date]
        daily = [row for row in daily if row.get("date") == forecast_date]
    return 200, {
        "location": region,
        # The selected CWA products contain forecasts, not station observations.
        "current": forecasts.get("current"),
        "hourly": hourly,
        "daily": daily,
        "updatedAt": data.get("updatedAt"),
        "source": data.get("source", {}),
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with DATA_PATH.open(encoding="utf-8") as stream:
                data = json.load(stream)
            query = parse_qs(urlsplit(self.path).query)
            status, result = get_weather_response(
                data,
                region=query.get("region", [None])[0],
                forecast_date=query.get("date", [None])[0],
            )
        except (OSError, json.JSONDecodeError):
            status, result = 503, {"error": "Weather snapshot is not available"}
        payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, s-maxage=300, stale-while-revalidate=900")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return
