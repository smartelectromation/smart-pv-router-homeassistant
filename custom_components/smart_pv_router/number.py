"""Consigne de nuit, durée du Boost et modulation manuelle des sorties."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
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
    # Réglages lus dans /getparams?pwd=0 (firmware avec API ≥ 2). Le routeur ignore sans erreur une
    # valeur hors bornes : l'entité affiche toujours la valeur relue après le réglage.
    # Seuil Auto (%) : 0 à 100.
    SmartPVRouterNumberDescription(
        key="THPERCENTAGE",
        read_key="THPERCENTAGE",
        translation_key="auto_threshold",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    # Délestage, puissance MAX (VA) : entier > 0 ; plafond 12 000 ou 30 000 VA selon le firmware
    # (au-delà, le routeur ramène au plafond).
    SmartPVRouterNumberDescription(
        key="OVERLOAD",
        read_key="OVERLOAD",
        translation_key="load_shedding_power",
        device_class=NumberDeviceClass.APPARENT_POWER,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        native_min_value=1,
        native_max_value=30000,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    # Cible Modul (W) : −9999 à +9999 (négatif autorisé). Réglable seulement avec l'option
    # gradateur du firmware.
    SmartPVRouterNumberDescription(
        key="THDIMMER",
        read_key="THDIMMER",
        translation_key="dimmer_target",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=-9999,
        native_max_value=9999,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)

# Modulation manuelle (mode 4) : POST /rest/api {"DIMMERn": 0..100}. Les firmwares avec la clé
# « API » renvoient la consigne dans /getjson ; les plus anciens non, et l'entité affiche
# alors la dernière valeur envoyée. Activées par défaut quand le firmware annonce l'option
# (la carte en fait un curseur sous la sortie en mode 4) ; désactivées avec un firmware plus
# ancien, qui ne dit pas si l'option existe. Utiles aussi à Solar Optimizer.
DIMMERS: tuple[NumberEntityDescription, ...] = tuple(
    NumberEntityDescription(
        key=key,
        translation_key=translation_key,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=0.1,  # le firmware accepte une consigne décimale (ex. 54,7 %)
        mode=NumberMode.SLIDER,
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

    Modulation manuelle : un firmware avec la clé « API » n'envoie DIMMER1 / DIMMER2 que si
    l'option existe ; un firmware plus ancien ne dit rien, on crée donc les deux.
    """
    coordinator = entry.runtime_data
    if coordinator.api_version > 0:
        _enable_dimmers(hass, entry, coordinator.data)
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


@callback
def _enable_dimmers(
    hass: HomeAssistant, entry: SmartPVRouterConfigEntry, data: dict[str, Any]
) -> None:
    """Réactiver les modulations manuelles désactivées par une version précédente (≤ 0.3.0).

    Seules celles que l'intégration avait désactivées d'office : une entité désactivée par
    l'utilisateur le reste.
    """
    registry = er.async_get(hass)
    for description in DIMMERS:
        if description.key not in data:
            continue
        entity_id = registry.async_get_entity_id(
            "number", DOMAIN, f"{entry.entry_id}_{description.key}"
        )
        reg = registry.async_get(entity_id) if entity_id else None
        if reg and reg.disabled_by is er.RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(reg.entity_id, disabled_by=None)


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
        self.coordinator.async_refresh_settings_soon()
        await self.coordinator.async_request_refresh()


class SmartPVRouterDimmerNumber(SmartPVRouterEntity, RestoreNumber):
    """Modulation manuelle d'une sortie, en %."""

    def __init__(self, coordinator, description: NumberEntityDescription) -> None:
        """Créer le réglage."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_entity_registry_enabled_default = coordinator.api_version > 0
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
        """Envoyer la consigne de modulation."""
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
