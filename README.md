# ARIA — Adversary Reconnaissance & Infrastructure Analysis

Single-file military intelligence web app for **North Karelia AO** (Finland).
Combines authority data, OSM, and the Physarum slime-mould algorithm to produce
a High Payoff Target (HPT) list, network-criticality analysis, and demolition
impact projections.

## Running locally

```bash
python3 -m http.server 7890 --directory .
```

Open <http://localhost:7890/aria.html>.

## Files

| File | Purpose |
|---|---|
| `aria.html` | Main app. Single-file Leaflet + Physarum + UI. All data embedded. |
| `aria_authority_bridges.json` | 268 Väylävirasto Siltarekisteri bridges in AO |
| `aria_comms_towers.json` | 187 strategic comms masts (OSM, ≥80 m or named) |
| `aria_civilian.json` | 451 civilian assets (schools, eldercare, fuel) |
| `aria_population_grid.json` | 11,493 Tilastokeskus 2023 1 km population cells |
| `aria_hpt_export.geojson` | Exportable HPT list — share with teammates |
| `aria_routes.geojson` | Väylävirasto road / rail / waterway data in WGS84 |
| `build_ao_routes.py` | ETRS-TM35FIN → WGS84 conversion + AO filtering |

## Key features

- **Hybrid HPT analysis** — validated strategic targets + algorithm-discovered chokepoints
- **Physarum slime-mould** flow simulation on the 4 600-edge road graph
- **Algorithm-discovered HPTs** — vulnerable bridges, isolated comms, supply lifelines
- **Demolition impact modal** — AI-templated cascade/casualty/recovery projection per target
- **Real population grid** — Tilastokeskus 2023, 229 614 residents
- **Authority validation** — every bridge cross-checked against Väylä Siltarekisteri
- **Clickable MSR routes** — see exactly which roads the algorithm classified

## Data sources

- **Väylävirasto Open Data** (Siltarekisteri, road/rail/waterway WFS)
- **Tilastokeskus** (1 km population grid 2023)
- **OpenStreetMap** via Overpass API (telecom masts, civilian infra)
- **Finnish Meteorological Institute** (weather, satellite gaps — currently unused)
