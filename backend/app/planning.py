"""Pure hypothetical planning. No database or mutation helpers are imported here."""

from copy import deepcopy
from decimal import Decimal, ROUND_DOWN
from typing import Annotated
from pydantic import Field, model_validator
from app.models import Model, ID
from app.geo import valid_coordinates, distance_km

Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class ScenarioDemand(Model):
    resource_id: ID
    quantity: Quantity
    region: Annotated[str, Field(min_length=1, max_length=100)]
    priority: Annotated[int, Field(ge=1, le=5)] = 3


class Scenario(Model):
    name: Annotated[str, Field(min_length=3, max_length=150)]
    disaster_type: Annotated[
        str, Field(pattern="^(FLOOD|EARTHQUAKE|CYCLONE|LANDSLIDE|FIRE|DROUGHT|TSUNAMI|OTHER)$")
    ]
    region: Annotated[str, Field(min_length=1, max_length=100)]
    district: Annotated[str, Field(max_length=100)] = ""
    population: Annotated[int, Field(ge=0, le=100000000)]
    severity: Annotated[str, Field(pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")]
    description: Annotated[str, Field(max_length=2000)] = ""
    latitude: Annotated[float, Field(ge=-90, le=90)] | None = None
    longitude: Annotated[float, Field(ge=-180, le=180)] | None = None
    disaster_id: ID | None = None
    accommodation_required: Annotated[int, Field(ge=0, le=100000000)]
    reserve_percent: Annotated[int, Field(ge=0, le=100)] = 20
    demands: Annotated[list[ScenarioDemand], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Provide both coordinates or neither")
        if self.accommodation_required > self.population:
            raise ValueError("Accommodation requirement cannot exceed estimated population")
        return self


def quantity(value):
    return Decimal(str(value))


def compare_plans(scenario, snapshot):
    """Each plan starts from the exact same snapshot; demand rows compete by resource ID."""
    resources = {r["resource_id"]: r for r in snapshot["resources"]}
    if any(d.resource_id not in resources for d in scenario.demands):
        raise ValueError("A selected resource no longer exists")
    warnings = [
        "HYPOTHETICAL SCENARIO - NOT A LIVE INCIDENT. No inventory or records were changed.",
        "Resource inventory has no warehouse coordinates. Plan A uses priority then input order; it does not claim nearest resource delivery.",
        "Demands are manager-entered assumptions. Population does not imply a consumption rate.",
        "Available stock already excludes live allocations; commitments are shown separately, never subtracted twice.",
        "Plans are heuristics, not optimal routing or dispatch decisions. Snapshot stock may change.",
        "An official disaster reference is context only. Existing commitments are reflected in available stock; entered demands represent this exercise, not automatically imported live requests.",
    ]
    plans = []
    for code, title in [
        ("A", "Nearest eligible / explicit fallback"),
        ("B", "Highest unmet demand first"),
        ("C", "Preserve reserve"),
    ]:
        available = {
            key: max(Decimal(0), quantity(r["available_quantity"])) for key, r in resources.items()
        }
        baseline = available.copy()
        reserve = {
            key: (value * Decimal(scenario.reserve_percent) / 100).quantize(
                Decimal("0.01"), rounding=ROUND_DOWN
            )
            if code == "C"
            else Decimal(0)
            for key, value in available.items()
        }
        ordered = list(enumerate(scenario.demands))
        if code == "B":
            ordered.sort(
                key=lambda pair: (
                    pair[1].resource_id,
                    -pair[1].quantity,
                    -pair[1].priority,
                    pair[0],
                )
            )
        else:
            ordered.sort(key=lambda pair: (-pair[1].priority, pair[0]))
        rows = []
        for index, demand in ordered:
            resource = resources[demand.resource_id]
            stock = max(Decimal(0), available[demand.resource_id] - reserve[demand.resource_id])
            proposed = min(stock, demand.quantity)
            available[demand.resource_id] -= proposed
            rows.append(
                {
                    "demand_index": index + 1,
                    "region": demand.region,
                    "priority": demand.priority,
                    "resource_id": demand.resource_id,
                    "resource_name": resource["resource_name"],
                    "unit": resource["unit"],
                    "required": str(demand.quantity),
                    "proposed": str(proposed),
                    "unmet": str(demand.quantity - proposed),
                    "coverage_percent": round(float(proposed / demand.quantity * 100), 2),
                }
            )
        totals = []
        for key in sorted({d.resource_id for d in scenario.demands}):
            required = sum(
                (d.quantity for d in scenario.demands if d.resource_id == key), Decimal(0)
            )
            proposed = baseline[key] - available[key]
            totals.append(
                {
                    "resource_id": key,
                    "resource_name": resources[key]["resource_name"],
                    "unit": resources[key]["unit"],
                    "required": str(required),
                    "available": str(baseline[key]),
                    "proposed": str(proposed),
                    "remaining": str(available[key]),
                    "reserve": str(reserve[key]),
                    "unmet": str(required - proposed),
                    "coverage_percent": round(float(proposed / required * 100), 2),
                }
            )
        plans.append(
            {
                "code": code,
                "title": title,
                "rows": rows,
                "resources": totals,
                "fully_covered_requests": sum(quantity(r["unmet"]) == 0 for r in rows),
                "partially_covered_requests": sum(
                    0 < quantity(r["proposed"]) < quantity(r["required"]) for r in rows
                ),
                "unallocated_requests": sum(quantity(r["proposed"]) == 0 for r in rows),
            }
        )
    shelters = []
    located = valid_coordinates(scenario.latitude, scenario.longitude)
    for raw in snapshot["shelters"]:
        if raw["status"] != "AVAILABLE" or raw["capacity"] <= raw["current_occupancy"]:
            continue
        row = deepcopy(raw)
        row["available_capacity"] = row["capacity"] - row["current_occupancy"]
        row["distance_km"] = (
            round(
                distance_km(
                    scenario.latitude, scenario.longitude, row["latitude"], row["longitude"]
                ),
                2,
            )
            if located and valid_coordinates(row.get("latitude"), row.get("longitude"))
            else None
        )
        shelters.append(row)
    shelters.sort(key=lambda r: (r["distance_km"] is None, r["distance_km"] or 0, r["shelter_id"]))
    eligible = sum(r["available_capacity"] for r in shelters)
    if not located or any(r["distance_km"] is None for r in shelters):
        warnings.append(
            "Some shelter distances are unavailable. Unlocated candidates remain visible; capacity across all regions is an upper bound, not guaranteed local accommodation."
        )
    return {
        "scenario": scenario.model_dump(mode="json"),
        "snapshot": deepcopy(snapshot),
        "plans": plans,
        "shelters": {
            "items": shelters,
            "eligible_capacity": eligible,
            "required": scenario.accommodation_required,
            "gap": max(0, scenario.accommodation_required - eligible),
            "distance_method": "Straight-line Haversine, not road travel; all regions included",
        },
        "warnings": warnings,
    }
