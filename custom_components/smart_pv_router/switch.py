"""Boost, EcoMax et écran.

Firmware avec la clé « API » (1 ou plus) dans /getjson : /get?BOOST=ON|OFF,
/get?ECOMAX=ON|OFF et /get?DISPLAY=ON|OFF fixent l'état, même répétés.

Firmware plus ancien : /get?BOOST=… et /get?ECOMAX=… inversent l'état, quelle que soit la
valeur envoyée. On relit donc l'état juste avant, et on n'envoie la commande que s'il
diffère de celui demandé. L'écran ne se commande pas en HTTP sur ces versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import SmartPVRouterError
from .const import API_ON_OFF_COMMANDS, DOMAIN
from .coordinator import SmartPVRouterConfigEntry
from .entity import SmartPVRouterEntity, to_bool


@dataclass(frozen=True, kw_only=True)
class SmartPVRouterSwitchDescription(SwitchEntityDescription):
    """Interrupteur : état lu dans /getjson (clé `key`), commandé par /get?`command`=…

    `min_api` : version d'API à partir de laquelle la commande existe (0 : toujours).
    """

    command: str
    min_api: int = 0


SWITCHES: tuple[SmartPVRouterSwitchDescription, ...] = (
    SmartPVRouterSwitchDescription(key="BOOST", translation_key="boost", command="BOOST"),
    SmartPVRouterSwitchDescription(key="ECOMAX", translation_key="ecomax", command="ECOMAX"),
    SmartPVRouterSwitchDescription(
        key="DISPLAY",
        translation_key="display",
        command="DISPLAY",
        min_api=API_ON_OFF_COMMANDS,
        entity_category=EntityCategory.CONFIG,
    ),
    # « Relance Réseau S2 » de la page Système (option NIGHT_OUT2 du firmware) : pendant la plage
    # horaire, la Sortie 2 est aussi chauffée par le réseau, comme la Sortie 1, jusqu'à saturation de
    # sa charge et dans la limite de la puissance de délestage. Désactivée : seule la Sortie 1 est
    # relancée. Lue dans /getparams?pwd=0 (API ≥ 2), réglée par /get?NIGHT_OUT2=1|0.
    SmartPVRouterSwitchDescription(
        key="NIGHT_OUT2",
        translation_key="relaunch_output_2",
        command="NIGHT_OUT2",
        min_api=2,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPVRouterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Créer les interrupteurs dont la clé existe (ECOMAX dépend d'une option)."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartPVRouterSwitch(coordinator, description)
        for description in SWITCHES
        if description.key in coordinator.data
        and coordinator.api_version >= description.min_api
    )


class SmartPVRouterSwitch(SmartPVRouterEntity, SwitchEntity):
    """Boost, EcoMax ou écran."""

    entity_description: SmartPVRouterSwitchDescription

    def __init__(self, coordinator, description: SmartPVRouterSwitchDescription) -> None:
        """Créer l'interrupteur."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """État lu dans /getjson."""
        return to_bool(self.coordinator.data.get(self.entity_description.key))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Mettre en marche."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Arrêter."""
        await self._async_set(False)

    async def _async_set(self, on: bool) -> None:
        api = self.coordinator.api
        description = self.entity_description
        try:
            if description.key == "NIGHT_OUT2":
                # Réglage (1 / 0), pas une commande ON / OFF ; relu dans /getparams?pwd=0.
                await api.async_command(description.command, "1" if on else "0")
                self.coordinator.async_refresh_settings_soon()
            elif self.coordinator.api_version >= API_ON_OFF_COMMANDS:
                await api.async_command(description.command, "ON" if on else "OFF")
            else:
                data = await api.async_get_json()
                if to_bool(data.get(description.key)) != on:
                    await api.async_command(description.command, "1")
        except SmartPVRouterError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
        await self.coordinator.async_request_refresh()
