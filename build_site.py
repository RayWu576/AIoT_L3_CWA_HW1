"""Read the existing DB and generate static Vercel assets. No DB writes."""
import json
import re
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from shutil import copyfile, copytree
from src.weather_map import create_weather_map
from src.locations import REGION_COORDINATES

BASE_DIR = Path(__file__).resolve().parent


def build_site(db_path=None, output=None):
    db_path = Path(db_path or BASE_DIR / "data" / "data.db").resolve()
    output = Path(output or BASE_DIR / "public")
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute(
            "SELECT regionName, dataDate, minT, maxT FROM TemperatureForecasts "
            "ORDER BY regionName, dataDate")]
    grouped = {}
    for row in rows:
        row["dataDate"] = date.fromisoformat(str(row["dataDate"])[:10]).isoformat()
        grouped.setdefault(row["dataDate"], []).append(row)
    (output / "maps").mkdir(parents=True, exist_ok=True)
    manifest = {}
    for day, daily_rows in sorted(grouped.items()):
        weather_map, warnings, count = create_weather_map(daily_rows)
        relative_path = f"maps/{day}.html"
        map_path = output / relative_path
        weather_map.save(str(map_path))
        html = map_path.read_text(encoding="utf-8")
        # Folium's default template references several CDNs even though this map
        # only needs Leaflet. Serve its core assets with the site for reliable demos.
        html = re.sub(r"^\s*<script src=\"https?://[^\"]+\"></script>\s*$", "", html, flags=re.MULTILINE)
        html = re.sub(r"^\s*<link rel=\"stylesheet\" href=\"https?://[^\"]+\"\s*/>\s*$", "", html, flags=re.MULTILINE)
        local_assets = (
            '<link rel="stylesheet" href="../static/vendor/leaflet.css"/>\n'
            '<script src="../static/vendor/jquery.min.js"></script>\n'
            '<script src="../static/vendor/leaflet.js"></script>\n'
        )
        html = html.replace("<head>", "<head>\n    " + local_assets, 1)
        map_path.write_text(html, encoding="utf-8")
        manifest[day] = {"url": relative_path, "warnings": warnings, "count": count}
    for filename, data in [
        ("weather.json", rows),
        ("maps.json", manifest),
        ("locations.json", REGION_COORDINATES),
    ]:
        (output / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    copyfile(BASE_DIR / "index.html", output / "index.html")
    copytree(BASE_DIR / "static", output / "static", dirs_exist_ok=True)
    print(f"Built {len(rows)} records / {len(manifest)} dates into {output}")
    return manifest


if __name__ == "__main__":
    build_site()
