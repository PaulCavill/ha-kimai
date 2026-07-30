"""Data update coordinator for the Kimai integration."""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import KimaiApiClient, KimaiApiError, KimaiAuthError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


@dataclass
class KimaiProjectData:
    """Aggregated Kimai data for a single project."""

    id: int
    name: str
    customer_id: int | None
    customer_name: str | None
    week_seconds: float
    month_seconds: float
    active: bool
    activities: list[dict[str, Any]]
    time_budget_seconds: float


class KimaiDataUpdateCoordinator(DataUpdateCoordinator[dict[int, KimaiProjectData]]):
    """Poll Kimai and aggregate week/month totals per active project."""

    def __init__(self, hass: HomeAssistant, client: KimaiApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, KimaiProjectData]:
        now = dt_util.now()
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        try:
            projects = await self.client.async_get_projects(visible=1)
            activities_by_project = await self.client.async_get_activities(visible=1)
            timesheets = await self.client.async_get_timesheets(
                begin=month_start.strftime(DATETIME_FORMAT),
                end=now.strftime(DATETIME_FORMAT),
            )
            active_entries = await self.client.async_get_active_timesheets()
        except KimaiAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KimaiApiError as err:
            _LOGGER.error(
                "Kimai API error during update: status=%s message=%s", err.status, err.message
            )
            raise UpdateFailed(str(err)) from err

        active_project_ids = {
            entry["project"] for entry in active_entries if entry.get("project")
        }

        week_seconds: dict[int, float] = defaultdict(float)
        month_seconds: dict[int, float] = defaultdict(float)
        for entry in timesheets:
            project_id = entry.get("project")
            if project_id is None:
                continue
            duration = entry.get("duration") or 0
            month_seconds[project_id] += duration

            begin = dt_util.parse_datetime(entry["begin"]) if entry.get("begin") else None
            if begin is not None:
                if begin.tzinfo is None:
                    begin = begin.replace(tzinfo=week_start.tzinfo)
                if begin >= week_start:
                    week_seconds[project_id] += duration

        global_activities = activities_by_project.get(None, [])

        data: dict[int, KimaiProjectData] = {}
        for project in projects:
            project_id = project["id"]
            total_month = month_seconds.get(project_id, 0)
            if not project.get("visible", True) or total_month <= 0:
                continue

            project_activities = activities_by_project.get(project_id, []) + global_activities
            data[project_id] = KimaiProjectData(
                id=project_id,
                name=project.get("name") or f"Project {project_id}",
                customer_id=project.get("customer"),
                customer_name=project.get("customerName") or project.get("parentTitle"),
                week_seconds=week_seconds.get(project_id, 0),
                month_seconds=total_month,
                active=project_id in active_project_ids,
                activities=[
                    {"id": activity["id"], "name": activity.get("name") or f"Activity {activity['id']}"}
                    for activity in project_activities
                ],
                time_budget_seconds=project.get("timeBudget") or 0,
            )
        return data
