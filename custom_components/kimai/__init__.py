"""The Kimai integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import KimaiApiClient
from .const import CONF_API_TOKEN, CONF_BASE_URL
from .coordinator import KimaiDataUpdateCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

CARD_URL = "/kimai_static/kimai-card.js"
CARD_PATH = Path(__file__).parent / "www" / "kimai-card.js"


@dataclass
class KimaiRuntimeData:
    """Runtime data stored on the config entry."""

    client: KimaiApiClient
    coordinator: KimaiDataUpdateCoordinator


KimaiConfigEntry = ConfigEntry[KimaiRuntimeData]

_static_path_registered = False


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up shared resources for the Kimai integration.

    Runs once regardless of how many config entries exist, so the static
    path/Lovelace resource registration must not assume an entry is present.
    """
    global _static_path_registered
    if not _static_path_registered:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_PATH), True)]
        )
        _static_path_registered = True
    await _async_register_lovelace_resource(hass)
    return True


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Best-effort auto-registration of the card as a Lovelace resource.

    Uses an internal/undocumented Lovelace storage API that has shifted
    across HA releases, so failures here are logged and left to the manual
    fallback documented in the README rather than raised.
    """
    try:
        lovelace = hass.data.get("lovelace")
        if lovelace is None or getattr(lovelace, "mode", None) != "storage":
            return
        resources = lovelace.resources
        if hasattr(resources, "async_load"):
            await resources.async_load()
        existing = {item["url"] for item in resources.async_items()}
        if CARD_URL not in existing:
            await resources.async_create_item({"res_type": "module", "url": CARD_URL})
    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Could not automatically register the Kimai card as a Lovelace "
            "resource; add %s manually under Settings > Dashboards > Resources",
            CARD_URL,
        )


async def async_setup_entry(hass: HomeAssistant, entry: KimaiConfigEntry) -> bool:
    """Set up Kimai from a config entry."""
    client = KimaiApiClient(hass, entry.data[CONF_BASE_URL], entry.data[CONF_API_TOKEN])
    coordinator = KimaiDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = KimaiRuntimeData(client=client, coordinator=coordinator)

    async_setup_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KimaiConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
