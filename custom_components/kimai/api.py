"""Kimai REST API client."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import (
    API_PATH_ACTIVITIES,
    API_PATH_PROJECTS,
    API_PATH_TIMESHEETS,
    API_PATH_TIMESHEETS_ACTIVE,
    API_PATH_USERS_ME,
    TIMESHEET_PAGE_SIZE,
)

_LOGGER = logging.getLogger(__name__)


class KimaiApiError(Exception):
    """Raised when the Kimai API returns an unexpected/error response."""

    def __init__(self, status: int | None, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class KimaiAuthError(KimaiApiError):
    """Raised when the Kimai API rejects the provided credentials."""


class KimaiConnectionError(KimaiApiError):
    """Raised when the Kimai instance cannot be reached."""


class KimaiApiClient:
    """Thin async wrapper around the Kimai 2.x REST API."""

    def __init__(self, hass: HomeAssistant, base_url: str, api_token: str) -> None:
        self._session = aiohttp_client.async_get_clientsession(hass)
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        }

    async def _request(
        self, method: str, path: str, params: dict[str, Any] | None = None, json: Any = None
    ) -> Any:
        url = f"{self._base_url}{path}"
        _LOGGER.debug("Kimai request: %s %s params=%s", method, url, params)
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                params=params,
                json=json,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                _LOGGER.debug("Kimai response: %s %s -> %s", method, url, response.status)
                if response.status in (401, 403):
                    body = await response.text()
                    _LOGGER.error(
                        "Kimai auth error for %s %s: status=%s body=%s",
                        method, url, response.status, body,
                    )
                    raise KimaiAuthError(response.status, body)
                if response.status >= 400:
                    body = await response.text()
                    _LOGGER.error(
                        "Kimai API error for %s %s: status=%s body=%s",
                        method, url, response.status, body,
                    )
                    raise KimaiApiError(response.status, body)
                if response.status == 204:
                    return None
                return await response.json()
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timed out connecting to Kimai at %s %s", method, url)
            raise KimaiConnectionError(None, "Timed out connecting to Kimai") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error for Kimai at %s %s: %s", method, url, err)
            raise KimaiConnectionError(None, str(err)) from err

    async def async_validate(self) -> None:
        """Validate the base URL and API token against Kimai."""
        await self._request("GET", API_PATH_USERS_ME)

    async def async_get_projects(self, visible: int = 1) -> list[dict[str, Any]]:
        """Fetch projects, defaulting to only visible/active ones."""
        return await self._request("GET", API_PATH_PROJECTS, params={"visible": visible})

    async def async_get_activities(self, visible: int = 1) -> dict[int | None, list[dict[str, Any]]]:
        """Fetch activities grouped by project id.

        Activities with no project (global activities) are keyed under None
        and should be merged into every project's own activity list by the
        caller.
        """
        activities = await self._request("GET", API_PATH_ACTIVITIES, params={"visible": visible})
        grouped: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
        for activity in activities:
            grouped[activity.get("project")].append(activity)
        return grouped

    async def async_get_timesheets(self, begin: str, end: str) -> list[dict[str, Any]]:
        """Fetch all timesheets between begin and end (local datetime strings), paginated."""
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = await self._request(
                "GET",
                API_PATH_TIMESHEETS,
                params={
                    "begin": begin,
                    "end": end,
                    "size": TIMESHEET_PAGE_SIZE,
                    "page": page,
                    "order_by": "begin",
                    "order": "ASC",
                },
            )
            results.extend(batch)
            if len(batch) < TIMESHEET_PAGE_SIZE:
                break
            page += 1
        return results

    async def async_get_active_timesheets(self) -> list[dict[str, Any]]:
        """Fetch currently-running (unfinished) timesheets."""
        return await self._request("GET", API_PATH_TIMESHEETS_ACTIVE)

    async def async_create_timesheet(
        self,
        project: int,
        activity: int,
        begin: str,
        end: str,
        description: str | None = None,
        billable: bool = True,
    ) -> dict[str, Any]:
        """Create a completed timesheet entry."""
        payload: dict[str, Any] = {
            "project": project,
            "activity": activity,
            "begin": begin,
            "end": end,
            "billable": billable,
        }
        if description:
            payload["description"] = description
        return await self._request("POST", API_PATH_TIMESHEETS, json=payload)
