package com.qtrace.app.domain.model

/** Mirrors backend/app/schemas/fleet.py::ScenarioType. Controls which inputs the fleet
 * planning flow shows (spec section 5 - scenario-specific inputs). */
enum class ScenarioType(val displayName: String, val exampleText: String) {
    PASSENGER_TRANSPORT("Passenger Transport", "College Bus, School Bus, Employee Shuttle"),
    PACKAGE_DELIVERY("Package Delivery", "E-commerce, Courier, Amazon-style delivery"),
    GOODS_LOGISTICS("Goods / Logistics", "Warehouse -> Stores, Distribution"),
}
