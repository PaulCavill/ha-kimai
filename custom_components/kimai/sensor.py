"""Sensor platform for the Kimai integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BASE_URL, DOMAIN
from .coordinator import KimaiDataUpdateCoordinator, KimaiProjectData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kimai project sensors, adding new ones as projects start qualifying."""
    coordinator = entry.runtime_data.coordinator
    known_project_ids: set[int] = set()

    @callback
    def _async_add_new_entities() -> None:
        new_ids = set(coordinator.data) - known_project_ids
        if not new_ids:
            return
        known_project_ids.update(new_ids)
        async_add_entities(
            KimaiProjectSensor(coordinator, entry, project_id) for project_id in new_ids
        )

    _async_add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))


class KimaiProjectSensor(CoordinatorEntity[KimaiDataUpdateCoordinator], SensorEntity):
    """Sensor showing hours tracked this month for a single Kimai project."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:briefcase-clock"

    def __init__(
        self,
        coordinator: KimaiDataUpdateCoordinator,
        entry: Any,
        project_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._project_id = project_id
        self._attr_unique_id = f"{entry.entry_id}_project_{project_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Kimai",
            manufacturer="Kimai",
            model="Kimai time tracking",
            configuration_url=entry.data.get(CONF_BASE_URL),
        )

    @property
    def _project(self) -> KimaiProjectData | None:
        return self.coordinator.data.get(self._project_id)

    @property
    def name(self) -> str | None:
        project = self._project
        return project.name if project else None

    @property
    def available(self) -> bool:
        return super().available and self._project is not None

    @property
    def native_value(self) -> float | None:
        project = self._project
        if project is None:
            return None
        return round(project.month_seconds / 3600, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        project = self._project
        if project is None:
            return {}
        return {
            "project_name": project.name,
            "raw_project_name": project.raw_project_name,
            "week_hours": round(project.week_seconds / 3600, 1),
            "week_seconds": project.week_seconds,
            "month_hours": round(project.month_seconds / 3600, 1),
            "month_seconds": project.month_seconds,
            "active": project.active,
            "project_id": project.id,
            "customer_id": project.customer_id,
            "customer_name": project.customer_name,
            "activities": project.activities,
            "time_budget_hours": (
                round(project.time_budget_seconds / 3600, 1)
                if project.time_budget_seconds
                else 0
            ),
        }
