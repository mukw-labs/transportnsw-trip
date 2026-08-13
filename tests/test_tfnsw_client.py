"""Tests for TfNSW trip normalization and ranking."""

from __future__ import annotations

from datetime import datetime

from custom_components.transportnsw_trip.tfnsw_client import normalize_trip_response, rank_options


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

