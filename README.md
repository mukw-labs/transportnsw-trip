# Transport NSW Trip Planner for Home Assistant

Custom Home Assistant integration for planned Transport for NSW trips.

This integration is currently a prototype scaffold. It provides:

- `transportnsw_trip.plan_trip` service for one-off route planning
- Async TfNSW Trip Planner API client
- Best/next option ranking with delay/lateness calculation
- Optional configured journey sensors
- HACS metadata

## Requirements

You need a TfNSW Open Data API key with access to the Trip Planner APIs.

## Example Service Call

```yaml
action: transportnsw_trip.plan_trip
response_variable: trip
data:
  origin: "Central Station"
  destination: "Parramatta Station"
  depart_by: "2026-08-14T08:30:00+10:00"
  modes:
    - train
    - metro
  max_results: 3
```

The service returns a response containing `best_option`, `next_option`, and `options`.

Example response:

```json
{
  "best_option": {
    "journey_id": "2026-08-13T22:33:00+00:00:2026-08-13T23:05:00+00:00:T1",
    "route": "T1",
    "departure_time": "2026-08-14T08:33:00+10:00",
    "scheduled_departure_time": "2026-08-14T08:30:00+10:00",
    "arrival_time": "2026-08-14T09:05:00+10:00",
    "scheduled_arrival_time": "2026-08-14T09:02:00+10:00",
    "duration": 1920,
    "transfers": 0,
    "realtime_delay": 180,
    "predicted_arrival": "2026-08-14T09:05:00+10:00",
    "lateness_minutes": 3,
    "legs": []
  },
  "next_option": null,
  "options": [],
  "last_updated": "2026-08-13T12:00:00+10:00"
}
```

## Development

Useful checks:

```bash
python3 -m compileall custom_components tests
python3 -m pytest
```

For full Home Assistant validation, run `hassfest` and `pytest-homeassistant-custom-component`
in a Home Assistant development environment.

## Current Limitations

- Existing journeys can be added and removed from the UI, but editing an existing journey currently
  requires removing and re-adding it.
- GTFS-RT vehicle position and occupancy enrichment is not implemented in this first build.
- The service currently uses the first configured API key if multiple entries exist.

## Installation

Copy `custom_components/transportnsw_trip` into your Home Assistant `custom_components`
directory, restart Home Assistant, then add the integration from Settings > Devices & Services.

## Configured Journeys

After adding the integration, open Configure from the integration card. The options UI supports:

- Refresh settings: set the polling interval in seconds.
- Fixed recurring journey: repeat on selected weekdays at a fixed local time. The time can be used
  as either a depart-at time or an arrive-by time.
- One-off journey: query one exact local date/time. Once the date/time has passed, the entity stops
  querying and reports no active option.
- Remove journey: delete an existing saved journey.

Configured journeys create one Home Assistant device per trip, with sensors for recommended
departure time, recommended arrival delay, next departure time, and next arrival delay, plus a
binary sensor for whether the recommended trip is delayed. Saving options reloads the integration
so entity changes are applied.

Calendar-based scheduling is intentionally not required for the first implementation. A Home
Assistant calendar is a good future trigger/source for recurring events, but the integration still
needs transit-specific fields such as origin, destination, depart-vs-arrive, modes, and result count.
