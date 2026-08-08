# Kimai for Home Assistant

A custom Home Assistant integration for [Kimai](https://www.kimai.org/) (2.x)
time tracking, plus a small Lovelace dashboard card to view weekly/monthly
totals per project and log new time entries without leaving Home Assistant.

## What you get

- One sensor entity per active Kimai project that has at least one timesheet
  entry in the current week or current month. State is total hours logged
  this month; attributes include hours for the current week, hours for the
  current month, whether a timer is currently running for that project, and
  the project's activities (needed to log new time).
- A `kimai.add_timesheet` service to log a completed time entry (project,
  activity, date, start time, duration or end time, description) directly
  against Kimai's REST API.
- A `kimai-card` Lovelace card that lists your Kimai project entities and
  provides an "+ Add time" form that calls the service above. The card reads
  entity state over Home Assistant's existing frontend websocket connection —
  no separate backend/websocket server is required.

## Requirements

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
dashboard view. The card's title defaults to "Kimai" but can be customized
by editing the card in YAML mode and adding a `title` field, e.g.:

```yaml
type: custom:kimai-card
title: My Time Tracker
title_size: 1.1em
```

`title_size` accepts any CSS font-size value (e.g. `1.1em`, `20px`) and
defaults to `1.5em` if omitted — useful for shrinking a longer custom title
so it doesn't wrap.

## Known limitations

- New entries are sent to Kimai as naive local date/times. This assumes your
  Kimai account's configured timezone matches your Home Assistant instance's
  timezone. If they differ, logged times may be off by the difference.
- Automatic Lovelace resource registration uses an internal Home Assistant
  API and is best-effort; use the manual steps above if it doesn't appear.
- Project entities, once created, are not removed if that project's tracked
  time later drops back to zero (e.g. at the start of a new month before any
  time has been logged again).
- Kimai requires selecting an **activity** in addition to a project for every
  timesheet entry, so the add-time form always includes an activity dropdown.
