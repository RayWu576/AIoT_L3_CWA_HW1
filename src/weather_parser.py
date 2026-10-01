"""Normalize the CWA nationwide 3-day and 1-week forecast payloads."""
from collections import defaultdict
from datetime import datetime
from math import isfinite

HOURLY_DATASET_ID = "F-D0047-089"
DAILY_DATASET_ID = "F-D0047-091"

_REGION_ALIASES = {
    "\u53f0\u5317\u5e02": "\u81fa\u5317\u5e02",
    "\u53f0\u4e2d\u5e02": "\u81fa\u4e2d\u5e02",
    "\u53f0\u5357\u5e02": "\u81fa\u5357\u5e02",
    "\u53f0\u6771\u7e23": "\u81fa\u6771\u7e23",
}

# CWA value keys remain stable when localized ElementName labels change.
_HOURLY_FIELDS = {
    "Temperature": "temperature",
    "ApparentTemperature": "apparentTemperature",
    "RelativeHumidity": "humidity",
    "ProbabilityOfPrecipitation": "pop",
    "Weather": "weather",
    "WeatherCode": "weatherCode",
    "WeatherDescription": "weatherDescription",
    "WindDirection": "windDirection",
    "WindSpeed": "windSpeed",
}
_DAILY_FIELDS = {
    "Temperature": "temperature",
    "MaxTemperature": "maxTemperature",
    "MinTemperature": "minTemperature",
    "RelativeHumidity": "humidity",
    "MaxApparentTemperature": "apparentTemperature",
    "ProbabilityOfPrecipitation": "pop",
    "Weather": "weather",
    "WeatherCode": "weatherCode",
    "WeatherDescription": "weatherDescription",
    "WindDirection": "windDirection",
    "WindSpeed": "windSpeed",
    "UVIndex": "uvIndex",
    "UVExposureLevel": "uvExposureLevel",
}


def _locations(payload):
    records = payload.get("records") or {}
    groups = records.get("Locations") or records.get("locations") or []
    if isinstance(groups, dict):
        groups = [groups]
    if groups:
        group = groups[0]
        result = group.get("Location") or group.get("location") or []
        return result if isinstance(result, list) else []
    result = records.get("Location") or records.get("location") or []
    return result if isinstance(result, list) else []


def _region_name(location):
    raw = location.get("LocationName") or location.get("locationName") or ""
    return _REGION_ALIASES.get(raw, raw)


def _series(location, known_fields):
    """Return {normalized field: {ISO timestamp: raw CWA value}}."""
    output = {value: {} for value in known_fields.values()}
    elements = location.get("WeatherElement") or location.get("weatherElement") or []
    for element in elements:
        for entry in element.get("Time") or element.get("time") or []:
            timestamp = (entry.get("DataTime") or entry.get("StartTime")
                         or entry.get("startTime"))
            if not timestamp:
                continue
            values = entry.get("ElementValue") or entry.get("elementValue") or []
            if isinstance(values, dict):
                values = [values]
            for value_group in values:
                for key, value in value_group.items():
                    normalized = known_fields.get(key)
                    if normalized is not None and value not in (None, ""):
                        output[normalized][timestamp] = value
    return output


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(result):
        return None
    return int(result) if result.is_integer() else result


def _datetime(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _time_sort(value):
    parsed = _datetime(value)
    return parsed.timestamp() if parsed else float("inf")


def _raw_or_number(value):
    number = _number(value)
    if number is not None:
        return number
    return value if isinstance(value, str) and value.strip() else None


def parse_hourly_forecasts(payload):
    """Parse the nationwide 3-hourly weather fields (CWA F-D0047-089)."""
    result = {}
    for location in _locations(payload):
        region = _region_name(location)
        if not region:
            continue
        values = _series(location, _HOURLY_FIELDS)
        timestamps = sorted(set(values["weather"]) | set(values["pop"]),
                            key=_time_sort)
        hourly = []
        for timestamp in timestamps:
            parsed_time = _datetime(timestamp)
            if parsed_time is None:
                continue
            point = {
                "time": parsed_time.strftime("%H:%M"),
                "datetime": timestamp,
            }
            for field in _HOURLY_FIELDS.values():
                value = values[field].get(timestamp)
                if field in {"temperature", "apparentTemperature", "humidity", "pop"}:
                    point[field] = _number(value)
                elif field == "windSpeed":
                    # Keep threshold values such as ">= 11" honest instead of coercing them.
                    point[field] = _raw_or_number(value)
                else:
                    point[field] = value.strip() if isinstance(value, str) else value
            hourly.append(point)
        result[region] = hourly
    return result


def parse_daily_forecasts(payload):
    """Parse CWA's 12-hour day/night ranges into one calendar-start-date row."""
    result = {}
    for location in _locations(payload):
        region = _region_name(location)
        if not region:
            continue
        values = _series(location, _DAILY_FIELDS)
        weather_times = values["weather"]
        dates = sorted({timestamp[:10] for timestamp in weather_times})
        daily = []
        for forecast_date in dates:
            period_times = sorted(
                (timestamp for timestamp in weather_times if timestamp[:10] == forecast_date),
                key=_time_sort,
            )
            # Prefer the daytime half-day record; fall back to the first actual period.
            daytime = next((timestamp for timestamp in period_times
                            if 6 <= (_datetime(timestamp).hour if _datetime(timestamp) else -1) < 18),
                           period_times[0] if period_times else None)
            if daytime is None:
                continue
            row = {"date": forecast_date}
            for field in ("minTemperature", "maxTemperature"):
                candidates = [_number(values[field].get(timestamp))
                              for timestamp in period_times]
                candidates = [value for value in candidates if value is not None]
                row[field] = (min(candidates) if field == "minTemperature" else max(candidates)) if candidates else None
            row["weather"] = values["weather"].get(daytime)
            row["weatherCode"] = values["weatherCode"].get(daytime)
            row["weatherDescription"] = values["weatherDescription"].get(daytime)
            row["apparentTemperature"] = _number(values["apparentTemperature"].get(daytime))
            row["humidity"] = _number(values["humidity"].get(daytime))
            row["windDirection"] = values["windDirection"].get(daytime)
            row["windSpeed"] = _raw_or_number(values["windSpeed"].get(daytime))
            pop_values = [_number(values["pop"].get(timestamp)) for timestamp in period_times]
            pop_values = [value for value in pop_values if value is not None]
            row["pop"] = max(pop_values) if pop_values else None
            uv_values = [_number(values["uvIndex"].get(timestamp)) for timestamp in period_times]
            uv_values = [value for value in uv_values if value is not None]
            row["uvIndex"] = max(uv_values) if uv_values else None
            uv_time = next((timestamp for timestamp in period_times
                            if values["uvIndex"].get(timestamp) is not None), None)
            row["uvExposureLevel"] = values["uvExposureLevel"].get(uv_time) if uv_time else None
            daily.append(row)
        result[region] = daily
    return result


def normalize_forecasts(hourly_payload, daily_payload, updated_at):
    """Build the frontend-safe weather object without CWA's nested JSON."""
    hourly = parse_hourly_forecasts(hourly_payload)
    daily = parse_daily_forecasts(daily_payload)
    regions = {}
    for region in sorted(set(hourly) | set(daily)):
        regions[region] = {
            "current": None,  # Both selected CWA products are forecasts, not observations.
            "hourly": hourly.get(region, []),
            "daily": daily.get(region, []),
        }
    return {
        "updatedAt": updated_at,
        "source": {
            "hourlyDataset": HOURLY_DATASET_ID,
            "dailyDataset": DAILY_DATASET_ID,
            "hourlyIntervalHours": 3,
            "dailyIntervalHours": 12,
        },
        "regions": regions,
    }
