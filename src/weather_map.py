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
        folium.Marker(
            location=REGION_COORDINATES[region],
            tooltip=escape(region),
            popup=folium.Popup(
                f"<b>{escape(region)}</b><br>最低溫：{low:.1f} °C<br>"
                f"最高溫：{high:.1f} °C<br>平均溫：{average:.1f} °C",
                max_width=260),
            icon=folium.Icon(color=get_temperature_color(average), icon="info-sign")
        ).add_to(weather_map)
        count += 1
    # Include offshore counties in the initial viewport, also on mobile.
    weather_map.fit_bounds([[21.8, 118.1], [26.4, 122.1]])
    return weather_map, warnings, count
