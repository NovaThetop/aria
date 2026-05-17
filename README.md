# ARIA — Adversary Reconnaissance & Infrastructure Analysis

A single-file web app that maps the **North Karelia AO** (Finland) using the
**Physarum polycephalum** slime-mold algorithm (Tero et al., *Science* 2010)
to find supply-network chokepoints the way nature finds them — by flow,
not by inspection.

**What it does**

- Discovers the AO's flow backbone via Physarum from 600+ key terrain nodes
- Ranks a hybrid High Payoff Target list — validated strategic targets +
  algorithm-discovered vulnerable bridges, supply lifelines, isolated comms
- Cross-validates every bridge against the Väylä Siltarekisteri
  (268 authority records)
- Runs a destruction simulation: pick two independent route pairs, click a
  midpoint ring, watch the slime-mold regrow around the 400 m blast
- Generates an LLM-templated demolition-impact modal per target
- Overlays 1 km population grid, civilian infra, comms masts, rail/waterways

## Running locally

```bash
python3 -m http.server 7890 --directory .
```

Open <http://localhost:7890/aria.html>.

No build step, no install, no dependencies — Leaflet is loaded from a CDN.
The whole app is one HTML file with embedded data and an OSM augmentation
file loaded at startup.

## How it works

The Physarum implementation follows Tero 2010:

1. Build a road graph from Väylävirasto + OSM (≈ 4,600 edges in the AO).
2. Inject pressure at key terrain / strategic asset nodes weighted by type.
3. Solve the Kirchhoff pressure system on the graph Laplacian with
   conjugate gradient (`physarumStep`).
4. Compute flux Q = D · Δp / L on each edge.
5. Adapt conductance: `D += 0.1 · (Q^1.8 / (1 + Q^1.8) − D)`.
6. Iterate; weak edges decay to 0, strong edges thicken into the tube.

For two-route destruction simulation, the slime-mold runs in path mode
(only start + end as food sources, multi-start with shortest-total-length
scoring), and destroyed midpoint rings apply a **400 m blast radius** so a
single destroyed segment can't be bypassed by a 50 m parallel OSM way.

## File layout

| File | Purpose |
|---|---|
| `aria.html` | Main app. Single-file Leaflet + Physarum + UI. |
| `aria_routes.geojson` | Väylävirasto state road / rail / waterway network |
| `aria_osm_roads.geojson` | OSM regional roads (tertiary/unclassified/etc.) |
| `aria_authority_bridges.json` | 268 Väylä Siltarekisteri bridges in AO |
| `aria_comms_towers.json` | 187 strategic comms masts |
| `aria_civilian.json` | 451 civilian assets (schools, eldercare, fuel) |
| `aria_population_grid.json` | 11,493 Tilastokeskus 2023 1 km cells |
| `aria_hpt_export.geojson` | Exportable HPT list — share with teammates |
| `build_ao_routes.py` | ETRS-TM35FIN → WGS84 conversion + AO filtering |
| `fetch_osm_roads.py` | Overpass API fetcher for OSM regional roads |

## Data sources

All data is open. Attribution required when redistributing.

- [**Väylävirasto Open Data**](https://vayla.fi/en/transport-network/data/open-data)
  (Creative Commons BY 4.0) — Tieosoiteverkko, Siltarekisteri, Ratatiedot, Vesiväylätiedot
- [**Tilastokeskus 1 km Population Grid 2023**](https://www.stat.fi/tup/ruututietokanta/index_en.html)
  (Creative Commons BY 4.0)
- [**OpenStreetMap via Overpass API**](https://overpass-api.de/)
  (Open Database License 1.0)
- [**Tero et al. 2010**](https://www.science.org/doi/10.1126/science.1177894) —
  *Rules for Biologically Inspired Adaptive Network Design*, Science 327:439–442
- [**Finnish Meteorological Institute Open Data**](https://en.ilmatieteenlaitos.fi/open-data)
  — weather/satellite (seasonal-analysis hook)

## License

[MIT](LICENSE) for the code. Data remains under each publisher's original
licence (see `LICENSE` for details).
