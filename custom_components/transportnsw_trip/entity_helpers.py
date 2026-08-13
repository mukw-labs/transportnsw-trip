"""Entity helper functions for Transport NSW Trip Planner."""

from __future__ import annotations

from .const import CONF_JOURNEYS, CONF_NAME

SENSOR_KEYS = ("best_delay", "best_departure")
BINARY_SENSOR_KEYS = ("disrupted",)


def journey_unique_id(entry_id: str, journey_name: str, key: str) -> str:
    """Return the unique ID for a journey entity."""
    return f"{entry_id}_{journey_name}_{key}"


def desired_unique_ids(entry_id: str, journeys: list[dict]) -> set[str]:
    """Return all unique IDs expected for the configured journeys."""
    ids: set[str] = set()
    for journey in journeys:
        journey_name = journey[CONF_NAME]
        ids.update(journey_unique_id(entry_id, journey_name, key) for key in SENSOR_KEYS)
        ids.update(journey_unique_id(entry_id, journey_name, key) for key in BINARY_SENSOR_KEYS)
    return ids

