"""Mode de fonctionnement des Sorties 1 et 2."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import SmartPVRouterError
from .const import DOMAIN, OUTPUT_MODES
from .coordinator import SmartPVRouterConfigEntry
from .entity import SmartPVRouterEntity, to_int

MODE_TO_OPTION = {mode: option for option, mode in OUTPUT_MODES.items()}


@dataclass(frozen=True, kw_only=True)
class SmartPVRouterSelectDescription(SelectEntityDescription):
    """Mode d'une sortie : lu dans MODEINFO, changé par /get?Out<n>_mode=N."""

    mode_fn: Callable[[int], int]


SELECTS: tuple[SmartPVRouterSelectDescription, ...] = (
    # MODEINFO = Sortie 2 x 10 + Sortie 1 (website.cpp, /getjson).
    SmartPVRouterSelectDescription(
        key="Out1_mode",
        translation_key="output_1_mode",
        options=list(OUTPUT_MODES),
        mode_fn=lambda modeinfo: modeinfo % 10,
    ),
    SmartPVRouterSelectDescription(
        key="Out2_mode",
        translation_key="output_2_mode",
        options=list(OUTPUT_MODES),
        mode_fn=lambda modeinfo: modeinfo // 10,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPVRouterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Créer les sélecteurs de mode."""
    coordinator = entry.runtime_data
    if "MODEINFO" not in coordinator.data:
        return
    async_add_entities(SmartPVRouterModeSelect(coordinator, description) for description in SELECTS)


class SmartPVRouterModeSelect(SmartPVRouterEntity, SelectEntity):
    """Mode d'une sortie du Smart PV-Router."""

    entity_description: SmartPVRouterSelectDescription

    def __init__(self, coordinator, description: SmartPVRouterSelectDescription) -> None:
        """Créer le sélecteur."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        """Mode actuel ; inconnu pour le mode Test (9)."""
        modeinfo = to_int(self.coordinator.data.get("MODEINFO"))
        if modeinfo is None:
            return None
        return MODE_TO_OPTION.get(self.entity_description.mode_fn(modeinfo))

    async def async_select_option(self, option: str) -> None:
        """Changer le mode (enregistré par le routeur)."""
        try:
            await self.coordinator.api.async_command(
                self.entity_description.key, str(OUTPUT_MODES[option])
            )
        except SmartPVRouterError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
        await self.coordinator.async_request_refresh()
