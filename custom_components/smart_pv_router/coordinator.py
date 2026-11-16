"""Lecture périodique de /getjson."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartPVRouterApi, SmartPVRouterError
from .const import API_SETTINGS, DOMAIN, LOGGER, SCAN_INTERVAL, SETTINGS_INTERVAL_S

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
        # Réglages de /getparams?pwd=0 (API ≥ 2), ajoutés aux données de /getjson.
        self._settings: dict[str, Any] = {}
        self._settings_at = 0.0

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

    def async_refresh_settings_soon(self) -> None:
        """Relire les réglages à la prochaine lecture (après un changement)."""
        self._settings_at = 0.0

    async def _async_update_data(self) -> dict[str, Any]:
        """Lire /getjson, et les réglages toutes les 60 s si le firmware le permet (API ≥ 2)."""
        try:
            data = await self.api.async_get_json()
        except SmartPVRouterError as err:
            raise UpdateFailed(f"Smart PV-Router injoignable : {err}") from err
        api = data.get("API")
        if isinstance(api, int) and not isinstance(api, bool) and api >= API_SETTINGS:
            now = time.monotonic()
            if now - self._settings_at >= SETTINGS_INTERVAL_S:
                try:
                    self._settings = await self.api.async_get_settings()
                    self._settings_at = now
                except SmartPVRouterError as err:
                    LOGGER.debug("Réglages non relus : %s", err)
        else:
            self._settings = {}
        # /getjson l'emporte pour les clés communes.
        return {**self._settings, **data}
