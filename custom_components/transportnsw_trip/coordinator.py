"""Data coordinator for configured Transport NSW journeys."""

from __future__ import annotations

from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ARRIVE_BY,
    CONF_DESTINATION,
    CONF_DATE_TIME,
    CONF_JOURNEYS,
    CONF_JOURNEY_TYPE,
    CONF_MAX_RESULTS,
    CONF_MODES,
    CONF_NAME,
    CONF_ORIGIN,
    CONF_TIME,
    CONF_WEEKDAYS,
    DEFAULT_MAX_RESULTS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    JOURNEY_TYPE_FIXED_RECURRING,
    JOURNEY_TYPE_ONE_OFF,
    WEEKDAY_INDEX,
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
            date_time = _journey_date_time(journey)
            if date_time is None:
                data[name] = {
                    "best_option": None,
                    "next_option": None,
                    "options": [],
                    "last_updated": datetime.now().astimezone().isoformat(),
                    "status": "expired",
                }
                continue

            request = TripPlanRequest(
                origin=journey[CONF_ORIGIN],
                destination=journey[CONF_DESTINATION],
                date_time=date_time,
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


def _journey_date_time(journey: dict[str, Any]) -> datetime | None:
    """Resolve a stored journey schedule to the next query datetime."""
    journey_type = journey.get(CONF_JOURNEY_TYPE, JOURNEY_TYPE_FIXED_RECURRING)
    now = datetime.now().astimezone()

    if journey_type == JOURNEY_TYPE_ONE_OFF:
        date_time = datetime.fromisoformat(journey[CONF_DATE_TIME])
        if date_time.tzinfo is None:
            date_time = date_time.astimezone()
        if date_time < now:
            return None
        return date_time

    if journey_type == JOURNEY_TYPE_FIXED_RECURRING:
        return _next_recurring_datetime(journey, now)

    return None


def _next_recurring_datetime(journey: dict[str, Any], now: datetime) -> datetime | None:
    """Return the next matching weekday/time for a fixed recurring journey."""
    weekdays = journey.get(CONF_WEEKDAYS) or []
    weekday_indexes = {WEEKDAY_INDEX[weekday] for weekday in weekdays if weekday in WEEKDAY_INDEX}
    if not weekday_indexes:
        return None

    scheduled_time = time.fromisoformat(journey[CONF_TIME])
    for day_offset in range(8):
        candidate_date = now.date() + timedelta(days=day_offset)
        if candidate_date.weekday() not in weekday_indexes:
            continue
        candidate = datetime.combine(candidate_date, scheduled_time, tzinfo=now.tzinfo)
        if candidate >= now:
            return candidate
    return None
