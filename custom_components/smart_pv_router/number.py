"""Consigne de nuit, durée du Boost et gradation manuelle des sorties."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import SmartPVRouterError
from .const import DOMAIN
from .coordinator import SmartPVRouterConfigEntry
from .entity import SmartPVRouterEntity, to_float


@dataclass(frozen=True, kw_only=True)
class SmartPVRouterNumberDescription(NumberEntityDescription):
    """Réglage lu dans /getjson (clé `read_key`) et envoyé par /get?`key`=N."""

    read_key: str


SETTINGS: tuple[SmartPVRouterNumberDescription, ...] = (
    # Consigne de nuit : lue dans REF_T, réglée par /get?TEMP_NIGHT=N (le firmware accepte
    # 0 <= N < 100). Option D18B20 du firmware.
    SmartPVRouterNumberDescription(
        key="TEMP_NIGHT",
        read_key="REF_T",
        translation_key="night_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=99,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    # Durée du Boost, en minutes : lue dans BOOSTTIME (firmwares avec la clé « API »), réglée
    # par /get?BOOSTTIME=N. Le firmware accepte N >= 1, sans maximum : la limite de 24 h est
    # celle de ce réglage, pas celle du routeur.
    SmartPVRouterNumberDescription(
        key="BOOSTTIME",
        read_key="BOOSTTIME",
        translation_key="boost_duration",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=1,
        native_max_value=1440,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)

# Gradation manuelle (mode 4) : POST /rest/api {"DIMMERn": 0..100}. Les firmwares avec la clé
# « API » renvoient la consigne dans /getjson ; les plus anciens non, et l'entité affiche
# alors la dernière valeur envoyée. Désactivées par défaut, utiles par exemple à Solar
# Optimizer.
DIMMERS: tuple[NumberEntityDescription, ...] = tuple(
    NumberEntityDescription(
        key=key,
        translation_key=translation_key,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_registry_enabled_default=False,
    )
    for key, translation_key in (
        ("DIMMER1", "manual_dimmer_1"),
        ("DIMMER2", "manual_dimmer_2"),
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPVRouterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Créer les réglages numériques.

    Gradation manuelle : un firmware avec la clé « API » n'envoie DIMMER1 / DIMMER2 que si
    l'option existe ; un firmware plus ancien ne dit rien, on crée donc les deux.
    """
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = [
        SmartPVRouterSetting(coordinator, description)
        for description in SETTINGS
        if description.read_key in coordinator.data
    ]
    entities.extend(
        SmartPVRouterDimmerNumber(coordinator, description)
        for description in DIMMERS
        if coordinator.api_version == 0 or description.key in coordinator.data
    )
    async_add_entities(entities)


class SmartPVRouterSetting(SmartPVRouterEntity, NumberEntity):
    """Consigne de nuit ou durée du Boost."""

    entity_description: SmartPVRouterNumberDescription

    def __init__(self, coordinator, description: SmartPVRouterNumberDescription) -> None:
        """Créer le réglage."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Valeur actuelle, lue dans /getjson."""
        return to_float(self.coordinator.data.get(self.entity_description.read_key))

    async def async_set_native_value(self, value: float) -> None:
        """Changer le réglage."""
        try:
            await self.coordinator.api.async_command(self.entity_description.key, f"{value:g}")
        except SmartPVRouterError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
        await self.coordinator.async_request_refresh()


class SmartPVRouterDimmerNumber(SmartPVRouterEntity, RestoreNumber):
    """Gradation manuelle d'une sortie, en %."""

    def __init__(self, coordinator, description: NumberEntityDescription) -> None:
        """Créer le réglage."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._last_value: float | None = None

    async def async_added_to_hass(self) -> None:
        """Reprendre la dernière valeur envoyée."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) is not None:
            self._last_value = last.native_value

    @property
    def native_value(self) -> float | None:
        """Valeur du routeur si le firmware la donne, sinon la dernière envoyée."""
        value = to_float(self.coordinator.data.get(self.entity_description.key))
        return value if value is not None else self._last_value

    async def async_set_native_value(self, value: float) -> None:
        """Envoyer la consigne de gradation."""
        try:
            await self.coordinator.api.async_rest({self.entity_description.key: value})
        except SmartPVRouterError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
        self._last_value = value
        self.async_write_ha_state()
        if self.entity_description.key in self.coordinator.data:
            await self.coordinator.async_request_refresh()
