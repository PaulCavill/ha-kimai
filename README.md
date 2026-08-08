# Kimai for Home Assistant

A custom Home Assistant integration for [Kimai](https://www.kimai.org/) (2.x)
time tracking, plus a small Lovelace dashboard card to view weekly/monthly
totals per project and log new time entries without leaving Home Assistant.

## What you get

All entities belong to a single "Kimai" device per configured instance.

- **One sensor per project with time logged this month.** State is total hours
  logged in the current calendar month (rounded to 1 decimal). Attributes:
  `week_hours` / `week_seconds`, `month_hours` / `month_seconds`, `active`
  (a timer is currently running for that project), `project_id`,
  `project_name`, `customer_id`, `customer_name`, `activities` (needed to log
  new time), and `time_budget_hours`.
- **A "Projects" sensor** (diagnostic) whose state is the number of visible
  Kimai projects and whose `projects` attribute lists every one of them with
  its activities — regardless of tracked time. This is the stable data source
  for the card's add-time picker, which would otherwise go empty right after a
  month rolls over.
- **A "Week Total" sensor** with total hours logged across all projects in the
  current week (Monday-based).
- **A `kimai.add_timesheet` service** to log a completed time entry (project,
  activity, date, start time, duration *or* end time, description, billable
  flag) directly against Kimai's REST API. It takes any entity from this
  integration as its target — the entity only identifies which Kimai instance
  to write to; the project comes from `project_id`.
- **A `kimai-card` Lovelace card** that lists your Kimai project entities in a
  two-column grid (with customer name, a running-timer badge, and a progress
  bar when the project has a time budget), a "Sync" button to refresh data on
  demand, and an "+ Add time" form that calls the service above. The card reads
  entity state over Home Assistant's existing frontend websocket connection —
  no separate backend/websocket server is required.

Kimai is polled every **30 minutes**. Use the card's Sync button, or
`homeassistant.update_entity`, to refresh sooner. Adding a time entry through
the service refreshes automatically.

## Requirements

- Home Assistant **2024.7.0** or newer.
- A self-hosted (or cloud) **Kimai 2.x** instance reachable from Home
  Assistant.
- An **API token** generated from your Kimai user profile (Settings → API
  Token). Username/password and the legacy `X-AUTH-*` header scheme are not
  supported — Kimai is deprecating them in favor of tokens.

## Installation

### HACS (custom repository)

1. HACS → Integrations → ⋮ → Custom repositories → add this repository URL
   with category "Integration".
2. Install "Kimai", then restart Home Assistant.

### Manual

1. Copy `custom_components/kimai` into your Home Assistant `config/custom_components/`
   directory.
2. Restart Home Assistant.

## Setting up the integration

Settings → Devices & Services → Add Integration → search for **Kimai**, then
enter your Kimai base URL (e.g. `https://kimai.example.com`) and your API
token.

## Adding the dashboard card

The integration serves the card automatically at `/kimai_static/kimai-card.js`
and tries to register it as a Lovelace resource for you (storage-mode
dashboards only). If it doesn't show up automatically, or you use a
YAML-mode dashboard, add it manually:

Settings → Dashboards → ⋮ → Resources → Add Resource:

- URL: `/kimai_static/kimai-card.js`
- Resource type: JavaScript Module

Then add a card of type `Custom: Kimai Card` (`custom:kimai-card`) to any
dashboard view. All options are optional and set by editing the card in YAML
mode:

```yaml
type: custom:kimai-card
title: My Time Tracker
title_size: 1.1em
entities:
  - sensor.kimai_some_project
  - sensor.kimai_another_project
```

| Option | Default | Description |
| --- | --- | --- |
| `title` | `Kimai` | Card heading. |
| `title_size` | `1.5em` | Any CSS font-size value — useful for shrinking a longer custom title so it doesn't wrap. |
| `entities` | auto-detected | Explicit list of project rows to show. Omit it and the card lists every Kimai project sensor it finds, sorted by entity id. |

## Using the service

```yaml
action: kimai.add_timesheet
target:
  entity_id: sensor.kimai_projects
data:
  project_id: 12
  activity_id: 3
  date: "2026-08-08"
  start_time: "09:00:00"
  duration_minutes: 90
  description: Fixed the thing
  billable: true
```

Provide exactly one of `duration_minutes` or `end_time` — supplying both, or
neither, is rejected. An `end_time` earlier than `start_time` is treated as
crossing midnight. `billable` defaults to `true`. Project and activity ids come
from the `projects` attribute of the "Projects" sensor (or a project sensor's
`activities` attribute).

## Known limitations

- New entries are sent to Kimai as naive local date/times. This assumes your
  Kimai account's configured timezone matches your Home Assistant instance's
  timezone. If they differ, logged times may be off by the difference.
- Automatic Lovelace resource registration uses an internal Home Assistant
  API and is best-effort; use the manual steps above if it doesn't appear.
