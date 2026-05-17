#!/usr/bin/env python3
"""
Fetch the full OSM road network for the ARIA North Karelia AO via the
Overpass API and emit aria_osm_roads.geojson — schema-compatible with the
existing aria_routes.geojson pipeline (LineString features with a `properties.highway` tag).

Usage:
    python3 fetch_osm_roads.py            # fetch + write aria_osm_roads.geojson
    python3 fetch_osm_roads.py --merge    # also merge into aria_routes.geojson (backup created)

Coverage:
    - South: 62.05 (Kitee + buffer)
    - North: 63.60 (Nurmes + buffer)
    - West:  28.90 (Outokumpu + buffer)
    - East:  31.00 (Ilomantsi + Niirala + buffer)

Includes road classes: motorway, trunk, primary, secondary, tertiary,
unclassified, residential. Excludes service/track/path/footway to keep
the file size manageable (rural Finland has many forest tracks that
aren't trafficable supply routes).

────────────────────────────────────────────────────────────────────────
If you'd rather use Overpass Turbo in the browser (https://overpass-turbo.eu),
paste this query and click "Export → download as GeoJSON":

    [out:json][timeout:300];
    (
      way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential)$"]
         (62.05, 28.90, 63.60, 31.00);
    );
    out geom;

Then save the file as aria_osm_roads.geojson next to aria.html.
────────────────────────────────────────────────────────────────────────
"""
import json
import sys
import urllib.request
import urllib.parse
import os
import shutil
import time

BBOX = (62.05, 28.90, 63.60, 31.00)  # (S, W, N, E)
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aria_osm_roads.geojson")
ROUTES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aria_routes.geojson")

HIGHWAY_CLASSES = [
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "unclassified",
    "residential",
]

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def build_query():
    s, w, n, e = BBOX
    regex = "^(" + "|".join(HIGHWAY_CLASSES) + ")$"
    return f"""
[out:json][timeout:300];
(
  way["highway"~"{regex}"]({s},{w},{n},{e});
);
out geom;
""".strip()


def fetch_overpass():
    query = build_query()
    print(f"Querying Overpass for bbox {BBOX} …")
    print(f"  classes: {', '.join(HIGHWAY_CLASSES)}")
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_err = None
    for url in OVERPASS_ENDPOINTS:
        print(f"  → {url}")
        try:
            req = urllib.request.Request(url, data=data, headers={
                "User-Agent": "aria-osm-fetch/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
            })
            with urllib.request.urlopen(req, timeout=360) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            print(f"    failed: {exc}")
            last_err = exc
            time.sleep(2)
    raise RuntimeError(f"All Overpass endpoints failed: {last_err}")


def to_geojson(osm_json):
    """Convert Overpass `out geom;` response to FeatureCollection of LineStrings."""
    features = []
    elements = osm_json.get("elements", [])
    for el in elements:
        if el.get("type") != "way":
            continue
        geom = el.get("geometry")
        if not geom or len(geom) < 2:
            continue
        coords = [[p["lon"], p["lat"]] for p in geom]
        tags = el.get("tags", {}) or {}
        props = {
            "@id": f"way/{el.get('id')}",
            "source": "OSM Overpass",
            "highway": tags.get("highway"),
        }
        for k in ("name", "name:fi", "ref", "bridge", "tunnel", "layer",
                  "surface", "maxspeed", "lanes", "oneway"):
            if k in tags:
                props[k] = tags[k]
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": props,
        })
    return {
        "type": "FeatureCollection",
        "name": "ARIA AO OSM Roads — North Karelia",
        "description": (
            "Full OSM road network (motorway through residential) in the AO bbox, "
            "fetched via Overpass API. Complements Väylävirasto authority data with "
            "regional and municipal roads that aren't in the state-route dataset."
        ),
        "bbox": list(BBOX),
        "features": features,
    }


def merge_into_routes(osm_gj):
    """Append OSM features to aria_routes.geojson, after backing up the original."""
    if not os.path.exists(ROUTES_PATH):
        print(f"  ! {ROUTES_PATH} not found — skipping merge")
        return
    backup = ROUTES_PATH + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(ROUTES_PATH, backup)
        print(f"  backup written → {backup}")

    with open(ROUTES_PATH, "r", encoding="utf-8") as f:
        routes = json.load(f)

    # Dedup by @id (Väylävirasto features don't have OSM ids, so this only
    # filters duplicates if we re-run with the same OSM ways)
    existing_ids = set()
    for f in routes.get("features", []):
        rid = (f.get("properties") or {}).get("@id")
        if rid:
            existing_ids.add(rid)

    added = 0
    for f in osm_gj["features"]:
        if f["properties"].get("@id") in existing_ids:
            continue
        # Mark provenance so the app can style/filter if needed
        f["properties"]["category"] = f["properties"].get("category") or "osm_road"
        routes["features"].append(f)
        added += 1

    with open(ROUTES_PATH, "w", encoding="utf-8") as f:
        json.dump(routes, f, ensure_ascii=False)
    print(f"  merged {added} OSM features into {ROUTES_PATH}")


def main():
    osm_json = fetch_overpass()
    n_ways = sum(1 for el in osm_json.get("elements", []) if el.get("type") == "way")
    print(f"  got {n_ways} ways")

    gj = to_geojson(osm_json)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False)
    size_mb = os.path.getsize(OUT_PATH) / 1e6
    print(f"  wrote {OUT_PATH} ({size_mb:.1f} MB, {len(gj['features'])} features)")

    if "--merge" in sys.argv:
        merge_into_routes(gj)


if __name__ == "__main__":
    main()
