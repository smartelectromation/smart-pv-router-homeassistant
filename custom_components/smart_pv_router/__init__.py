"""Intégration Home Assistant du Smart PV-Router by Smart Electromation Technology."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac

from .api import SmartPVRouterApi
from .const import DOMAIN
from .coordinator import SmartPVRouterConfigEntry, SmartPVRouterCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: SmartPVRouterConfigEntry) -> bool:
    """Connecter le routeur et créer ses entités."""
    api = SmartPVRouterApi(async_get_clientsession(hass), entry.data[CONF_HOST])
    coordinator = SmartPVRouterCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    if entry.unique_id is None:
        await _async_set_unique_id(hass, entry, coordinator)
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_set_unique_id(
    hass: HomeAssistant,
    entry: SmartPVRouterConfigEntry,
    coordinator: SmartPVRouterCoordinator,
) -> None:
    """Donner son adresse MAC à un routeur ajouté à la main, dès qu'elle est connue.

    Sans elle, la découverte automatique proposerait une seconde fois le même routeur.
    Source : clé MAC de /getjson, absente des anciens firmwares.
    """
    raw = coordinator.data.get("MAC")
    if not isinstance(raw, str) or len(raw) != 12:
        return
    try:
        int(raw, 16)
    except ValueError:
        return
    mac = format_mac(raw)
    if any(other.unique_id == mac for other in hass.config_entries.async_entries(DOMAIN)):
        return
    hass.config_entries.async_update_entry(entry, unique_id=mac)


async def async_unload_entry(hass: HomeAssistant, entry: SmartPVRouterConfigEntry) -> bool:
    """Retirer le routeur."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
