# System Architecture

## Component Overview

```mermaid
flowchart LR
    subgraph Client
        AND[Android App<br/>Kotlin + Compose]
    end

    AND -- HTTPS/JSON --> API

    subgraph Backend["FastAPI Backend (backend/app)"]
        API[API Layer<br/>app/api] --> SVC[Services<br/>app/services]
        SVC --> ROUTING[RoutingProvider<br/>app/routing]
        SVC --> GEO[GeocodingProvider<br/>app/geocoding]
        SVC --> OPT[Optimization Service<br/>app/optimization]
        SVC --> REPO[Repositories<br/>app/repositories]
        OPT --> QPSO[QPSO Engine]
        OPT --> ORTOOLS[OR-Tools Baseline]
        SVC --> WORKERS[RQ Workers<br/>app/workers]
    end

    ROUTING --> OSRM[OSRM<br/>development]
    ROUTING --> TOMTOM_ROUTE[TomTom Routing<br/>production, traffic-aware]
    GEO --> TOMTOM_SEARCH[TomTom Search<br/>geocoding]
    REPO --> DB[(PostgreSQL / PostGIS)]
    WORKERS --> REDIS[(Redis Queue)]
```

## Layers

1. **Client layer** (`android/`) — Kotlin/Compose app; contains no API secrets, talks to the backend over HTTPS/JSON only.
2. **API layer** (`backend/app/api`) — versioned FastAPI routers; input validation, predictable response shapes, no leaked internals.
3. **Service layer** (`backend/app/services`) — business logic; orchestrates routing, optimization, and persistence. UI/API code never implements optimization or routing logic directly (CLAUDE.md §6.2).
4. **Routing layer** (`backend/app/routing`) — `RoutingProvider` abstraction (`route`, `matrix`) with `OSRMProvider` (development) and a future `TomTomProvider` (production, traffic-aware). Provider-specific logic stays inside this layer only (CLAUDE.md §6.3).
5. **Geocoding layer** (`backend/app/geocoding`) — separate `GeocodingProvider` abstraction (OSRM has no address-search endpoint), with `TomTomGeocodingProvider` calling TomTom Search. Requires `TOMTOM_API_KEY`; raises a structured configuration error rather than silently degrading if it's missing (CLAUDE.md §34).
6. **Optimization layer** (`backend/app/optimization`) — a QPSO stop-ordering solver (`qpso.py`, random-key encoding over intermediate stops) plus a planned OR-Tools classical baseline, operating on the distance/time matrix a `RoutingProvider` returns. For a plain origin→destination request there is only one possible order, so the optimization service reports `algorithm="DIRECT_ROUTE"` honestly instead of invoking QPSO on a problem with nothing to search (CLAUDE.md §15, §67).
7. **Persistence layer** (`backend/app/models`, `backend/app/repositories`) — SQLAlchemy models for the domain entities (User, Vehicle, Depot, DeliveryStop, Route, OptimizationJob, TrafficSnapshot) backed by PostgreSQL/PostGIS, with Alembic migrations.
8. **Background jobs** (`backend/app/workers`) — Redis + RQ workers for long-running optimization jobs; not yet wired up since the current origin→destination feature resolves synchronously (CLAUDE.md §15, §25, §31 - don't add infrastructure before it's needed).

## Why routing is delegated, not built in-house

An earlier version of this document (and the original hackathon framing)
proposed a custom weighted-graph engine with in-house Dijkstra/A* shortest
paths, benchmarked against GA/ACO/PSO. The production architecture in
[CLAUDE.md](../CLAUDE.md) instead delegates all road-network routing to
external providers (OSRM/TomTom) via the `RoutingProvider` interface, and
scopes QPSO/OR-Tools to the VRP-style stop-ordering problem on top of the
resulting distance/time matrix. This avoids maintaining a bespoke routing
engine and keeps QTrace's optimization core focused on fleet/route
intelligence rather than road-graph shortest-path computation.

## RoutingProvider Contract

- **`route(coordinates) -> RouteResult`** — road-network route through an ordered list of coordinates: distance, duration, geometry.
- **`matrix(coordinates) -> MatrixResult`** — full pairwise distance/duration matrix, the primary input to the optimization layer.
- **`geocode(address) -> Coordinate`** — declared on the interface for future providers that support it, but `OSRMProvider` explicitly raises `NotImplementedError`: OSRM has no address-search endpoint. Real geocoding goes through the separate `GeocodingProvider` interface (`TomTomGeocodingProvider`).

Coordinate ordering is `(latitude, longitude)` everywhere in QTrace's own
schemas; providers with a different convention (OSRM uses `lon,lat`) convert
at their own boundary only (CLAUDE.md §39).
