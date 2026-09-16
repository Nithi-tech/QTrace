# OSRM Routing Integration

## What OSRM is

[OSRM](http://project-osrm.org/) (Open Source Routing Machine) is a road-network routing
engine built on [OpenStreetMap](https://www.openstreetmap.org/) data. QTrace uses it for
every road-network calculation: point-to-point routes, route geometry, and the
distance/duration matrices that feed the optimizer. QTrace does not maintain its own
city-graph routing engine (CLAUDE.md §11).

## Why QTrace uses it

QPSO and the OR-Tools baseline optimize **stop ordering and vehicle assignment**, not
road geometry. They need real road distances/times, not straight-line estimates, to
produce routes that are actually drivable and cost-realistic (CLAUDE.md §5, §11). OSRM
supplies that; QTrace's algorithms consume it.

## Architecture

```
Coordinates (from geocoding or direct input)
        │
        ▼
  OSRM Table API  ──────────────► distance matrix + duration matrix
        │                              │
        │                              ▼
        │                         QPSOSolver (in-process, no I/O)
        │                              │
        │                              ▼
        │                       optimized stop order
        │                              │
        ▼                              ▼
  OSRM Route API  ◄─────────── ordered coordinate list
        │
        ▼
  RouteResult (distance, duration, GeoJSON geometry)
```

**Rule: OSRM is never called from inside the QPSO fitness loop.** `OptimizationService.plan_route`
(`backend/app/services/optimization_service.py`) calls the routing provider exactly twice
for a multi-stop request: once for the table (`matrix()`), once for the final route
(`route()`), regardless of how many particles/iterations QPSO runs. `QPSOSolver.optimize`
(`backend/app/optimization/qpso.py`) only ever reads the in-memory matrix it's given — it
has no knowledge of HTTP, OSRM, or any provider.

## Provider abstraction

`RoutingProvider` (`backend/app/routing/base.py`) is the interface; `OSRMProvider`
(`backend/app/routing/osrm_provider.py`) is the only implementation. Coordinate ordering
is converted at this one boundary: QTrace uses `(latitude, longitude)` everywhere
internally and at the API; OSRM's HTTP API expects `longitude,latitude`
(`backend/app/schemas/routing.py`, `backend/app/routing/osrm_provider.py`). This
conversion is covered by `tests/routing/test_osrm_provider.py::test_route_converts_lat_lon_and_parses_result`.

## Development vs. production OSRM

| | Development (default) | Production |
|---|---|---|
| `OSRM_BASE_URL` | `https://router.project-osrm.org` (public demo instance) | Your own self-hosted OSRM server |
| Setup cost | None — no map data download required | Requires processing an OpenStreetMap extract |
| Guarantees | None — rate-limited, best-effort, not for production load | Whatever you provision |

The public demo server is free and requires no setup, which is why it's the default —
QTrace does not download or bundle map data. It is explicitly **not** a production
dependency (project policy: [openstreetmap.org/fixthemap#technical-usage](https://operations.osmfoundation.org/policies/tileusage/)-style
fair-use policies apply to OSRM's demo server too). To self-host:

1. Download an OpenStreetMap extract for your target region (e.g. from
   [Geofabrik](https://download.geofabrik.de/)).
2. Process it with the `osrm/osrm-backend` Docker image: `osrm-extract` → `osrm-partition`
   → `osrm-customize` (the MLD pipeline).
3. Serve it with `osrm-routed --algorithm mld <file>.osrm` and point `OSRM_BASE_URL` at it.

This is a deliberately deferred step (CLAUDE.md §46 - don't over-engineer the first
version); it does not require any application code changes since routing already goes
through the `RoutingProvider` abstraction.

## Route API

`OSRMProvider.route()` calls `/route/v1/{profile}/{coordinates}` with
`overview=full&geometries=geojson` and returns a normalized `RouteResult` (distance,
duration, GeoJSON `LineString` geometry) — raw OSRM JSON never leaves this module.

## Table API

`OSRMProvider.matrix()` calls `/table/v1/{profile}/{coordinates}` and returns a
normalized `MatrixResult` (`distances_meters`, `durations_seconds` as full pairwise
matrices). `OptimizationService` bounds the coordinate count sent here via
`MAX_ROUTE_STOPS` (default 25) before calling the provider, since neither the public
demo server nor a self-hosted instance guarantees unlimited table size
(CLAUDE.md §27) — exceeding it raises `TooManyStopsError` (`LOCATION_LIMIT_EXCEEDED`, HTTP 400).

## Geocoding

Two interchangeable `GeocodingProvider` implementations exist, selected by
`GEOCODING_PROVIDER`:

- **`tomtom`** (default) — `TomTomGeocodingProvider`, requires `TOMTOM_API_KEY`.
- **`nominatim`** — `NominatimProvider`, keyless, backed by OpenStreetMap data via the
  public Nominatim instance. Throttled to ~1 request/second per Nominatim's usage policy
  and sends a descriptive `User-Agent`, as required by that policy.

OSRM itself has no geocoding endpoint (`OSRMProvider.geocode()` raises
`NotImplementedError` by design) — geocoding is always a separate, explicitly configured
provider (CLAUDE.md §11).

## QPSO integration

`OptimizationService.plan_route` (`backend/app/services/optimization_service.py`):

- **0–1 intermediate stops**: only one possible visit order exists, so the route is
  requested directly. `algorithm="DIRECT_ROUTE"` — this is reported honestly rather than
  claiming an optimization ran when it didn't (CLAUDE.md §15).
- **2+ intermediate stops**: `matrix()` is called once on `[origin, *stops, destination]`;
  `QPSOSolver.optimize()` runs entirely against that in-memory duration matrix; the
  resulting order is used to reorder the intermediate stops; `route()` is called once more
  on the final ordered list to get real road geometry. `algorithm="QPSO"`.

`OptimizationRouteResult.stop_order` exposes the visit order as indices into the
request's `stops` list, so callers (including the Android app) know exactly which stop
was visited when, without needing to know anything about OSRM or QPSO internals.

## Scope not covered by this pass

Per CLAUDE.md §46/§8.2 ("implement the variant required by the current feature", "do not
over-engineer the first version"), the following exist in the target architecture but are
**not** implemented yet, and this integration does not add them:

- **Traffic-aware cost** (`app/traffic/` is an empty stub) — the objective function
  currently minimizes travel time from OSRM only.
- **Multi-vehicle VRP / capacity / time windows (CVRP/CVRPTW)** — `QPSOSolver` optimizes a
  single vehicle's stop order (a TSP-path variant); it does not yet partition stops across
  vehicles or enforce capacity/time-window constraints.
- **Caching** of geocoding/table results — every request currently calls the provider
  fresh. Recommended next step: a Redis-backed cache (Redis is already in the target
  stack for job queues), keyed on the sorted, rounded coordinate list + profile.
- **Background job execution** (`app/workers/` is an empty stub) — optimization currently
  runs synchronously within the request.

## Environment variables

```env
OSRM_BASE_URL=https://router.project-osrm.org
OSRM_PROFILE=driving

GEOCODING_PROVIDER=tomtom        # "tomtom" or "nominatim"
TOMTOM_API_KEY=
NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org

ROUTING_REQUEST_TIMEOUT_SECONDS=5.0
ROUTING_MAX_RETRIES=2
MAX_ROUTE_STOPS=25
```

## Error handling

All routing/geocoding failures are structured exceptions mapped to HTTP status codes in
`backend/app/main.py` — no stack traces ever reach the client:

| Code | HTTP | Cause |
|---|---|---|
| `INVALID_ROUTE_INPUT` | 400 | Malformed input (e.g. fewer than 2 coordinates) |
| `LOCATION_LIMIT_EXCEEDED` | 400 | Request has more locations than `MAX_ROUTE_STOPS` |
| `ROUTING_PROVIDER_TIMEOUT` | 504 | OSRM did not respond within `ROUTING_REQUEST_TIMEOUT_SECONDS`, after retries |
| `ROUTING_PROVIDER_UNAVAILABLE` | 502 | OSRM unreachable, or returned an error/no-route result |
| `GEOCODING_PROVIDER_NOT_CONFIGURED` | 503 | Required geocoding credential/config missing |
| `GEOCODING_PROVIDER_TIMEOUT` | 504 | Geocoding provider timed out, after retries |
| `GEOCODING_PROVIDER_UNAVAILABLE` | 502 | Geocoding provider unreachable or errored |

Timeouts trigger a bounded number of retries (`ROUTING_MAX_RETRIES`, default 2); a
non-2xx HTTP response from the provider is treated as non-transient and is not retried
(CLAUDE.md §45).

## Rate limits and licensing

- The public OSRM demo server and the public Nominatim instance are shared, free
  services with fair-use policies — not committed SLAs. Do not point automated/load
  tests at them; `respx`-mocked unit tests are used instead (CLAUDE.md §44).
- Data is © OpenStreetMap contributors, licensed [ODbL](https://opendatacommons.org/licenses/odbl/).
  MapLibre's default attribution control (used unmodified in the Android app) already
  surfaces this attribution on the map.

## Development setup

No setup is required beyond `backend/.env` (copy from `.env.example`) — the defaults
point at the public OSRM and Nominatim/TomTom services, so `POST /api/v1/routes` and
`POST /api/v1/optimization/jobs` work immediately after `pip install -r requirements.txt`.

## Troubleshooting

- **`ROUTING_PROVIDER_UNAVAILABLE` / `ROUTING_PROVIDER_TIMEOUT`**: check `OSRM_BASE_URL`
  is reachable (`curl "$OSRM_BASE_URL/route/v1/driving/13.388,52.517;13.397,52.529"` should
  return `"code":"Ok"`); the public demo server can be temporarily rate-limited under load.
- **`GEOCODING_PROVIDER_NOT_CONFIGURED`**: `GEOCODING_PROVIDER=tomtom` requires
  `TOMTOM_API_KEY` to be set; switch to `GEOCODING_PROVIDER=nominatim` for a keyless
  alternative.
- **`LOCATION_LIMIT_EXCEEDED`**: reduce the number of stops, or raise `MAX_ROUTE_STOPS`
  if your OSRM instance (self-hosted) can handle a larger table request.
