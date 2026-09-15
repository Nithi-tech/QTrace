# QTrace

**Quantum-Inspired Intelligent Traffic Route Optimization** for transportation systems, built for **AICTE Smart India Hackathon (SIH) 2026 — Quantum Technology Vertical**, Problem Statement 1 by [Egreen Quanta](https://www.egreenquanta.com/).

QTrace models a city's road network as a weighted graph and solves large-scale Vehicle Routing / shortest-path problems with a **Quantum Particle Swarm Optimization (QPSO)** engine, benchmarked against classical exact methods and other metaheuristics (GA, ACO, PSO, Dijkstra/A*).

## Table of Contents

- [Problem Statement](#problem-statement)
- [Objectives](#objectives)
- [Expected Deliverables](#expected-deliverables)
- [Proposed Solution](#proposed-solution)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Project Plan / Roadmap](#project-plan--roadmap)
- [Evaluation Methodology](#evaluation-methodology)
- [Getting Started](#getting-started)
- [Documentation](#documentation)
- [License](#license)

## Problem Statement

Modern urban transportation networks face persistent traffic congestion, inefficient route planning, and high operational costs. Classical optimization struggles with large-scale Vehicle Routing Problems (VRP) due to their NP-hard nature. QTrace uses a **quantum-inspired metaheuristic** (QPSO) — embedding quantum-mechanical concepts into classical computation — to get stronger global search, faster convergence, and a better exploration/exploitation balance, without requiring actual quantum hardware.

Full source text: [docs/problem-statement.md](docs/problem-statement.md)

## Objectives

1. Design a quantum-inspired metaheuristic framework capable of solving large-scale VRP and shortest-path problems.
2. Minimize total travel time, distance, and traffic congestion.
3. Reduce computational complexity while improving convergence speed and solution quality vs. classical algorithms.
4. Demonstrate scalability for smart-city logistics and intelligent transportation systems.

## Expected Deliverables

| # | Deliverable | Mapped to |
|---|---|---|
| 1 | Graph-based Network Model | [src/graph/](src/graph/README.md) |
| 2 | Mathematical Formulation | [docs/math-formulation.md](docs/math-formulation.md) |
| 3 | Quantum-Inspired Algorithm Module (QPSO) | [src/optimization/qpso/](src/optimization/qpso/README.md), baselines in [src/optimization/baselines/](src/optimization/baselines/README.md) |
| 4 | Software Platform / Prototype | [src/api/](src/api/README.md) + [src/visualization/](src/visualization/README.md) |
| 5 | Demonstration | [docs/demonstration.md](docs/demonstration.md), [benchmarks/](benchmarks/results/README.md) |

Full deliverables table with metrics: [docs/problem-statement.md#expected-deliverables](docs/problem-statement.md#expected-deliverables)

## Proposed Solution

A common **solver interface** lets QPSO and every baseline (Dijkstra/A*, GA, ACO, classical PSO, small-instance exact VRP) run against the same graph, objective function, and constraint set, so results are directly comparable.

See the full architecture diagram and layer breakdown: [docs/architecture.md](docs/architecture.md)

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Core algorithms | Python 3.11+ (NumPy) | QPSO + baselines, easiest to benchmark/plot in |
| Graph modeling | NetworkX / osmnx | osmnx for real OpenStreetMap network import |
| API | FastAPI | Simple typed endpoints for route requests |
| Visualization | React + Leaflet/deck.gl, or Plotly Dash | Map overlay of routes + convergence charts |
| Benchmarking | pandas, matplotlib/plotly | Metrics tables and comparison charts |
| Packaging | Docker / docker-compose | Reproducible demo environment |
| Testing | pytest | Unit + integration tests |

*Final choices may be adjusted once the team is finalized — see [Getting Started](#getting-started).*

## Repository Structure

```
QTrace/
├── docs/                        # problem statement, architecture, formulation, demo plan
├── data/
│   ├── synthetic/                # generated benchmark graphs
│   └── real_world/               # OSM-derived urban networks
├── src/
│   ├── graph/                    # network modeling + dynamic weights
│   ├── optimization/
│   │   ├── qpso/                 # core QPSO engine
│   │   └── baselines/            # Dijkstra/A*, GA, ACO, classical PSO
│   ├── api/                      # backend service
│   ├── visualization/            # map/graph dashboard
│   └── utils/                    # shared helpers
├── benchmarks/
│   ├── scripts/                  # automated benchmark runners
│   └── results/                  # collected metrics + charts
├── notebooks/                    # exploratory analysis
├── tests/                        # unit/integration tests
├── scripts/                      # setup / data-gen / demo-run scripts
└── docker/                       # containerized demo environment
```

Each folder above has its own short `README.md` describing its purpose and current status.

## Project Plan / Roadmap

| Phase | Focus | Key Outputs | Maps to Deliverable |
|---|---|---|---|
| 0. Kickoff & Literature Review | Study QPSO/VRP literature, finalize scope & tech stack | Reference list, scope doc | — |
| 1. Graph & Data Layer | Build graph model, synthetic generator, OSM importer, dynamic weight updates | [src/graph](src/graph/README.md), [data/](data/synthetic/README.md) | #1 |
| 2. Mathematical Formulation | Define objective function, constraints (capacity, time-window, flow), decision variables | [docs/math-formulation.md](docs/math-formulation.md) | #2 |
| 3. QPSO Core Engine | Implement particle/route encoding, quantum update rules, constraint handling, convergence tracking | [src/optimization/qpso](src/optimization/qpso/README.md) | #3 |
| 4. Baseline Algorithms | Implement Dijkstra/A*, GA, ACO, classical PSO behind the same solver interface | [src/optimization/baselines](src/optimization/baselines/README.md) | #3 |
| 5. Software Platform | Build API + visualization dashboard (input network/traffic, output routes, map rendering) | [src/api](src/api/README.md), [src/visualization](src/visualization/README.md) | #4 |
| 6. Benchmarking & Convergence Analysis | Run systematic sweeps across instance sizes; collect solution quality, runtime, convergence speed | [benchmarks/](benchmarks/scripts/README.md) | #2, #3 |
| 7. Demonstration & Final Report | Realistic/large-scale demo scenario, technical write-up, results packaging | [docs/demonstration.md](docs/demonstration.md) | #5 |

> Timeline (weeks) to be filled in once the hackathon schedule and team availability are confirmed — phases 1–2 and 3–4 can run in parallel.

## Evaluation Methodology

Benchmarks compare QPSO against baselines on the same instances, measuring:

- **Solution quality** — total cost vs. best-known/exact (gap %).
- **Convergence speed** — iterations and wall-clock time to reach a target quality.
- **Scalability** — behavior as node/edge/vehicle counts grow (synthetic large instances).
- **Robustness** — solution quality under changing/dynamic traffic weights.

Details: [docs/math-formulation.md#benchmarks-to-compare-against](docs/math-formulation.md#benchmarks-to-compare-against)

## Getting Started

> Project is at the planning/scaffold stage — implementation has not started yet. This section will be filled in with setup/run instructions as each module lands (tracked per phase above).

## Documentation

- [Problem Statement (full)](docs/problem-statement.md)
- [System Architecture](docs/architecture.md)
- [Mathematical Formulation](docs/math-formulation.md)
- [Demonstration Plan](docs/demonstration.md)

## License

TBD.
