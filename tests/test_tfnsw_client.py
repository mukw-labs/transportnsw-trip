"""Tests for TfNSW trip normalization and ranking."""

from __future__ import annotations

from datetime import datetime

from custom_components.transportnsw_trip.const import (
    CONF_DATE_TIME,
    CONF_DESTINATION,
    CONF_JOURNEY_TYPE,
    CONF_NAME,
    CONF_ORIGIN,
    CONF_TIME,
    CONF_WEEKDAYS,
    DOMAIN,
    JOURNEY_TYPE_FIXED_RECURRING,
    JOURNEY_TYPE_ONE_OFF,
)
from custom_components.transportnsw_trip.coordinator import _journey_date_time
from custom_components.transportnsw_trip.entity_helpers import (
    desired_device_identifiers,
    desired_unique_ids,
    journey_device_identifier,
    journey_suggested_object_id,
)
from custom_components.transportnsw_trip.tfnsw_client import (
    _excluded_mode_params,
    normalize_trip_response,
    rank_options,
)


def test_normalize_trip_response_computes_delay_and_lateness() -> None:
    """Normalize journey times into stable response fields."""
    raw = {
        "journeys": [
            {
                "legs": [
                    {
                        "origin": {"id": "1", "name": "Central"},
                        "destination": {"id": "2", "name": "Parramatta"},
                        "departureTimePlanned": "2099-01-01T08:00:00Z",
                        "departureTimeEstimated": "2099-01-01T08:03:00Z",
                        "arrivalTimePlanned": "2099-01-01T08:30:00Z",
                        "arrivalTimeEstimated": "2099-01-01T08:35:00Z",
                        "transportation": {
                            "number": "T1",
                            "product": {"class": 1, "name": "Train"},
                            "destination": {"name": "Parramatta"},
                        },
                    }
                ]
            }
        ]
    }

    options = normalize_trip_response(raw, include_raw_payload=False)

    assert len(options) == 1
    assert options[0]["route"] == "T1"
    assert options[0]["realtime_delay"] == 180
    assert options[0]["lateness_minutes"] == 5
    assert options[0]["transfers"] == 0
    assert "raw_payload" not in options[0]


def test_normalize_trip_response_reads_times_from_leg_locations() -> None:
    """TfNSW rapidJSON puts leg times on origin/destination objects."""
    raw = {
        "journeys": [
            {
                "legs": [
                    {
                        "duration": 270,
                        "origin": {
                            "id": "2073161",
                            "name": "Pymble",
                            "departureTimePlanned": "2099-01-01T08:00:00Z",
                            "departureTimeEstimated": "2099-01-01T08:02:00Z",
                        },
                        "destination": {
                            "id": "207191",
                            "name": "Killara",
                            "arrivalTimePlanned": "2099-01-01T08:30:00Z",
                            "arrivalTimeEstimated": "2099-01-01T08:33:00Z",
                        },
                        "transportation": {
                            "number": "T1",
                            "product": {"class": 1, "name": "Train"},
                        },
                    }
                ]
            }
        ]
    }

    options = normalize_trip_response(raw, include_raw_payload=False)

    assert len(options) == 1
    assert options[0]["route"] == "T1"
    assert options[0]["realtime_delay"] == 120
    assert options[0]["lateness_minutes"] == 3
    assert options[0]["departure_time"].endswith("08:02:00+00:00")


def test_rank_options_for_departure_prefers_earliest_arrival() -> None:
    """For depart-by searches, best means earliest predicted arrival."""
    raw = {
        "journeys": [
            _journey("2099-01-01T08:00:00Z", "2099-01-01T08:40:00Z", "slow"),
            _journey("2099-01-01T08:10:00Z", "2099-01-01T08:30:00Z", "fast"),
        ]
    }
    options = normalize_trip_response(raw, include_raw_payload=False)

    ranked = rank_options(options, arrive_by=False, target_time=datetime.fromisoformat("2099-01-01T08:00:00+00:00"))

    assert ranked[0]["route"] == "fast"
    assert ranked[1]["route"] == "slow"
    assert "predicted_arrival_dt" not in ranked[0]


def test_rank_options_for_arrival_prefers_latest_feasible_departure() -> None:
    """For arrive-by searches, best means latest departure that arrives in time."""
    raw = {
        "journeys": [
            _journey("2099-01-01T07:30:00Z", "2099-01-01T08:20:00Z", "early"),
            _journey("2099-01-01T07:55:00Z", "2099-01-01T08:25:00Z", "latest"),
            _journey("2099-01-01T08:10:00Z", "2099-01-01T08:40:00Z", "late"),
        ]
    }
    options = normalize_trip_response(raw, include_raw_payload=False)

    ranked = rank_options(options, arrive_by=True, target_time=datetime.fromisoformat("2099-01-01T08:30:00+00:00"))

    assert [option["route"] for option in ranked] == ["latest", "early"]


def test_journey_date_time_returns_none_for_expired_one_off() -> None:
    """Expired one-off journeys should not keep polling the API."""
    journey = {
        CONF_JOURNEY_TYPE: JOURNEY_TYPE_ONE_OFF,
        CONF_DATE_TIME: "2000-01-01T08:00:00+10:00",
    }

    assert _journey_date_time(journey) is None


def test_journey_date_time_resolves_fixed_recurring() -> None:
    """Fixed recurring journeys resolve to a future matching datetime."""
    journey = {
        CONF_JOURNEY_TYPE: JOURNEY_TYPE_FIXED_RECURRING,
        CONF_TIME: "08:30:00",
        CONF_WEEKDAYS: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    }

    assert _journey_date_time(journey) is not None


def test_excluded_mode_params_use_tfnsw_checkbox_format() -> None:
    """TfNSW trip planner expects exclMOT flags, not a comma-separated list."""
    params = _excluded_mode_params(["train"])

    assert params["excludedMeans"] == "checkbox"
    assert params["exclMOT_2"] == "1"
    assert "exclMOT_1" not in params


def test_journey_helpers_build_stable_entity_and_device_ids() -> None:
    """Configured journeys should map to one device and three entities."""
    journeys = [
        {
            CONF_NAME: "Morning Train",
            CONF_ORIGIN: "2073161",
            CONF_DESTINATION: "207191",
        }
    ]

    assert journey_device_identifier("entry123", "Morning Train") == "entry123_Morning Train"
    assert journey_suggested_object_id("Morning Train", "best_delay") == "Morning Train_best_delay"
    assert desired_device_identifiers("entry123", journeys) == {
        (DOMAIN, "entry123_Morning Train")
    }
    assert desired_unique_ids("entry123", journeys) == {
        "entry123_Morning Train_best_delay",
        "entry123_Morning Train_best_departure",
        "entry123_Morning Train_disrupted",
    }


def _journey(departure: str, arrival: str, route: str) -> dict:
    return {
        "legs": [
            {
                "origin": {"id": "1", "name": "Origin"},
                "destination": {"id": "2", "name": "Destination"},
                "departureTimePlanned": departure,
                "departureTimeEstimated": departure,
                "arrivalTimePlanned": arrival,
                "arrivalTimeEstimated": arrival,
                "transportation": {
                    "number": route,
                    "product": {"class": 1, "name": "Train"},
                },
            }
        ]
    }
