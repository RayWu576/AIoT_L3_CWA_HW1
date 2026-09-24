"""Build Folium maps from daily forecast rows."""
from html import escape
from math import isfinite
import folium
from src.locations import REGION_COORDINATES


def get_temperature_color(avg_temp):
    if avg_temp < 20:
        return "blue"
    if avg_temp < 25:
        return "green"
    if avg_temp <= 30:
        return "orange"
    return "red"


def create_weather_map(rows):
    weather_map = folium.Map(location=[23.7, 121.0], zoom_start=7,
                             tiles="OpenStreetMap")
    warnings = []
    count = 0
    for row in rows:
        region = row["regionName"]
        if region not in REGION_COORDINATES:
            warnings.append(f"{region} 找不到座標資料，因此未顯示在地圖上。")
            continue
        try:
            low, high = float(row["minT"]), float(row["maxT"])
            if not (isfinite(low) and isfinite(high)) or low > high:
                raise ValueError("Invalid temperatures")
        except (TypeError, ValueError):
            warnings.append(f"{region} 溫度資料不完整，因此未顯示在地圖上。")
            continue
        average = (low + high) / 2
        forecast_date = escape(str(row.get("dataDate", "N/A")))
        marker_color = get_temperature_color(average)
        folium.CircleMarker(
            location=REGION_COORDINATES[region],
            radius=9,
            color=marker_color,
            weight=2,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.9,
            tooltip=escape(region),
            popup=folium.Popup(
                f"<b>{escape(region)}</b><br>\u65e5\u671f:{forecast_date}<br>"
                f"\u6700\u4f4e\u6eab:{low:.1f} \u00b0C<br>"
                f"\u6700\u9ad8\u6eab:{high:.1f} \u00b0C<br>"
                f"\u5e73\u5747\u6eab:{average:.1f} \u00b0C",
                max_width=260),
        ).add_to(weather_map)
        count += 1
    # Include offshore counties in the initial viewport, also on mobile.
    weather_map.fit_bounds([[21.8, 118.1], [26.4, 122.1]])
    return weather_map, warnings, count
