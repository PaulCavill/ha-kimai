"""Config flow for the Kimai integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .api import KimaiApiClient, KimaiApiError, KimaiAuthError, KimaiConnectionError
from .const import CONF_API_TOKEN, CONF_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        ),
        vol.Required(CONF_API_TOKEN): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


class KimaiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kimai."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].rstrip("/")
            client = KimaiApiClient(self.hass, base_url, user_input[CONF_API_TOKEN])
            try:
                await client.async_validate()
            except KimaiAuthError:
                errors["base"] = "invalid_auth"
            except KimaiConnectionError:
                errors["base"] = "cannot_connect"
            except KimaiApiError:
                errors["base"] = "unknown"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Kimai connection")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(base_url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Kimai ({base_url})",
                    data={
                        CONF_BASE_URL: base_url,
                        CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
