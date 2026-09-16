# QTrace

**Quantum-Inspired Route Intelligence for Smart Urban Logistics.**

QTrace optimizes multi-stop routes for fleets and delivery operations using
quantum-inspired optimization (QPSO), real-world road routing, traffic
information, and geospatial intelligence. Originating from the [AICTE Smart
India Hackathon (SIH) 2026 — Quantum Technology Vertical, Problem Statement
1](docs/problem-statement.md) by Egreen Quanta, QTrace's production direction
is a FastAPI backend with an Android (Kotlin/Compose) client — see
[CLAUDE.md](CLAUDE.md) for the full architecture and engineering rules this
repository follows.

QTrace is not a Google Maps clone. Its purpose is logistics optimization:
multi-stop routing, fleet-aware optimization, congestion-aware decisions,
and operational intelligence.

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Optimization Approach](#optimization-approach)
- [Getting Started](#getting-started)
- [Documentation](#documentation)
- [License](#license)

## Architecture

```
Android App --HTTPS/JSON--> FastAPI Backend --> Optimization Service (QPSO, OR-Tools baseline)
                                             --> Routing Service --> RoutingProvider (OSRM / TomTom)
                                             --> Traffic Service
                                             --> PostgreSQL/PostGIS
                                             --> Redis + RQ workers (long-running optimization jobs)
```

Road-network routing (shortest paths, distance/time matrices) is delegated to
external providers (OSRM for development, TomTom for production) behind a
`RoutingProvider` abstraction — QTrace does not maintain its own city-graph
routing engine. QPSO and the OR-Tools baseline optimize **stop ordering and
vehicle assignment** (TSP/VRP/CVRP/CVRPTW) on top of the distance/time matrix
a provider returns.

Full details: [docs/architecture.md](docs/architecture.md)

## Tech Stack

| Layer | Choice |
|---|---|
| Android | Kotlin, Jetpack Compose, Material 3, MVVM/UDF, Retrofit, Room, MapLibre |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Optimization | QPSO (quantum-inspired), OR-Tools (classical baseline) |
| Routing | OSRM (development), TomTom (production traffic-aware routing) |
| Database | PostgreSQL + PostGIS |
| Background jobs | Redis + RQ |
| Auth/notifications/monitoring | Firebase Authentication, FCM, Crashlytics |

See [CLAUDE.md](CLAUDE.md) §3 for the complete, authoritative stack list and
constraints on changing it.

## Repository Structure

```
QTrace/
├── android/                      # Kotlin/Compose app - see android/README.md
│   └── app/src/main/kotlin/com/qtrace/app/{ui,domain,data,di}/
├── backend/                     # FastAPI service
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                 # settings/config
│   │   ├── models/                # SQLAlchemy domain models
│   │   ├── schemas/                # Pydantic I/O schemas
│   │   ├── routing/                # RoutingProvider abstraction + OSRMProvider
│   │   ├── geocoding/               # GeocodingProvider abstraction + TomTomGeocodingProvider
│   │   ├── optimization/            # QPSO stop-ordering solver
│   │   ├── services/, repositories/, traffic/, workers/, utils/
│   │   └── api/v1/                 # versioned endpoints
│   ├── tests/
│   ├── alembic/                    # migrations
│   ├── requirements.txt
│   └── Dockerfile
├── data/                         # sample/synthetic and real-world datasets
├── docs/                         # architecture, math formulation, problem statement
├── benchmarks/                   # optimization benchmarking scripts + results
├── notebooks/                    # exploratory analysis
├── scripts/                      # setup / data-gen / demo scripts
├── docker/                       # container/demo environment
├── CLAUDE.md                     # engineering rules and architecture source of truth
└── README.md
```

## Optimization Approach

QTrace's core is Quantum-Inspired Particle Swarm Optimization (QPSO) applied
to vehicle routing (TSP/VRP/CVRP/CVRPTW), with OR-Tools as a classical
baseline for comparison on identical inputs, constraints, and objective
function (see [CLAUDE.md](CLAUDE.md) §8-§9). QPSO is a quantum-inspired
*classical* algorithm — it does not run on quantum hardware.

## Getting Started

Backend (development):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values; never commit .env
uvicorn app.main:app --reload
```

Run tests:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

`GET /health` is available once the app is running. Route planning:
`POST /api/v1/routes` (road route, optionally through `stops`), `POST
/api/v1/optimization/jobs` / `GET /api/v1/optimization/jobs/{id}` (route +
QPSO stop-order optimization for 2+ stops), `GET
/api/v1/geocoding/search?query=...` (place search). Multi-vehicle fleet
routing: `POST /api/v1/fleet/routes` (depot + fleet + destinations in, one
optimized route per vehicle out — see
[docs/qisa-roadmap.md](docs/qisa-roadmap.md) for the current per-vehicle
algorithm and the planned future optimizer). Routing defaults to the
public OSRM demo server (no setup required); geocoding defaults to TomTom
(requires `TOMTOM_API_KEY`) or set `GEOCODING_PROVIDER=nominatim` for a
keyless alternative — see [docs/OSRM_INTEGRATION.md](docs/OSRM_INTEGRATION.md).

Android:

```bash
cd android
./gradlew :app:assembleDebug
```

See [android/README.md](android/README.md) for required `local.properties` values.

## Documentation

- [System Architecture](docs/architecture.md)
- [OSRM Routing Integration](docs/OSRM_INTEGRATION.md)
- [QISA Roadmap (future multi-vehicle optimizer)](docs/qisa-roadmap.md)
- [Mathematical Formulation](docs/math-formulation.md)
- [Original Problem Statement (hackathon source)](docs/problem-statement.md)
- [Demonstration Plan](docs/demonstration.md)
- [Engineering rules (CLAUDE.md)](CLAUDE.md)

## License

TBD.
