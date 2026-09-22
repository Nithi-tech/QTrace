package com.qtrace.app.domain.model

/** Mirrors backend/app/schemas/fleet.py::OptimizationObjective. */
enum class OptimizationObjective(val displayName: String) {
    BALANCED("Balanced"),
    MIN_TIME("Minimum Travel Time"),
    MIN_DISTANCE("Minimum Distance"),
    MIN_COST("Minimum Cost"),
}
