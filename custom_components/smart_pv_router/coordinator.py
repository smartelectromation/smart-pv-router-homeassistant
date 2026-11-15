"""Lecture périodique de /getjson."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartPVRouterApi, SmartPVRouterError
from .const import DOMAIN, LOGGER, SCAN_INTERVAL

type SmartPVRouterConfigEntry = ConfigEntry[SmartPVRouterCoordinator]


class SmartPVRouterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Données du routeur, relues toutes les 5 s."""

    config_entry: SmartPVRouterConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SmartPVRouterConfigEntry,
        api: SmartPVRouterApi,
    ) -> None:
        """Préparer la lecture."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    @property
    def api_version(self) -> int:
        """Version de l'API du routeur : clé « API » de /getjson, 0 si le firmware ne la donne pas.

        1 : /get?BOOST=ON|OFF, /get?ECOMAX=ON|OFF et /get?DISPLAY=ON|OFF fixent l'état ;
        /getjson donne MAC, BOOSTTIME, DIMMER1 et DIMMER2.
        """
        value = (self.data or {}).get("API")
        if isinstance(value, bool) or not isinstance(value, int):
            return 0
        return value

    async def _async_update_data(self) -> dict[str, Any]:
        """Lire /getjson."""
        try:
            return await self.api.async_get_json()
        except SmartPVRouterError as err:
            raise UpdateFailed(f"Smart PV-Router injoignable : {err}") from err
