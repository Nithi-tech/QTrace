# QTrace Crowd-Traffic Architecture

## 1. Why commercial traffic APIs were removed

An earlier iteration of this integration used HERE Traffic API v7. It was replaced
before reaching production use, at the project's explicit request, with a
provider-agnostic architecture built around QTrace's own anonymized GPS telemetry.
The core route-optimization feature must not require a paid commercial traffic API key
to function.

**Audit of what existed before this change** (verified directly against the repo, not
assumed): no commercial traffic provider was active in the codebase at the time -
TomTom is used only for geocoding (`app/geocoding/tomtom_provider.py`), never for
routing or traffic; OSRM (`app/routing/osrm_provider.py`) already handled all routing.
There was nothing to "remove" from an active traffic pipeline; this document describes
what was *built*, not what was torn out.

## 2. Limitations of OpenStreetMap for live traffic

OpenStreetMap itself is a static map of road geometry and tags (including, where
tagged, `maxspeed`) - it has no live traffic layer. OSRM, built on OSM data, reports a
**routing-profile speed** per edge (the `speed` annotation - verified live against the
public OSRM demo server), which reflects the profile's assumed travel speed for that
road class, not current conditions. Neither OSM nor OSRM tells you how fast traffic is
moving *right now*. That is what this system exists to add.

## 3. QTrace crowd-traffic architecture

```
Android (future work - not implemented in this pass)
        │ POST /api/v1/traffic/observations (batch, one continuous trace)
        ▼
TrafficTelemetryService (app/traffic/service.py)
        │
        ├─→ validation (plausible speed, usable GPS accuracy)
        │
        ├─→ OSRMProvider.match_trace() (app/routing/map_matching.py)  ← ONE call/batch
        │        real OSM node-pair edges + OSRM's profile speed per edge
        │
        ├─→ TrafficRepository: upsert TrafficSegment, insert TrafficObservation
        │
        ├─→ recompute TrafficSnapshot (median speed, reference speed, congestion,
        │        confidence, freshness) per touched segment
        │
        └─→ update TrafficHistoricalProfile (day-of-week/time-bucket baseline)


GET /api/v1/optimization/jobs                     GET /api/v1/traffic/segments
        │                                                   │
        ▼                                                   ▼
TrafficMatrixService (app/traffic/matrix_service.py)   normalized TrafficSegmentSummary
        │  (a DB read - no external API call)              list, freshness recomputed
        ├─→ bounding box over the request's stops               at read time
        ├─→ TrafficRepository.get_snapshots_in_bbox()
        ├─→ app/traffic/matcher.py: straight-line corridor
        │        intersection per stop-pair (Shapely)
        └─→ confidence-weighted traffic matrix
                        │
                        ▼
        app/optimization/fitness.py: blended with OSRM's
        distance/duration matrix (DISTANCE_WEIGHT/TIME_WEIGHT/TRAFFIC_WEIGHT)
                        │
                        ▼
                QPSOSolver.optimize()  ← unchanged; still just a generic cost matrix
                        │
                        ▼
                OSRM route() on the optimized order → final geometry → MapLibre
```

## 4. GPS collection (Android - not yet implemented)

**This pass is backend-first, by explicit scope decision.** The ingestion endpoint,
validation, map-matching, aggregation, and QPSO integration are complete and tested
end-to-end with synthetic observations. The Android side (location permission request,
consent toggle, foreground-only sampling while a route is active, batching, upload) is
a separate follow-up against an already-complete, already-tested API contract - see
"Known limitations" below.

When built, it must collect only: latitude, longitude, timestamp, speed, heading,
horizontal accuracy - never identity, never in the background, never without explicit
opt-in (see "Privacy" below).

## 5. Map matching

`app/routing/map_matching.py` defines `RoadMatchingProvider` (`match_trace`,
`snap_point`), implemented by `OSRMProvider` (which also implements `RoutingProvider` -
two separate interfaces on one class, so plain routing's existing test doubles across
the codebase were never touched). Real OSM node IDs and per-edge routing-profile speeds
come from OSRM's Match API (`/match/v1/{profile}/...`, `annotations=true`), verified
live against `router.project-osrm.org` during development. A segment is the
order-independent pair of OSM nodes an edge runs between
(`MatchedEdge.segment_key`) - both travel directions share one segment, a documented
simplification.

**Documented simplification**: segment geometry is the whole matched trace's polyline,
not sliced per micro-edge (OSRM's response doesn't reliably expose that without the
much larger `steps=true` response). Every edge's node IDs and per-edge speed are still
exact, real, matched values - only the stored *shape* used for later spatial matching
is coarser than the true edge.

## 6. Aggregation

For each segment, `app/traffic/service.py` uses the two bounding observations' own
*reported* `speed_mps` (averaged) as the primary signal - a phone's GPS speed reading
is generally more reliable than back-computing speed from two position fixes, though
OSRM's matched distance/duration is also captured (`MatchedLeg`) as a cross-check.
`app/traffic/aggregation.py::median_speed_mps` computes the segment's current speed as
the **median** (not mean) of recent observations - robust to one outlier vehicle.

## 7. Traffic scoring

```
speed_ratio      = clamp(current_speed / reference_speed, 0, 1)
congestion_score = 1 - speed_ratio      # 0 = free-flowing, 1 = stopped
```

`reference_speed` is not congestion by itself - it's the "expected" baseline this
segment's current speed is compared against. See §9.

## 8. Confidence

```
count_factor      = clamp(observation_count / (TRAFFIC_MIN_OBSERVATIONS * 3), 0, 1)
freshness_factor  = 1.0 (LIVE) | 0.7 (RECENT) | 0.3 (STALE) | 0.0 (EXPIRED/UNKNOWN)
confidence        = count_factor * freshness_factor
```

Multiplied, not averaged: either too few observations *or* stale data should pull
confidence down, not get diluted by the other being good
(`app/traffic/aggregation.py::compute_confidence`). At optimization time,
`TrafficMatrixService` bakes `congestion_score * confidence` directly into each matrix
cell (the "effective traffic weight" the spec calls for) - `app/optimization/fitness.py`
stays a generic blender with no confidence-specific logic of its own.

## 9. Freshness

```
age <= TRAFFIC_LIVE_TTL_SECONDS     (120s default)  -> LIVE
age <= TRAFFIC_RECENT_TTL_SECONDS   (300s default)  -> RECENT
age <= TRAFFIC_EXPIRED_SECONDS      (900s default)  -> STALE
age  > TRAFFIC_EXPIRED_SECONDS                       -> EXPIRED
no snapshot exists at all                            -> UNKNOWN (never reported as LOW)
```

`GET /api/v1/traffic/segments` recomputes this against the *current* time on every
read - a snapshot that was LIVE ten minutes ago and never updated since is not still
reported as LIVE just because that was the last value written.

## 10. Historical baseline

`TrafficHistoricalProfile` keys on `(segment_id, day_of_week, time_bucket_minutes)`
(default 15-minute buckets, UTC). Bucketed by the **observation's own GPS timestamp**,
not when the server happened to process it - a late-arriving or backfilled batch still
lands in the bucket it actually happened in.

`median_speed_mps` on this table is a **running-mean approximation**, not a true
rolling median - an exact rolling median would require keeping every raw sample
indefinitely, which `TRAFFIC_RAW_RETENTION_DAYS` explicitly prevents. Documented, not
hidden.

## 11. Reference-speed hierarchy

```
1. OSRM's routing-profile speed for the matched edge (real, per-edge; NOT independently
   verified as a raw OSM maxspeed tag - the public OSRM demo server doesn't expose a
   separate maxspeed annotation to check it against)
2. QTrace's own historical median for this segment/day/time-bucket
3. A single documented fallback constant (~30 km/h, DEFAULT_FALLBACK_REFERENCE_SPEED_MPS)
```

No road-class-specific tier is implemented: OSRM's match/route responses used here
don't reliably expose per-edge road class, and inventing one would mean guessing.
Honestly narrower than the original 4-tier design; not a road-class-baseline in
disguise.

## 12. Public traffic feed adapters

Not implemented in this pass. `TrafficProvider`-style abstraction principles from the
routing/geocoding modules (`app/routing/base.py`, `app/geocoding/base.py`) apply if
this is built later: a `PublicTrafficFeedProvider`, optional, off by default, scoped to
a specific verified region/license - never assumed to cover "everywhere."

## 13. QPSO integration

Exactly as before this rewrite: `app/optimization/qpso.py` was **not modified**. It
takes one generic `cost_matrix`; `app/optimization/fitness.py::build_cost_matrix`
normalizes distance/duration to `[0,1]` and blends them with the traffic matrix
(already `[0,1]` and confidence-weighted) using `DISTANCE_WEIGHT`/`TIME_WEIGHT`/
`TRAFFIC_WEIGHT`. `TrafficMatrixService` is queried exactly once per optimization
request (a DB read), never inside QPSO's fitness loop.

**Proof this isn't decorative**:
`tests/services/test_optimization_service.py::test_real_qtrace_traffic_snapshot_changes_which_order_qpso_picks`
seeds a real snapshot (via the real repository) showing heavy congestion on one
specific road, with distance/duration held exactly tied between two possible stop
orders, and asserts QPSO picks the order that avoids it - using the real
`TrafficRepository` + `TrafficMatrixService`, not a mock.

## 14. Privacy

- Collected (once Android telemetry exists): latitude, longitude, timestamp, speed,
  heading, GPS accuracy. Never name, phone number, contacts, messages, or any other
  identifying data (`TrafficObservationInput` has no such field, by design).
- `TrafficObservation` rows carry no user/device identifier at all - there is nothing
  in this schema tying an observation back to who submitted it.
- Ingestion is opt-in by design intent (Android consent UI is part of the deferred
  follow-up, §4); `TRAFFIC_TELEMETRY_INGESTION_ENABLED` lets an operator pause
  ingestion server-side without a deploy.

## 15. Data retention

```
TRAFFIC_RAW_RETENTION_DAYS      = 7   (raw TrafficObservation rows)
TRAFFIC_SNAPSHOT_RETENTION_DAYS = 30  (TrafficSnapshot rows once orphaned/expired)
```

`app/traffic/retention.py::purge_expired_traffic_data` deletes observations older than
the raw cutoff and snapshots older than the snapshot cutoff. Run via
`python -m app.traffic.retention` (cron) - not wired to a scheduled job queue yet since
none exists in this codebase (`app/workers/` is an empty stub); building a full RQ
integration for one cron-shaped task would be over-engineering for what's needed today.

## 16. Failure behavior

Every failure mode degrades to the same safe result - `traffic.available = false`,
route optimization completes using distance/time alone:

| Condition | Result |
|---|---|
| `TRAFFIC_ENABLED=false` | baseline matrix, `enabled=false` |
| No segments near the request's stops yet | baseline matrix, `available=false` |
| OSRM map-matching fails for a trace | ingestion reports 0 accepted, doesn't crash |
| A GPS observation is implausible (speed/accuracy) | rejected with a reason, batch continues |

## Environment variables

```env
TRAFFIC_ENABLED=true
TRAFFIC_TELEMETRY_INGESTION_ENABLED=true
TRAFFIC_LIVE_TTL_SECONDS=120.0
TRAFFIC_RECENT_TTL_SECONDS=300.0
TRAFFIC_EXPIRED_SECONDS=900.0
TRAFFIC_MIN_OBSERVATIONS=3
TRAFFIC_CORRIDOR_RADIUS_METERS=100.0
TRAFFIC_RAW_RETENTION_DAYS=7
TRAFFIC_SNAPSHOT_RETENTION_DAYS=30
TRAFFIC_MAX_BATCH_SIZE=500

DISTANCE_WEIGHT=0.4
TIME_WEIGHT=0.4
TRAFFIC_WEIGHT=0.2
```

## API endpoints

- `POST /api/v1/traffic/observations` - ingest one batch (one continuous trace).
- `GET /api/v1/traffic/segments?west=&south=&east=&north=` - normalized current state
  of every segment in a bounding box.

## Tests

```
tests/traffic/test_aggregation.py        - median, congestion score, freshness, confidence
tests/traffic/test_reference_speed.py    - reference-speed hierarchy
tests/traffic/test_historical.py         - day-of-week/time-bucket helpers
tests/traffic/test_matcher.py            - corridor/geometry matching
tests/traffic/test_matrix_service.py     - disabled/no-data/matched/stale paths
tests/traffic/test_ingestion_service.py  - validation, map-match failure, snapshot/
                                            historical-profile updates
tests/traffic/test_retention.py          - purge logic
tests/routing/test_osrm_map_matching.py  - OSRM /match and /nearest parsing (respx-mocked
                                            against shapes verified live)
tests/optimization/test_fitness.py       - cost-matrix normalization/weighting
tests/api/test_traffic_api.py            - ingestion/query endpoints
tests/services/test_optimization_service.py::test_real_qtrace_traffic_snapshot_changes_which_order_qpso_picks
                                          - end-to-end proof, real repository + matrix service
```

No test calls the real public OSRM server (CLAUDE.md #44) - `test_osrm_map_matching.py`
is `respx`-mocked against response shapes verified live during development.

## Known limitations

- **No Android telemetry collection yet** - explicit scope decision for this pass (see
  §4). The API contract it will call already exists and is tested.
- **No real device GPS data has been ingested** - every test uses synthetic
  observations. The pipeline's correctness is proven; its behavior under real-world GPS
  noise, multipath error in urban canyons, etc. is not yet observed.
- **Straight-line corridors, not true route-shape corridors**, for optimization-time
  segment matching (§13) - the same documented tradeoff as the earlier HERE-based
  design, now applied to QTrace's own data instead of a third party's.
- **No road-class reference-speed tier** (§11) - narrower than originally specced,
  because the data to support it honestly isn't available from this OSRM setup.
- **Running-mean historical baseline**, not a true rolling median (§10, §6 model
  docstring).
- **No global coverage claim, and none should ever be made**: QTrace only has traffic
  data where QTrace's own users have driven recently. Coverage is exactly as good as
  the app's own usage, nothing more - `traffic.available=false` is the honest default
  everywhere until real usage exists.
