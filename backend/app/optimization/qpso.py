"""Quantum-inspired Particle Swarm Optimization for route stop-ordering (CLAUDE.md #9).

Scope: given a fixed origin (index 0) and destination (last index), find the
visit order of any intermediate stops that minimizes total route cost from a
precomputed distance/duration matrix. This is a TSP-path variant of VRP - the
building block CVRP/CVRPTW will extend later (CLAUDE.md #8.2).

With 0 or 1 intermediate stops there is only one possible order, so this
module reports that immediately without running particle iterations
(CLAUDE.md #15 - do not manufacture optimization activity that didn't happen).

Encoding: each particle is a vector of continuous "priority" keys, one per
intermediate stop; the visit order is the stops sorted by their priority
value (random-key encoding), which lets a continuous-domain QPSO update rule
operate on a discrete ordering problem.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class QPSOConfig:
    """All QPSO parameters are explicit and configurable (CLAUDE.md #9, #35 - no magic numbers)."""

    population_size: int = 30
    max_iterations: int = 100
    contraction_expansion_max: float = 1.0
    contraction_expansion_min: float = 0.5
    convergence_patience: int = 15
    """Stop early if global best hasn't improved for this many iterations."""
    seed: int | None = None
    """Fixed seed makes a run reproducible (CLAUDE.md #41, #52)."""


@dataclass
class QPSOResult:
    order: list[int]
    """Indices into the intermediate-stop list, in visit order."""
    total_cost: float
    iterations_run: int
    converged: bool
    cost_history: list[float] = field(default_factory=list)


def _route_cost(cost_matrix: list[list[float]], full_order: list[int]) -> float:
    return sum(cost_matrix[full_order[i]][full_order[i + 1]] for i in range(len(full_order) - 1))


def _decode(position: list[float]) -> list[int]:
    """Random-key decoding: sort intermediate-stop indices by their priority value."""
    return sorted(range(len(position)), key=lambda i: position[i])


class QPSOSolver:
    """Stop-ordering optimizer. See module docstring for scope and encoding."""

    def __init__(self, config: QPSOConfig | None = None) -> None:
        self._config = config or QPSOConfig()

    def optimize(self, cost_matrix: list[list[float]], num_intermediate_stops: int) -> QPSOResult:
        if num_intermediate_stops < 0:
            raise ValueError("num_intermediate_stops must be >= 0")

        destination_index = len(cost_matrix) - 1

        if num_intermediate_stops <= 1:
            # Only one possible visit order exists - nothing to search for.
            order = list(range(num_intermediate_stops))
            full_order = [0, *[i + 1 for i in order], destination_index]
            return QPSOResult(
                order=order,
                total_cost=_route_cost(cost_matrix, full_order),
                iterations_run=0,
                converged=True,
                cost_history=[],
            )

        return self._run_particle_swarm(cost_matrix, num_intermediate_stops, destination_index)

    def _run_particle_swarm(
        self, cost_matrix: list[list[float]], num_intermediate_stops: int, destination_index: int
    ) -> QPSOResult:
        cfg = self._config
        rng = random.Random(cfg.seed)

        def fitness(position: list[float]) -> float:
            order = _decode(position)
            full_order = [0, *[i + 1 for i in order], destination_index]
            return _route_cost(cost_matrix, full_order)

        particles = [
            [rng.random() for _ in range(num_intermediate_stops)] for _ in range(cfg.population_size)
        ]
        personal_best = [list(p) for p in particles]
        personal_best_fitness = [fitness(p) for p in particles]

        global_best_index = min(range(cfg.population_size), key=lambda i: personal_best_fitness[i])
        global_best = list(personal_best[global_best_index])
        global_best_fitness = personal_best_fitness[global_best_index]

        cost_history = [global_best_fitness]
        iterations_without_improvement = 0
        iterations_run = 0

        for iteration in range(cfg.max_iterations):
            iterations_run = iteration + 1
            # Contraction-expansion coefficient linearly decays exploration -> exploitation.
            progress = iteration / max(cfg.max_iterations - 1, 1)
            beta = cfg.contraction_expansion_max - progress * (
                cfg.contraction_expansion_max - cfg.contraction_expansion_min
            )

            mean_best = [
                sum(personal_best[p][d] for p in range(cfg.population_size)) / cfg.population_size
                for d in range(num_intermediate_stops)
            ]

            improved_this_iteration = False
            for p in range(cfg.population_size):
                for d in range(num_intermediate_stops):
                    phi = rng.random()
                    attractor = phi * personal_best[p][d] + (1 - phi) * global_best[d]
                    # Delta-potential-well update: u in (0, 1) avoids log(0).
                    u = max(rng.random(), 1e-9)
                    direction = 1.0 if rng.random() > 0.5 else -1.0
                    spread = abs(mean_best[d] - particles[p][d])
                    particles[p][d] = attractor + direction * beta * spread * math.log(1.0 / u)

                candidate_fitness = fitness(particles[p])
                if candidate_fitness < personal_best_fitness[p]:
                    personal_best[p] = list(particles[p])
                    personal_best_fitness[p] = candidate_fitness
                    if candidate_fitness < global_best_fitness:
                        global_best = list(particles[p])
                        global_best_fitness = candidate_fitness
                        improved_this_iteration = True

            cost_history.append(global_best_fitness)
            iterations_without_improvement = (
                0 if improved_this_iteration else iterations_without_improvement + 1
            )
            if iterations_without_improvement >= cfg.convergence_patience:
                break

        return QPSOResult(
            order=_decode(global_best),
            total_cost=global_best_fitness,
            iterations_run=iterations_run,
            converged=iterations_without_improvement >= cfg.convergence_patience,
            cost_history=cost_history,
        )
