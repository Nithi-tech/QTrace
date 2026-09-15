# Problem Statement (Source)

**Event:** AICTE Smart India Hackathon (SIH) 2026 — Quantum Technology Vertical
**Organization:** Egreen Quanta
**Problem Statement 1:** Quantum-Inspired Intelligent Traffic Route Optimization in Transportation Systems Using Metaheuristic Optimization

## Background

Modern urban transportation networks face persistent challenges of traffic congestion, inefficient route planning, and high operational costs. Classical optimization techniques struggle with large-scale Vehicle Routing Problems (VRP) because of their NP-hard nature. While quantum computers offer theoretical advantages for combinatorial optimization, current hardware limitations prevent their direct large-scale use. Quantum-inspired metaheuristic algorithms (e.g., Quantum Particle Swarm Optimization - QPSO) embed quantum-mechanical concepts into classical computation, delivering stronger global search, faster convergence, and a better balance between exploration and exploitation.

## Problem Description

Develop a quantum-inspired metaheuristic optimization framework that dynamically generates near-optimal vehicle routes under real-time or simulated traffic conditions. The transportation network will be modelled as a weighted graph. The framework will focus on algorithms such as Quantum Particle Swarm Optimization (QPSO) and will be benchmarked against conventional metaheuristics and exact methods.

## Objectives

1. Design a quantum-inspired metaheuristic framework capable of solving large-scale VRP and shortest-path problems.
2. Minimize total travel time, distance, and traffic congestion.
3. Reduce computational complexity while improving convergence speed and solution quality compared with classical algorithms.
4. Demonstrate scalability for smart-city logistics and intelligent transportation systems.

## Expected Solution

A complete software platform that implements a Quantum-Inspired Metaheuristic Optimization Algorithm for intelligent traffic routing. The platform must include graph-based network modelling, mathematical formulation of the optimization problem, constraint handling, convergence analysis, and systematic performance benchmarking.

## Expected Deliverables

| # | Deliverable | Description | Key Components / Metrics |
|---|---|---|---|
| 1 | Graph-based Network Model | Representation of the transportation network as a weighted directed/undirected graph | Nodes (intersections/depots), Edges (roads with travel time/distance/congestion weights), Dynamic weight update mechanism |
| 2 | Mathematical Formulation | Complete optimization model of the VRP / traffic routing problem | Objective function (min travel time), Capacity, time-window and flow constraints, Decision variables |
| 3 | Quantum-Inspired Algorithm Module | Core optimization engine | QPSO or equivalent quantum-inspired metaheuristic, Encoding of routes/particles, Quantum rotation / update rules |
| 4 | Software Platform / Prototype | Executable system | User interface or API, Input of network data & traffic conditions, Output of optimized routes, Visualization of routes on map/graph |
| 5 | Demonstration | Complete technical and real or simulated large-scale scenario | Algorithm description, Implementation details, Experimental results, at least one realistic urban network (or synthetic large instance) showing near-optimal routes under varying traffic conditions |

*Source: `SIH26137.pdf` (Egreen Quanta, SIH 2026 Quantum Technology Vertical).*
