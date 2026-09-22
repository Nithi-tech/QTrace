# Real-Time Traffic Intelligence

## What this is

QTrace resolves traffic for a stop through a three-tier fallback hierarchy and blends
the result into the same cost matrix QPSO already searches (`docs/OSRM_INTEGRATION.md`).
No tier is ever queried from inside QPSO's fitness/particle-update loop, and no traffic
data is ever fabricated (CLAUDE.md §12, §43, §68).

## Fallback hierarchy

```
TomTom live flow  ──fresh & valid?──► use it (status LIVE)
       │ no / unconfigured / provider error
       ▼
QTrace crowd telemetry ──fresh & valid?──► use it (status LIVE/RECENT)
       │ no data, or stale past TRAFFIC_EXPIRED_SECONDS
       ▼
Historical baseline (day-of-week × time-bucket) ──enough samples?──► use it (status HISTORICAL)
       │ no
       ▼
UNAVAILABLE — reported honestly, never guessed
```

This is `TrafficService.resolve()` (`backend/app/traffic/traffic_service.py`), called
once per **unique stop coordinate** (never per stop-pair, never per QPSO
particle/iteration) by `TrafficMatrixService.get_traffic_matrix()`
(`backend/app/traffic/matrix_service.py`), which resolves every stop concurrently via
`asyncio.gather`.

Freshness is re-checked at **read time**, never trusted from a stored label — a crowd
snapshot stored as `LIVE` two hours ago is re-classified against the current time before
use and correctly falls through to the historical tier if it's gone stale
(`tests/traffic/test_traffic_service.py::test_stale_crowd_snapshot_is_rejected_in_favor_of_historical`).

## Providers

### TomTom (`backend/app/traffic/tomtom_provider.py`)

Reuses the existing `TOMTOM_API_KEY` (already used for geocoding,
`docs/OSRM_INTEGRATION.md`) — there is no second TomTom credential or client.

- **Flow** (`GET .../traffic/services/4/flowSegmentData/absolute/10/json`) is
  **point-based**, not area-based — verified live during development. There is no "give
  me every segment in this box" endpoint in TomTom's plain-JSON API (only a far more
  complex protobuf vector-tile API), so QTrace queries flow once per unique stop
  coordinate rather than sweeping a bounding box. This is also more precise: it asks for
  traffic exactly where a stop is, not an area average.
- **Incidents** (`GET .../traffic/services/5/incidentDetails`) genuinely is bbox-based
  and is queried that way — once per request, over a box covering all of that request's
  stops (`app/traffic/matcher.py::build_bounding_box`).
- Speed unit conversion (TomTom returns km/h) happens once, at this provider boundary
  (CLAUDE.md §39). A 401/403 is never retried (it will not resolve itself); other
  failures retry up to `TRAFFIC_MAX_RETRIES` times.
- If `TOMTOM_API_KEY` is unset, `get_tomtom_traffic_provider()` (`backend/app/api/deps.py`)
  returns `None` and the fallback hierarchy proceeds straight to the QTrace crowd tier —
  this is not an error condition.

### QTrace crowd telemetry (`backend/app/traffic/telemetry_service.py`)

QTrace's own source of live traffic, built from opted-in Android clients' GPS samples —
no third-party traffic subscription required for this tier to work.

1. `POST /api/v1/traffic/observations` accepts a batch of raw `(lat, lon, speed_mps,
   accuracy_m, timestamp)` samples.
2. Samples failing sanity checks are rejected, never silently dropped without a reason:
   implausible speed (> `MAX_PLAUSIBLE_SPEED_MPS`, 55 m/s ≈ 198 km/h), poor GPS accuracy
   (> `MAX_USABLE_ACCURACY_M`, 100 m), a timestamp more than 5 minutes in the future, or
   more than a day in the past.
3. The valid trace is map-matched to real OSM road edges via
   `OSRMProvider.match_trace()` (`/match/v1/{profile}/...`) — the same OSRM instance used
   for routing, not a duplicate integration.
4. Each matched edge becomes/updates a `TrafficSegment` row keyed by its OSM node pair;
   an observation is stored per edge per trace leg.
5. The segment's current `TrafficSnapshot` (median speed, congestion score, freshness
   status, confidence) and its historical profile (bucketed by day-of-week ×
   `TRAFFIC_MIN_OBSERVATIONS`-gated 15-minute window) are recomputed from recent
   observations — bucketed by each observation's own GPS timestamp, not ingestion
   wall-clock time, so a late-arriving or backfilled batch lands in the bucket it
   actually happened in.

### Historical baseline (`backend/app/traffic/historical.py`, `reference_speed.py`)

A running mean of QTrace-crowd-observed speed per segment, per day-of-week, per
15-minute bucket (`TrafficHistoricalProfile`). Only used once a segment has accumulated
at least `TRAFFIC_MIN_OBSERVATIONS` samples in that bucket, and its confidence is always
discounted relative to a live reading (`_HISTORICAL_CONFIDENCE_FACTOR = 0.5` in
`traffic_service.py`) — a documented QTrace engineering choice, not a claimed statistical
calibration.

## Combining into one matrix

`TrafficMatrixService.get_traffic_matrix()` builds one `N × N` matrix per request:

- **Congestion cell** `(i, j)`: the confidence-weighted average of stop `i` and stop
  `j`'s resolved congestion scores.
- **Incident cell** `(i, j)`: the worst incident (by severity, or 1.0 for a closure)
  whose geometry intersects the straight-line corridor between stops `i` and `j`
  (`app/traffic/matcher.py`) — a documented simplification (the real route may curve),
  the same tradeoff already made to avoid an OSRM call per stop-pair.
- **Final cell** = `max(congestion, incident) × confidence` — **max, not sum**: an
  incident on an already-congested road is not "more than maximally bad" for routing
  purposes (`tests/traffic/test_matrix_service.py::test_incident_on_corridor_can_override_low_congestion`).

`app/optimization/fitness.py::build_cost_matrix` then blends this traffic matrix with
min-max-normalized distance and duration into the single cost matrix `QPSOSolver`
actually searches:

```
cost[i][j] = DISTANCE_WEIGHT · norm(distance[i][j])
           + TIME_WEIGHT     · norm(duration[i][j])
           + TRAFFIC_WEIGHT  · traffic[i][j]      (already in [0, 1], used as-is)
```

`QPSOSolver` (`backend/app/optimization/qpso.py`) is **unmodified** — it only ever sees
a generic `cost_matrix` and has no knowledge that traffic exists. Traffic genuinely
changes which order QPSO picks, not just the response's decoration: proven by
`tests/services/test_optimization_service.py::test_traffic_incident_flips_qpso_stop_order`,
which holds distances/durations fixed and shows a single real, geometry-matched road
closure flip QPSO's chosen visit order.

## What "changes the order" actually requires

Congestion cells are computed as a symmetric average of each stop's own score, so for
any fixed set of stops between a fixed origin/destination, the *sum* of congestion
across a full path's edges is the same regardless of visit order (every intermediate
stop is visited exactly once, with exactly two adjacent edges, whichever order it's
visited in). **Congestion alone cannot break a tie between orderings** — it can still
correctly report overall traffic level and `traffic_impact_seconds`, but ordering
changes come from **incidents**, since an incident's corridor match is genuinely
specific to *which pair* of stops are adjacent, not just which stops exist. This is a
real, deliberate property of this design, not an oversight — documented here so it
isn't rediscovered as a "bug" later.

## Freshness and confidence

| Status | Meaning | Threshold |
|---|---|---|
| `LIVE` | Age ≤ `TRAFFIC_LIVE_TTL_SECONDS` (default 120s) | freshest tier available |
| `RECENT` | Age ≤ `TRAFFIC_RECENT_TTL_SECONDS` (default 300s) | still usable |
| `STALE` / `EXPIRED` | Older than that, up to `TRAFFIC_EXPIRED_SECONDS` (900s) / beyond it | not used — falls through |
| `HISTORICAL` | No live/recent data; a sufficiently-sampled historical profile exists | discounted confidence |
| `UNAVAILABLE` | Nothing usable at any tier | reported as such, never guessed |

Every optimization response's `traffic` field (`TrafficStatus`) reports the *worst-tier,
lowest-confidence-honest* summary across all stop-pairs actually used
(`_STATUS_PRIORITY` / `_SOURCE_PRIORITY` in `matrix_service.py`) — never overstates
freshness by cherry-picking the best pair.

## Caching (not Redis)

TomTom flow/incident responses are cached in-process for `TRAFFIC_CACHE_TTL_SECONDS`
(`backend/app/traffic/cache.py::TTLCache`), keyed on the rounded `(lat, lon)`. No Redis
client exists anywhere in this codebase yet; adding one solely for this cache would be
new infrastructure this feature doesn't itself require (CLAUDE.md §31, §46). A
Redis-backed cache with the same interface is a documented, straightforward follow-up
once that infrastructure exists for another reason (e.g. job queues).

## Retention

`backend/app/traffic/retention.py::purge_expired_traffic_data` deletes raw observations
older than `TRAFFIC_RAW_RETENTION_DAYS` (default 7) and orphaned/expired snapshots older
than `TRAFFIC_SNAPSHOT_RETENTION_DAYS` (default 30). Historical profiles are never
purged — they are a small, bounded (segment × day-of-week × time-bucket) running
aggregate, not raw data that grows unbounded. This is a plain function, not a scheduled
job yet; wiring it to a periodic trigger (cron, or an RQ worker once that infrastructure
exists) is a deferred next step, not built in this pass.

## API endpoints

| Method & path | Purpose |
|---|---|
| `POST /api/v1/traffic/observations` | Crowd-telemetry ingestion (§ above) |
| `GET /api/v1/traffic/point?latitude=&longitude=` | Resolve traffic at one point through the full fallback hierarchy |
| `GET /api/v1/traffic/segments/{segment_id}` | QTrace's own crowd-telemetry view of one road segment |

No bbox-listing endpoint is provided: segment geometry is stored as opaque GeoJSON, not
PostGIS columns, so an efficient "every segment in this box" query isn't available
without a real schema change beyond this pass's scope (CLAUDE.md §31) — and nothing in
this codebase calls that shape of query today.

## Environment variables

```env
TRAFFIC_ENABLED=true
TRAFFIC_TELEMETRY_INGESTION_ENABLED=true

TRAFFIC_TIMEOUT_SECONDS=5.0
TRAFFIC_MAX_RETRIES=2
TRAFFIC_CACHE_TTL_SECONDS=60.0

TRAFFIC_LIVE_TTL_SECONDS=120.0
TRAFFIC_RECENT_TTL_SECONDS=300.0
TRAFFIC_EXPIRED_SECONDS=900.0

TRAFFIC_MIN_OBSERVATIONS=3
TRAFFIC_CORRIDOR_RADIUS_METERS=150.0

TRAFFIC_RAW_RETENTION_DAYS=7
TRAFFIC_SNAPSHOT_RETENTION_DAYS=30
TRAFFIC_MAX_BATCH_SIZE=500

# QPSO fitness weights - need not sum to 1; only relative magnitude matters to QPSO.
DISTANCE_WEIGHT=0.4
TIME_WEIGHT=0.4
TRAFFIC_WEIGHT=0.2
```

`TOMTOM_API_KEY` (already documented in `docs/OSRM_INTEGRATION.md`) is reused as-is.

## Scope not covered by this pass

- **Redis-backed caching** — see "Caching" above; in-process `TTLCache` only.
- **Scheduled retention** — `purge_expired_traffic_data` exists and is tested but is not
  wired to a scheduler/worker yet.
- **Android UI for traffic** — the backend returns `TrafficStatus`/
  `traffic_impact_seconds` on every optimization response; rendering it (route coloring,
  a "traffic: LIVE via TomTom" badge, etc.) is Android-side work not built in this pass.
- **Directional/edge-specific flow** — TomTom flow is resolved per-point, not per
  directed road edge, for the reasons in "Providers" above; see "What changes the order"
  above for what this does and doesn't allow traffic to influence.
