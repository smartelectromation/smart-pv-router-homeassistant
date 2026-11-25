"""Capteurs binaires du Smart PV-Router (clés de /getjson)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SmartPVRouterConfigEntry
from .entity import SmartPVRouterEntity, to_bool

BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="STATUS_OUT1",
        translation_key="output_1_active",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BinarySensorEntityDescription(
        key="STATUS_OUT2",
        translation_key="output_2_active",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BinarySensorEntityDescription(
        key="LOAD1_SATURED",
        translation_key="output_1_saturated",
    ),
    BinarySensorEntityDescription(
        key="LOAD2_SATURED",
        translation_key="output_2_saturated",
    ),
    BinarySensorEntityDescription(
        key="NIGHT",
        translation_key="night_period",
    ),
    BinarySensorEntityDescription(
        key="BACT",
        translation_key="anti_bacteria_cycle",
    ),
    # Batterie externe lue par le routeur : elle lui répond. Sinon, sa puissance et son niveau
    # sont « inconnus ».
    BinarySensorEntityDescription(
        key="HIBAT_OK",
        translation_key="battery_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="MQTT",
        translation_key="mqtt_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPVRouterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Créer les capteurs binaires dont la clé existe."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartPVRouterBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
        if description.key in coordinator.data
    )


class SmartPVRouterBinarySensor(SmartPVRouterEntity, BinarySensorEntity):
    """Capteur binaire du Smart PV-Router."""

    def __init__(self, coordinator, description: BinarySensorEntityDescription) -> None:
        """Créer le capteur binaire."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """État lu dans /getjson."""
        return to_bool(self.coordinator.data.get(self.entity_description.key))
