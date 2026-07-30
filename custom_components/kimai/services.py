"""Services for the Kimai integration."""
from __future__ import annotations

from datetime import datetime, timedelta

import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .api import KimaiApiError
from .const import (
    ATTR_ACTIVITY_ID,
    ATTR_BILLABLE,
    ATTR_DATE,
    ATTR_DESCRIPTION,
    ATTR_DURATION_MINUTES,
    ATTR_END_TIME,
    ATTR_START_TIME,
    DOMAIN,
    SERVICE_ADD_TIMESHEET,
)
from .coordinator import DATETIME_FORMAT

ADD_TIMESHEET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_ACTIVITY_ID): vol.Coerce(int),
        vol.Required(ATTR_DATE): cv.date,
        vol.Required(ATTR_START_TIME): cv.time,
        vol.Optional(ATTR_DURATION_MINUTES): vol.Coerce(int),
        vol.Optional(ATTR_END_TIME): cv.time,
        vol.Optional(ATTR_DESCRIPTION): cv.string,
        vol.Optional(ATTR_BILLABLE, default=True): cv.boolean,
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register Kimai services, once regardless of how many entries exist."""
    if hass.services.has_service(DOMAIN, SERVICE_ADD_TIMESHEET):
        return

    async def _async_handle_add_timesheet(call: ServiceCall) -> None:
        entity_id = call.data[ATTR_ENTITY_ID]

        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)
        if entity_entry is None or entity_entry.config_entry_id is None:
            raise HomeAssistantError(f"'{entity_id}' is not a known Kimai project entity")

        config_entry = hass.config_entries.async_get_entry(entity_entry.config_entry_id)
        if config_entry is None or config_entry.domain != DOMAIN:
            raise HomeAssistantError(f"'{entity_id}' is not a known Kimai project entity")

        prefix = f"{config_entry.entry_id}_project_"
        if entity_entry.unique_id is None or not entity_entry.unique_id.startswith(prefix):
            raise HomeAssistantError(f"'{entity_id}' is not a known Kimai project entity")
        project_id = int(entity_entry.unique_id[len(prefix) :])

        duration_minutes = call.data.get(ATTR_DURATION_MINUTES)
        end_time = call.data.get(ATTR_END_TIME)
        if (duration_minutes is None) == (end_time is None):
            raise ServiceValidationError(
                "Provide exactly one of duration_minutes or end_time"
            )

        begin_dt = datetime.combine(call.data[ATTR_DATE], call.data[ATTR_START_TIME])
        if end_time is not None:
            end_dt = datetime.combine(call.data[ATTR_DATE], end_time)
            if end_dt <= begin_dt:
                end_dt += timedelta(days=1)
        else:
            end_dt = begin_dt + timedelta(minutes=duration_minutes)

        runtime_data = config_entry.runtime_data

        try:
            await runtime_data.client.async_create_timesheet(
                project=project_id,
                activity=call.data[ATTR_ACTIVITY_ID],
                begin=begin_dt.strftime(DATETIME_FORMAT),
                end=end_dt.strftime(DATETIME_FORMAT),
                description=call.data.get(ATTR_DESCRIPTION),
                billable=call.data[ATTR_BILLABLE],
            )
        except KimaiApiError as err:
            raise HomeAssistantError(f"Kimai rejected the timesheet entry: {err.message}") from err

        await runtime_data.coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TIMESHEET,
        _async_handle_add_timesheet,
        schema=ADD_TIMESHEET_SCHEMA,
    )
