"""Diagnostics téléchargeables pour le support."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import SmartPVRouterConfigEntry

TO_REDACT = {"SSID", "MAC", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SmartPVRouterConfigEntry
) -> dict[str, Any]:
    """Configuration et dernière lecture de /getjson, sans données personnelles."""
    return {
        "entry": async_redact_data(
            {"data": dict(entry.data), "unique_id": entry.unique_id}, TO_REDACT
        ),
        "getjson": async_redact_data(entry.runtime_data.data, TO_REDACT),
    }
