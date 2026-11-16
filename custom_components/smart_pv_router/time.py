"""Plages horaires de relance (heures creuses).

Lues dans /getparams?pwd=0 (firmware avec ``API`` ≥ 2), réglées par /get?<clé>=hh:mm. Comme sur
la page du routeur : début (NIGHTTIME) et fin (DAYTIME) de la plage horaire ; NIGHTTIME2 et DAYTIME2
sont une seconde plage horaire (pas la Sortie 2), absente des routeurs qui n'en ont qu'une : l'entité
n'est créée que si la clé existe.
"""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import SmartPVRouterError
from .const import DOMAIN
from .coordinator import SmartPVRouterConfigEntry
from .entity import SmartPVRouterEntity

TIMES: tuple[TimeEntityDescription, ...] = tuple(
    TimeEntityDescription(key=key, translation_key=translation_key, entity_category=EntityCategory.CONFIG)
    for key, translation_key in (
        ("NIGHTTIME", "time_slot_1_start"),
        ("DAYTIME", "time_slot_1_end"),
        ("NIGHTTIME2", "time_slot_2_start"),
        ("DAYTIME2", "time_slot_2_end"),
    )
)


def _parse(value: object) -> time | None:
    """« hh:mm » (ou « h:m ») → heure ; None si illisible."""
    if not isinstance(value, str):
        return None
    parts = value.strip().split(":")
    try:
        return time(int(parts[0]) % 24, int(parts[1]) % 60)
    except (IndexError, ValueError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPVRouterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Créer les heures dont la clé existe (firmware avec API ≥ 2)."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartPVRouterTime(coordinator, description)
        for description in TIMES
        if description.key in coordinator.data
    )


class SmartPVRouterTime(SmartPVRouterEntity, TimeEntity):
    """Début ou fin d'une plage horaire."""

    def __init__(self, coordinator, description: TimeEntityDescription) -> None:
        """Créer l'heure."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> time | None:
        """Heure relue dans le routeur."""
        return _parse(self.coordinator.data.get(self.entity_description.key))

    async def async_set_value(self, value: time) -> None:
        """Régler l'heure (enregistrée par le routeur)."""
        try:
            await self.coordinator.api.async_command(
                self.entity_description.key, f"{value.hour:02d}:{value.minute:02d}"
            )
        except SmartPVRouterError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
        # Le routeur ignore sans erreur une valeur refusée : on affiche la valeur relue.
        self.coordinator.async_refresh_settings_soon()
        await self.coordinator.async_request_refresh()
