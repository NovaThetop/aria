#!/usr/bin/env python3
"""
Convert Finnish authority route data (ETRS-TM35FIN → WGS84)
and produce aria_routes.geojson for ARIA drop-in.
Sources:
  - tiestotiedot_tieosoiteverkko.json  (Väylävirasto road network)
  - ratatiedot_locationtracks.json     (rail tracks)
  - vesivaylatiedot_vaylat_uusi.json   (waterways — for bridge context)
"""
import json, math, os

SRC = "/Users/petrpodlozny/Downloads/ccb8dd98-1937-401e-a857-5e29684551f8 (1)"
OUT = "/Users/petrpodlozny/aria_routes.geojson"

# ── ETRS-TM35FIN (EPSG:3067) → WGS84 ───────────────────────────
def tm35fin_to_wgs84(E, N):
    a   = 6378137.0
    f   = 1.0/298.257222101
    k0  = 0.9996
    E0  = 500000.0
    lon0 = math.radians(27.0)

    b    = a*(1-f)
    e2   = 2*f - f*f
    ep2  = e2/(1-e2)
    n    = f/(2-f)
    A0   = a*(1 - n + (5*n*n/4)*(1 - n) + (81*n**4/64))
    B0   = a*(3*n/2 - 27*n**3/32)*(1)
    C0   = a*(15*n*n/16)*(1 - n)
    D0   = a*(-35*n**3/48)
    E_c  = a*(315*n**4/512)

    x  = E - E0
    M  = N / k0
    mu = M / (a*(1 - e2/4 - 3*e2*e2/64 - 5*e2**3/256))

    e1  = (1 - math.sqrt(1-e2)) / (1 + math.sqrt(1-e2))
    phi1 = (mu
            + (3*e1/2 - 27*e1**3/32)*math.sin(2*mu)
            + (21*e1**2/16 - 55*e1**4/32)*math.sin(4*mu)
            + (151*e1**3/96)*math.sin(6*mu)
            + (1097*e1**4/512)*math.sin(8*mu))

    sin1 = math.sin(phi1)
    cos1 = math.cos(phi1)
    tan1 = math.tan(phi1)
    N1   = a / math.sqrt(1 - e2*sin1*sin1)
    T1   = tan1*tan1
    C1   = ep2*cos1*cos1
    R1   = a*(1-e2) / (1 - e2*sin1*sin1)**1.5
    D    = x / (N1*k0)

    lat = phi1 - (N1*tan1/R1)*(
        D*D/2
        - (5 + 3*T1 + 10*C1 - 4*C1*C1 - 9*ep2)*D**4/24
        + (61 + 90*T1 + 298*C1 + 45*T1*T1 - 252*ep2 - 3*C1*C1)*D**6/720)

    lon = lon0 + (
        D
        - (1 + 2*T1 + C1)*D**3/6
        + (5 - 2*C1 + 28*T1 - 3*C1*C1 + 8*ep2 + 24*T1*T1)*D**5/120
    ) / cos1

    return math.degrees(lat), math.degrees(lon)

# ── North Karelia AO bounds (ETRS-TM35FIN) ─────────────────────
# Lat 61.5–64.5N, Lon 27.0–31.5E → approx TM35FIN
AO_Y_MIN, AO_Y_MAX = 6830000, 7160000
AO_X_MIN, AO_X_MAX = 540000,  710000

def in_ao(coords):
    # coords may be [[x,y,z,m],...] or [[[x,y,z,m],...],...]
    c = coords[0]
    if isinstance(c[0], list):
        c = c[0]  # MultiLineString
    return AO_X_MIN <= c[0] <= AO_X_MAX and AO_Y_MIN <= c[1] <= AO_Y_MAX

def flatten_coords(coords):
    if coords and isinstance(coords[0][0], list):
        return [pt for ring in coords for pt in ring]
    return coords

def convert_line(coords):
    out = []
    flat = flatten_coords(coords)
    for c in flat:
        pt = c if not isinstance(c[0], list) else c[0]
        lat, lon = tm35fin_to_wgs84(float(pt[0]), float(pt[1]))
        out.append([round(lon,5), round(lat,5)])
    return out

# ── Route metadata ──────────────────────────────────────────────
ROAD_META = {
    6:  {"name":"E63 / Rd 6",  "role":"Main north–south artery. South Finland → Joensuu → Kajaani. Primary MSR for the AO.",         "type":"MSR",  "color":"#ff2200"},
    9:  {"name":"E75 / Rd 9",  "role":"Main east–west corridor. Joensuu → Kuopio → Tampere. Primary MSR westbound.",                  "type":"MSR",  "color":"#ff2200"},
    23: {"name":"Rd 23",       "role":"Transverse supply route. Joensuu → Varkaus → central Finland. ASR westbound.",                 "type":"ASR",  "color":"#ff8800"},
    73: {"name":"Rd 73",       "role":"Primary supply route north to Lieksa and border zone. Only paved road for most of this axis.", "type":"ASR",  "color":"#ff8800"},
    74: {"name":"Rd 74",       "role":"Eastern border route Joensuu → Ilomantsi. Only paved road into the Ilomantsi salient.",        "type":"ASR",  "color":"#ff8800"},
    75: {"name":"Rd 75",       "role":"Northern supply corridor Nurmes → Kajaani. Connects the northern AO to Kajaani hub.",          "type":"TAC",  "color":"#ffff00"},
    71: {"name":"Rd 71",       "role":"Southern approach Savonlinna → Joensuu. Secondary reinforcement route from south.",            "type":"TAC",  "color":"#ffff00"},
    5:  {"name":"Rd 5 / E63",  "role":"E63 southern section, links AO to Helsinki. Strategic reinforcement corridor.",               "type":"MSR",  "color":"#ff2200"},
}

features = []

# ── ROADS ───────────────────────────────────────────────────────
print("Processing roads...")
with open(f"{SRC}/tiestotiedot_tieosoiteverkko.json") as f:
    roads = json.load(f)

road_count = 0
for feat in roads["features"]:
    tie = feat["properties"].get("tie")
    if tie not in ROAD_META:
        continue
    coords = feat["geometry"]["coordinates"]
    if not in_ao(coords):
        continue
    meta = ROAD_META[tie]
    wgs_coords = convert_line(coords)
    if len(wgs_coords) < 2:
        continue
    features.append({
        "type": "Feature",
        "properties": {
            "source":      "Väylävirasto tieosoiteverkko",
            "category":    "supply_route",
            "road_number": tie,
            "name":        meta["name"],
            "role":        meta["role"],
            "route_type":  meta["type"],
            "color":       meta["color"],
            "highway":     "trunk" if tie in (6,9,5) else "primary",
            "ref":         str(tie),
        },
        "geometry": {"type":"LineString", "coordinates": wgs_coords}
    })
    road_count += 1

print(f"  → {road_count} road segments")

# ── RAIL ────────────────────────────────────────────────────────
print("Processing rail tracks...")
with open(f"{SRC}/ratatiedot_locationtracks.json") as f:
    rail = json.load(f)

# Finnish rail route numbers for North Karelia
# Route 8 = Savo line (Helsinki-Joensuu-Kajaani), Route 15 = Karjala line
RAIL_ROUTES = {
    "008": {"name":"Savo Line",   "role":"Main rail artery: Helsinki → Joensuu → Kajaani. Strategic heavy logistics — armour, fuel, ammunition."},
    "015": {"name":"Karjala Line","role":"Karjala rail line: Joensuu → Imatra/Lappeenranta. Connects AO southward."},
    "011": {"name":"Pohjois-Karjala line","role":"Joensuu → Nurmes northern rail corridor. Supplies forward northern positions."},
    "014": {"name":"Savonlinna line","role":"Joensuu → Savonlinna. Secondary east–west connection."},
}

rail_count = 0
for feat in rail["features"]:
    if feat["geometry"] is None:
        continue
    props = feat["properties"]
    route = props.get("route_name","")
    coords = feat["geometry"]["coordinates"]
    if not in_ao(coords):
        continue
    # Only main lines (not sidings/yard tracks)
    track_type = props.get("type","")
    if track_type not in ("pääraide","liikennepaikkaväliraide") and "pääraide" not in track_type:
        # Include if it's on a key route even if siding
        if route not in RAIL_ROUTES:
            continue
    meta = RAIL_ROUTES.get(route, {"name":f"Rail route {route}", "role":"Rail supply corridor."})
    wgs_coords = convert_line(coords)
    if len(wgs_coords) < 2:
        continue
    features.append({
        "type": "Feature",
        "properties": {
            "source":     "Väylävirasto ratatiedot",
            "category":   "railway",
            "route":      route,
            "name":       meta["name"],
            "role":       meta["role"],
            "track_name": props.get("name",""),
            "track_type": track_type,
            "length_m":   round(props.get("length",0)),
            "railway":    "rail",
            "color":      "#00aaff",
        },
        "geometry": {"type":"LineString", "coordinates": wgs_coords}
    })
    rail_count += 1

print(f"  → {rail_count} rail segments")

# ── WATERWAYS (for bridge-over-river context) ───────────────────
print("Processing waterways...")
with open(f"{SRC}/vesivaylatiedot_vaylat_uusi.json") as f:
    water = json.load(f)

water_count = 0
for feat in water["features"]:
    if feat["geometry"] is None:
        continue
    coords = feat["geometry"]["coordinates"]
    if not in_ao(coords):
        continue
    props = feat["properties"]
    wgs_coords = convert_line(coords)
    if len(wgs_coords) < 2:
        continue
    name = props.get("nimifi","") or props.get("nimisv","") or "Waterway"
    cls  = props.get("vaylaluokkafi","")
    features.append({
        "type": "Feature",
        "properties": {
            "source":   "Väylävirasto vesivaylat",
            "category": "waterway",
            "name":     name,
            "class":    cls,
            "waterway": "navigable",
            "color":    "#0066cc",
        },
        "geometry": {"type":"LineString", "coordinates": wgs_coords}
    })
    water_count += 1

print(f"  → {water_count} waterway segments")

# ── OUTPUT ──────────────────────────────────────────────────────
fc = {
    "type": "FeatureCollection",
    "name": "ARIA AO Routes — North Karelia (Väylävirasto)",
    "description": "Road supply routes (E63/E75/Rd73/74/75), rail lines, and navigable waterways. Finnish authority data, converted from ETRS-TM35FIN.",
    "features": features
}

with open(OUT, "w") as f:
    json.dump(fc, f, ensure_ascii=False)

size_mb = os.path.getsize(OUT)/1024/1024
print(f"\nDone → {OUT}")
print(f"Total features: {len(features)} ({size_mb:.1f} MB)")
print(f"  Roads: {road_count}  Rail: {rail_count}  Waterways: {water_count}")
