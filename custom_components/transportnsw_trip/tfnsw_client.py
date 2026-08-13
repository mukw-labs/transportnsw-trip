"""Async client for TfNSW Trip Planner APIs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import DEFAULT_MAX_RESULTS, MODE_MAP

BASE_TRIP_URL = "https://api.transport.nsw.gov.au/v1/tp/trip"


class TransportNSWError(Exception):
    """Base Transport NSW API error."""


class TransportNSWAuthError(TransportNSWError):
    """Transport NSW authentication error."""


class TransportNSWRateLimitError(TransportNSWError):
    """Transport NSW rate limit error."""


@dataclass(slots=True)
class TripPlanRequest:
    """A trip planning request."""

    origin: str
    destination: str
    date_time: datetime
    arrive_by: bool = False
    modes: list[str] | None = None
    max_results: int = DEFAULT_MAX_RESULTS
    include_raw_payload: bool = False


class TransportNSWClient:
    """Small async wrapper around the TfNSW Trip Planner endpoint."""

    def __init__(self, session: ClientSession, api_key: str) -> None:
        """Initialize the client."""
        self._session = session
        self._api_key = api_key

    async def async_plan_trip(self, request: TripPlanRequest) -> dict[str, Any]:
        """Fetch and normalize trip options."""
        raw = await self._async_get_trip(request)
        options = normalize_trip_response(raw, request.include_raw_payload)
        ranked = rank_options(options, request.arrive_by, request.date_time)

        return {
            "best_option": ranked[0] if ranked else None,
            "next_option": ranked[1] if len(ranked) > 1 else None,
            "options": ranked[: request.max_results],
            "last_updated": datetime.now().astimezone().isoformat(),
        }

    async def _async_get_trip(self, request: TripPlanRequest) -> dict[str, Any]:
        """Call the TfNSW trip endpoint."""
        params: dict[str, str] = {
            "outputFormat": "rapidJSON",
            "coordOutputFormat": "EPSG:4326",
            "depArrMacro": "arr" if request.arrive_by else "dep",
            "itdDate": request.date_time.strftime("%Y%m%d"),
            "itdTime": request.date_time.strftime("%H%M"),
            "type_origin": _location_type(request.origin),
            "name_origin": request.origin,
            "type_destination": _location_type(request.destination),
            "name_destination": request.destination,
            "TfNSWTR": "true",
            "calcNumberOfTrips": str(max(request.max_results, 2)),
        }

        excluded = _excluded_modes(request.modes)
        if excluded:
            params["excludedMeans"] = ",".join(excluded)

        headers = {
            "Accept": "application/json",
            "Authorization": f"apikey {self._api_key}",
        }

        try:
            async with self._session.get(BASE_TRIP_URL, params=params, headers=headers, timeout=10) as response:
                if response.status == 401:
                    raise TransportNSWAuthError("Invalid TfNSW API key")
                if response.status in (403, 429):
                    raise TransportNSWRateLimitError("TfNSW API rate limit exceeded")
                response.raise_for_status()
                return await response.json()
        except ClientResponseError as err:
            raise TransportNSWError(f"TfNSW API returned HTTP {err.status}") from err
        except ClientError as err:
            raise TransportNSWError(f"TfNSW API request failed: {err}") from err


def normalize_trip_response(raw: dict[str, Any], include_raw_payload: bool) -> list[dict[str, Any]]:
    """Normalize TfNSW journey payloads into stable trip options."""
    journeys = raw.get("journeys") or []
    return [
        option
        for journey in journeys
        if (option := _normalize_journey(journey, include_raw_payload)) is not None
    ]


def rank_options(
    options: list[dict[str, Any]], arrive_by: bool, target_time: datetime
) -> list[dict[str, Any]]:
    """Rank trip options and return the preferred order."""
    target_time = target_time.astimezone()
    future_or_feasible = [
        option
        for option in options
        if option["predicted_departure_dt"] >= datetime.now().astimezone()
    ]

    if arrive_by:
        candidates = [
            option
            for option in future_or_feasible
            if option["predicted_arrival_dt"] <= target_time
        ]
        return _strip_sort_fields(
            sorted(
                candidates,
                key=lambda option: (
                    -option["predicted_departure_dt"].timestamp(),
                    option["transfers"],
                    option["duration"],
                    max(option["lateness_minutes"], 0),
                ),
            )
        )

    return _strip_sort_fields(
        sorted(
            future_or_feasible,
            key=lambda option: (
                option["predicted_arrival_dt"],
                option["transfers"],
                option["duration"],
                max(option["lateness_minutes"], 0),
            ),
        )
    )


def _normalize_journey(journey: dict[str, Any], include_raw_payload: bool) -> dict[str, Any] | None:
    legs = journey.get("legs") or []
    transit_legs = [leg for leg in legs if leg.get("transportation")]
    if not legs:
        return None

    first = legs[0]
    last = legs[-1]
    scheduled_departure = _parse_time(first.get("departureTimePlanned"))
    predicted_departure = _parse_time(first.get("departureTimeEstimated")) or scheduled_departure
    scheduled_arrival = _parse_time(last.get("arrivalTimePlanned"))
    predicted_arrival = _parse_time(last.get("arrivalTimeEstimated")) or scheduled_arrival

    if not all((scheduled_departure, predicted_departure, scheduled_arrival, predicted_arrival)):
        return None

    route = _first_route(transit_legs)
    duration = int((predicted_arrival - predicted_departure).total_seconds())
    realtime_delay = int((predicted_departure - scheduled_departure).total_seconds())
    lateness_minutes = round((predicted_arrival - scheduled_arrival).total_seconds() / 60)

    normalized_legs = [_normalize_leg(leg) for leg in legs]
    journey_id = journey.get("id") or f"{predicted_departure.isoformat()}:{predicted_arrival.isoformat()}:{route}"

    option: dict[str, Any] = {
        "journey_id": journey_id,
        "route": route,
        "legs": normalized_legs,
        "departure_time": predicted_departure.isoformat(),
        "scheduled_departure_time": scheduled_departure.isoformat(),
        "arrival_time": predicted_arrival.isoformat(),
        "scheduled_arrival_time": scheduled_arrival.isoformat(),
        "duration": duration,
        "transfers": max(0, len(transit_legs) - 1),
        "realtime_delay": realtime_delay,
        "predicted_arrival": predicted_arrival.isoformat(),
        "lateness_minutes": lateness_minutes,
        "predicted_departure_dt": predicted_departure,
        "predicted_arrival_dt": predicted_arrival,
    }

    if include_raw_payload:
        option["raw_payload"] = journey

    return option


def _normalize_leg(leg: dict[str, Any]) -> dict[str, Any]:
    transportation = leg.get("transportation") or {}
    product = transportation.get("product") or {}
    return {
        "origin": _location_summary(leg.get("origin") or {}),
        "destination": _location_summary(leg.get("destination") or {}),
        "departure_time": _iso_or_none(leg.get("departureTimeEstimated") or leg.get("departureTimePlanned")),
        "scheduled_departure_time": _iso_or_none(leg.get("departureTimePlanned")),
        "arrival_time": _iso_or_none(leg.get("arrivalTimeEstimated") or leg.get("arrivalTimePlanned")),
        "scheduled_arrival_time": _iso_or_none(leg.get("arrivalTimePlanned")),
        "mode": product.get("name") or product.get("class"),
        "route": transportation.get("number"),
        "destination_display": (transportation.get("destination") or {}).get("name"),
    }


def _first_route(transit_legs: list[dict[str, Any]]) -> str | None:
    if not transit_legs:
        return None
    return (transit_legs[0].get("transportation") or {}).get("number")


def _location_summary(location: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": location.get("id"),
        "name": location.get("name"),
        "disassembled_name": location.get("disassembledName"),
        "coord": location.get("coord"),
    }


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    fixed = value.replace("Z", "+00:00")
    return datetime.fromisoformat(fixed).astimezone()


def _iso_or_none(value: str | None) -> str | None:
    parsed = _parse_time(value)
    return parsed.isoformat() if parsed else None


def _location_type(value: str) -> str:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) == 2:
        try:
            float(parts[0])
            float(parts[1])
        except ValueError:
            return "any"
        return "coord"
    return "any"


def _excluded_modes(modes: list[str] | None) -> list[str]:
    if not modes:
        return []
    allowed = {MODE_MAP[mode] for mode in modes if mode in MODE_MAP}
    return [str(mode_id) for mode_id in MODE_MAP.values() if mode_id not in allowed]


def _strip_sort_fields(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for option in options:
        option.pop("predicted_departure_dt", None)
        option.pop("predicted_arrival_dt", None)
    return options

