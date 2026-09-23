import os
import sys
import json
import pandas as pd
import requests
from dotenv import load_dotenv

# Ensure console output handles UTF-8 properly on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Use truststore if available to leverage Windows OS certificate store for CWA
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# -----------------------------
# 1. Load environment variables
# -----------------------------
load_dotenv()

API_KEY = os.getenv("CWA_API_KEY")

if not API_KEY:
    raise ValueError(
        "CWA_API_KEY not found. "
        "Please check whether .env exists and contains CWA_API_KEY."
    )


# -----------------------------
# 2. CWA API endpoint
# -----------------------------
# CWA 臺灣各縣市未來1週天氣預報 dataset ID: F-D0047-091
url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091"


# -----------------------------
# 3. Query parameters
# -----------------------------
params = {
    "Authorization": API_KEY,
    "format": "JSON",
}


# -----------------------------
# 4. Send request
# -----------------------------
print("Requesting CWA API...")

response = requests.get(
    url,
    params=params,
    timeout=15,
)

print("HTTP status code:", response.status_code)
response.raise_for_status()


# -----------------------------
# 5. Convert response to JSON
# -----------------------------
data = response.json()

print("\nAPI request successful.")


# ==========================================
# M1-2 Checkpoint Outputs
# ==========================================
print("\n" + "=" * 50)
print("M1-2 Checkpoint Outputs")
print("=" * 50)

print("\n1. Top-level JSON keys (data.keys()):")
print(data.keys())

records = data.get("records", {})
print("\n2. Records keys:")
print(records.keys())

# Extract location list
# Note: In CWA dataset F-D0047-091, records has 'Locations' containing 'Location'
locations_group = records.get("Locations") or records.get("locations")
if isinstance(locations_group, list) and len(locations_group) > 0:
    locations = locations_group[0].get("Location") or locations_group[0].get("location")
else:
    locations = records.get("location") or records.get("Location") or []

print(f"\nTotal locations found: {len(locations)}")

if len(locations) > 0:
    first_loc = locations[0]
    first_loc_name = first_loc.get("LocationName") or first_loc.get("locationName")
    print(f"\n3. First location preview (locationName: {first_loc_name}):")
    # Preview location structure (excluding long time arrays for readability)
    sample_preview = {
        "LocationName": first_loc_name,
        "Geocode": first_loc.get("Geocode"),
        "Latitude": first_loc.get("Latitude"),
        "Longitude": first_loc.get("Longitude"),
        "WeatherElement_Count": len(first_loc.get("WeatherElement", [])),
    }
    print(json.dumps(sample_preview, ensure_ascii=False, indent=2))

    # Find MinT and MaxT elements in first location
    weather_elements = first_loc.get("WeatherElement") or first_loc.get("weatherElement") or []
    maxt_elem = next(
        (e for e in weather_elements if e.get("ElementName") in ["最高溫度", "MaxT"]),
        None,
    )
    mint_elem = next(
        (e for e in weather_elements if e.get("ElementName") in ["最低溫度", "MinT"]),
        None,
    )

    print("\n4. MinT / MaxT 實際資料結構 (First 2 time intervals):")
    if maxt_elem:
        print("  MaxT ElementName:", maxt_elem.get("ElementName"))
        print("  MaxT sample time entries:")
        print(json.dumps(maxt_elem.get("Time", [])[:2], ensure_ascii=False, indent=4))
    if mint_elem:
        print("  MinT ElementName:", mint_elem.get("ElementName"))
        print("  MinT sample time entries:")
        print(json.dumps(mint_elem.get("Time", [])[:2], ensure_ascii=False, indent=4))


# ==========================================
# M2: Parse JSON to Pandas DataFrame
# ==========================================
print("\n" + "=" * 50)
print("M2: JSON -> Pandas DataFrame")
print("=" * 50)

rows = []

for loc in locations:
    region_name = loc.get("LocationName") or loc.get("locationName")
    elements = loc.get("WeatherElement") or loc.get("weatherElement") or []

    maxt_elem = next(
        (e for e in elements if e.get("ElementName") in ["最高溫度", "MaxT"]),
        None,
    )
    mint_elem = next(
        (e for e in elements if e.get("ElementName") in ["最低溫度", "MinT"]),
        None,
    )

    if not maxt_elem or not mint_elem:
        continue

    # Map daily MaxT by date (YYYY-MM-DD)
    daily_maxt = {}
    for t in maxt_elem.get("Time", []):
        start_time = t.get("StartTime") or t.get("startTime")
        date_str = start_time[:10]
        val_list = t.get("ElementValue") or t.get("elementValue") or [{}]
        val_raw = val_list[0].get("MaxTemperature") or val_list[0].get("value")
        if val_raw is not None:
            val = float(val_raw)
            daily_maxt[date_str] = max(daily_maxt.get(date_str, -999.0), val)

    # Map daily MinT by date (YYYY-MM-DD)
    daily_mint = {}
    for t in mint_elem.get("Time", []):
        start_time = t.get("StartTime") or t.get("startTime")
        date_str = start_time[:10]
        val_list = t.get("ElementValue") or t.get("elementValue") or [{}]
        val_raw = val_list[0].get("MinTemperature") or val_list[0].get("value")
        if val_raw is not None:
            val = float(val_raw)
            daily_mint[date_str] = min(daily_mint.get(date_str, 999.0), val)

    # Combine by common dates
    dates = sorted(set(daily_maxt.keys()) & set(daily_mint.keys()))
    for d in dates:
        rows.append(
            {
                "regionName": region_name,
                "dataDate": d,
                "minT": daily_mint[d],
                "maxT": daily_maxt[d],
            }
        )

# Construct DataFrame
df = pd.DataFrame(rows)

# Ensure strict columns
df = df[["regionName", "dataDate", "minT", "maxT"]]

# Enforce numeric types
df["minT"] = pd.to_numeric(df["minT"], errors="coerce")
df["maxT"] = pd.to_numeric(df["maxT"], errors="coerce")

# Sort by regionName and dataDate
df = df.sort_values(by=["regionName", "dataDate"]).reset_index(drop=True)


# ==========================================
# Verification & Inspection Outputs
# ==========================================
print("\nprint(df.head(20)):")
print(df.head(20))

print("\nprint(df.shape):")
print(df.shape)

print("\nprint(df.dtypes):")
print(df.dtypes)

print("\nprint(df['regionName'].unique()):")
print(df["regionName"].unique())

print("\nprint(df.isna().sum()):")
print(df.isna().sum())

print("\nprint(df[df['minT'] > df['maxT']]):")
invalid_rows = df[df["minT"] > df["maxT"]]
print(invalid_rows)
print(f"Total invalid rows (minT > maxT): {len(invalid_rows)}")
