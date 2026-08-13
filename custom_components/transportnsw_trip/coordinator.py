"""Data coordinator for configured Transport NSW journeys."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ARRIVE_BY,
    CONF_DESTINATION,
    CONF_JOURNEYS,
    CONF_MAX_RESULTS,
    CONF_MODES,
    CONF_NAME,
    CONF_OFFSET_MINUTES,
    CONF_ORIGIN,
    DEFAULT_MAX_RESULTS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .tfnsw_client import TransportNSWClient, TransportNSWError, TripPlanRequest

LOGGER = logging.getLogger(__name__)


class TransportNSWTripCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for configured journey updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: TransportNSWClient) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.client = client
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=_entry_update_interval(entry),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all configured journeys."""
        journeys = self.entry.options.get(CONF_JOURNEYS, [])
        data: dict[str, Any] = {}

        for journey in journeys:
            name = journey[CONF_NAME]
            request = TripPlanRequest(
                origin=journey[CONF_ORIGIN],
                destination=journey[CONF_DESTINATION],
                date_time=datetime.now().astimezone()
                + timedelta(minutes=journey.get(CONF_OFFSET_MINUTES, 0)),
                arrive_by=journey.get(CONF_ARRIVE_BY, False),
                modes=journey.get(CONF_MODES),
                max_results=journey.get(CONF_MAX_RESULTS, DEFAULT_MAX_RESULTS),
            )
            try:
                data[name] = await self.client.async_plan_trip(request)
            except TransportNSWError as err:
                raise UpdateFailed(str(err)) from err

        return data


def _entry_update_interval(entry: ConfigEntry) -> timedelta:
    seconds = entry.options.get("update_interval")
    if seconds is None:
        return DEFAULT_UPDATE_INTERVAL
    return timedelta(seconds=int(seconds))
