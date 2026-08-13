"""Services for Transport NSW Trip Planner."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DEFAULT_MAX_RESULTS, DOMAIN, SERVICE_PLAN_TRIP
from .tfnsw_client import (
    TransportNSWAuthError,
    TransportNSWError,
    TransportNSWRateLimitError,
    TripPlanRequest,
)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("origin"): cv.string,
        vol.Required("destination"): cv.string,
        vol.Optional("depart_by"): cv.datetime,
        vol.Optional("arrive_by"): cv.datetime,
        vol.Optional("modes"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("max_results", default=DEFAULT_MAX_RESULTS): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=10)
        ),
        vol.Optional("include_raw_payload", default=False): cv.boolean,
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_PLAN_TRIP):
        return

    async def async_plan_trip(call: ServiceCall) -> ServiceResponse:
        return await _async_handle_plan_trip(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAN_TRIP,
        async_plan_trip,
        schema=SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Unload integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_PLAN_TRIP):
        hass.services.async_remove(DOMAIN, SERVICE_PLAN_TRIP)


async def _async_handle_plan_trip(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Handle plan_trip service calls."""
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        raise HomeAssistantError("Transport NSW Trip Planner is not configured")

    depart_by = call.data.get("depart_by")
    arrive_by = call.data.get("arrive_by")
    if bool(depart_by) == bool(arrive_by):
        raise ServiceValidationError("Specify exactly one of depart_by or arrive_by")

    date_time = _as_datetime(arrive_by or depart_by)
    first_entry = next(iter(entries.values()))
    client = first_entry["client"]
    request = TripPlanRequest(
        origin=call.data["origin"],
        destination=call.data["destination"],
        date_time=date_time,
        arrive_by=arrive_by is not None,
        modes=call.data.get("modes"),
        max_results=call.data["max_results"],
        include_raw_payload=call.data["include_raw_payload"],
    )

    try:
        return await client.async_plan_trip(request)
    except TransportNSWAuthError as err:
        raise HomeAssistantError("TfNSW API authentication failed") from err
    except TransportNSWRateLimitError as err:
        raise HomeAssistantError("TfNSW API rate limit exceeded") from err
    except TransportNSWError as err:
        raise HomeAssistantError(str(err)) from err


def _as_datetime(value: datetime) -> datetime:
    """Return an aware datetime in the local timezone."""
    if value.tzinfo is None:
        return value.astimezone()
    return value

