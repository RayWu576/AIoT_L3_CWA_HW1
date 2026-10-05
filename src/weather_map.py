"""Build Folium maps from daily forecast rows."""
from html import escape
from math import isfinite

import folium
from branca.element import MacroElement, Template
from src.locations import REGION_COORDINATES


MARKER_MIN_ZOOM = 8


def get_temperature_color(avg_temp):
    if avg_temp < 20:
        return "blue"
    if avg_temp < 25:
        return "green"
    if avg_temp <= 30:
        return "orange"
    return "red"


def _popup_html(region, forecast_date, low, high, average):
    return f"""
    <section class="weather-popup">
      <div class="weather-popup__eyebrow">DAILY FORECAST</div>
      <div class="weather-popup__title">{escape(region)}</div>
      <div class="weather-popup__date">{forecast_date}</div>
      <div class="weather-popup__temperatures">
        <div class="weather-popup__temperature weather-popup__temperature--low">
          <span>\u6700\u4f4e\u6eab</span><strong>{low:.1f}\u00b0</strong>
        </div>
        <div class="weather-popup__temperature weather-popup__temperature--high">
          <span>\u6700\u9ad8\u6eab</span><strong>{high:.1f}\u00b0</strong>
        </div>
      </div>
      <div class="weather-popup__average"><span>\u5e73\u5747\u6eab</span><strong>{average:.1f} \u00b0C</strong></div>
    </section>
    """


def _add_map_styles(weather_map):
    weather_map.get_root().header.add_child(folium.Element("""
    <style>
      .leaflet-interactive.weather-marker {
        filter: drop-shadow(0 2px 4px rgba(3, 12, 24, .48));
        transition: filter .16s ease, stroke-width .16s ease;
      }
      .leaflet-interactive.weather-marker:hover {
        filter: drop-shadow(0 0 7px rgba(255, 255, 255, .8));
        stroke-width: 3px;
      }
      .leaflet-tooltip.weather-tooltip {
        border: 1px solid rgba(255,255,255,.28);
        border-radius: 9px;
        background: #101b2b;
        color: #f1f6fc;
        box-shadow: 0 6px 20px rgba(0,0,0,.24);
        font: 600 12px/1.3 system-ui, sans-serif;
        padding: 7px 10px;
      }
      .leaflet-tooltip.weather-tooltip:before { border-top-color: #101b2b; }
      .leaflet-popup-content-wrapper {
        padding: 0 !important;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.34);
        border-radius: 16px !important;
        background: #111d2d !important;
        box-shadow: 0 14px 38px rgba(4,12,22,.38) !important;
      }
      .leaflet-popup-content { margin: 0 !important; width: 250px !important; }
      .leaflet-popup-tip { background: #111d2d !important; }
      .leaflet-popup-close-button {
        z-index: 2;
        padding: 8px 10px 0 0 !important;
        color: #a8bbd1 !important;
        font: 400 20px/1 system-ui, sans-serif !important;
      }
      .weather-popup {
        box-sizing: border-box;
        padding: 16px;
        color: #eaf1f9;
        font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        background: radial-gradient(130% 110% at 100% 0%, #233a55 0%, #142338 48%, #101a29 100%);
      }
      .weather-popup__eyebrow {
        margin-bottom: 4px;
        color: #92a8c1;
        font-size: 9px;
        font-weight: 800;
        letter-spacing: .16em;
      }
      .weather-popup__title { color: #f5f8fc; font-size: 19px; font-weight: 750; line-height: 1.3; }
      .weather-popup__date { margin-top: 3px; color: #a9bbcf; font-size: 12px; }
      .weather-popup__temperatures { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin-top: 14px; }
      .weather-popup__temperature {
        display: flex; flex-direction: column; gap: 5px;
        padding: 10px 11px; border: 1px solid rgba(182,205,231,.12);
        border-radius: 11px; background: rgba(255,255,255,.055);
      }
      .weather-popup__temperature span, .weather-popup__average span { color: #9db0c6; font-size: 11px; }
      .weather-popup__temperature strong { font-size: 21px; line-height: 1; }
      .weather-popup__temperature--low strong { color: #8fd0e2; }
      .weather-popup__temperature--high strong { color: #ffbc88; }
      .weather-popup__average {
        display: flex; align-items: center; justify-content: space-between;
        margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(182,205,231,.14);
      }
      .weather-popup__average strong { color: #f4f7fb; font-size: 15px; }
      .weather-zoom-hint {
        margin-top: 8px; padding: 8px 11px; border: 1px solid rgba(255,255,255,.18);
        border-radius: 10px; background: rgba(16,27,43,.94); color: #e5edf7;
        box-shadow: 0 4px 14px rgba(0,0,0,.18); font: 600 11px/1.35 system-ui, sans-serif;
      }
    </style>
    """))


def _add_zoom_gated_markers(weather_map, markers):
    marker_names = ",".join(marker.get_name() for marker in markers)
    controller = MacroElement()
    controller._template = Template(f"""{{% macro script(this, kwargs) %}}
    (function () {{
      const map = {weather_map.get_name()};
      const markers = [{marker_names}];
      const minZoom = {MARKER_MIN_ZOOM};
      const hint = L.control({{ position: "topleft" }});
      hint.onAdd = function () {{
        const element = L.DomUtil.create("div", "weather-zoom-hint");
        element.textContent = "\u653e\u5927\u5730\u5716\uff0c\u67e5\u770b\u5404\u7e23\u5e02\u5929\u6c23";
        L.DomEvent.disableClickPropagation(element);
        return element;
      }};
      hint.addTo(map);
      function updateMarkerVisibility() {{
        const visible = map.getZoom() >= minZoom;
        markers.forEach(function (marker) {{
          if (visible && !map.hasLayer(marker)) marker.addTo(map);
          else if (!visible && map.hasLayer(marker)) map.removeLayer(marker);
        }});
        hint.getContainer().style.display = visible ? "none" : "block";
      }}
      map.on("zoomend", updateMarkerVisibility);
      updateMarkerVisibility();
    }})();
    {{% endmacro %}}
    """)
    controller.add_to(weather_map)


def create_weather_map(rows):
    weather_map = folium.Map(location=[23.7, 121.0], zoom_start=7,
                             tiles="OpenStreetMap", control_scale=True)
    _add_map_styles(weather_map)
    warnings = []
    markers = []
    count = 0
    for row in rows:
        region = row["regionName"]
        if region not in REGION_COORDINATES:
            warnings.append(f"{region} \u627e\u4e0d\u5230\u5ea7\u6a19\u8cc7\u6599\uff0c\u672a\u986f\u793a\u5728\u5730\u5716\u4e0a")
            continue
        try:
            low, high = float(row["minT"]), float(row["maxT"])
            if not (isfinite(low) and isfinite(high)) or low > high:
                raise ValueError("Invalid temperatures")
        except (TypeError, ValueError):
            warnings.append(f"{region} \u6eab\u5ea6\u8cc7\u6599\u7121\u6548\uff0c\u672a\u986f\u793a\u5728\u5730\u5716\u4e0a")
            continue
        average = (low + high) / 2
        forecast_date = escape(str(row.get("dataDate", "N/A")))
        marker_color = get_temperature_color(average)
        marker = folium.CircleMarker(
            location=REGION_COORDINATES[region],
            radius=8,
            color="white",
            weight=2,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.95,
            className="weather-marker",
            tooltip=folium.Tooltip(
                f"{escape(region)} \u00b7 {average:.1f}\u00b0C",
                sticky=True, class_name="weather-tooltip"),
            popup=folium.Popup(
                _popup_html(region, forecast_date, low, high, average),
                max_width=280, parse_html=True),
        )
        markers.append(marker.add_to(weather_map))
        count += 1
    _add_zoom_gated_markers(weather_map, markers)
    # Include offshore counties in the initial viewport, also on mobile.
    weather_map.fit_bounds([[21.8, 118.1], [26.4, 122.1]])
    return weather_map, warnings, count
