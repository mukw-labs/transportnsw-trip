"""Entity helper functions for Transport NSW Trip Planner."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import CONF_JOURNEYS, CONF_NAME, DOMAIN

SENSOR_KEYS = ("best_delay", "best_departure")
BINARY_SENSOR_KEYS = ("disrupted",)


def journey_device_identifier(entry_id: str, journey_name: str) -> str:
    """Return the device identifier for a configured journey."""
    return f"{entry_id}_{journey_name}"


def journey_device_info(entry: ConfigEntry, journey: dict[str, Any]) -> DeviceInfo:
    """Return device info for a configured journey."""
    journey_name = journey[CONF_NAME]
    return DeviceInfo(
        configuration_url="https://transportnsw.info/trip",
        identifiers={(DOMAIN, journey_device_identifier(entry.entry_id, journey_name))},
        manufacturer="Transport for NSW",
        model="Configured Trip",
        name=journey_name,
    )


def journey_unique_id(entry_id: str, journey_name: str, key: str) -> str:
    """Return the unique ID for a journey entity."""
    return f"{entry_id}_{journey_name}_{key}"


def journey_suggested_object_id(journey_name: str, key: str) -> str:
    """Return the suggested object ID for a journey entity."""
    return f"{journey_name}_{key}"


def desired_device_identifiers(entry_id: str, journeys: list[dict]) -> set[tuple[str, str]]:
    """Return all device identifiers expected for the configured journeys."""
    return {
        (DOMAIN, journey_device_identifier(entry_id, journey[CONF_NAME]))
        for journey in journeys
    }


def desired_unique_ids(entry_id: str, journeys: list[dict]) -> set[str]:
    """Return all unique IDs expected for the configured journeys."""
    ids: set[str] = set()
    for journey in journeys:
        journey_name = journey[CONF_NAME]
        ids.update(journey_unique_id(entry_id, journey_name, key) for key in SENSOR_KEYS)
        ids.update(journey_unique_id(entry_id, journey_name, key) for key in BINARY_SENSOR_KEYS)
    return ids
