"""Capteurs du Smart PV-Router (clés de /getjson)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import SmartPVRouterConfigEntry
from .entity import SmartPVRouterEntity, to_bool, to_float, to_int

# GRID_ERR (settings.h) : 0 pas d'alarme, 1 plus aucune mesure (No GRID), 2 mesure figée.
GRID_ALARMS = {0: "none", 1: "no_measure", 2: "frozen"}


def _boost_remaining(data: dict[str, Any]) -> StateType:
    """BOOSTREM n'existe que pendant un Boost : 0 sinon."""
    if not to_bool(data.get("BOOST")):
        return 0
    return to_int(data.get("BOOSTREM"))


def _grid_alarm(data: dict[str, Any]) -> StateType:
    code = to_int(data.get("GRID_ERR"))
    return None if code is None else GRID_ALARMS.get(code)


@dataclass(frozen=True, kw_only=True)
class SmartPVRouterSensorDescription(SensorEntityDescription):
    """Capteur lu dans /getjson."""

    value_fn: Callable[[dict[str, Any]], StateType] | None = None
    exists_fn: Callable[[dict[str, Any]], bool] | None = None


def _power(key: str, translation_key: str, **kwargs: Any) -> SmartPVRouterSensorDescription:
    return SmartPVRouterSensorDescription(
        key=key,
        translation_key=translation_key,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        **kwargs,
    )


def _energy(key: str, translation_key: str) -> SmartPVRouterSensorDescription:
    # Compteurs du jour en kWh, remis à zéro à 06:00 (et au redémarrage pour INJECT,
    # TOT_PROD et TOT_S) : total_increasing traite chaque baisse comme un nouveau cycle.
    return SmartPVRouterSensorDescription(
        key=key,
        translation_key=translation_key,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    )


def _temperature(key: str, translation_key: str, **kwargs: Any) -> SmartPVRouterSensorDescription:
    return SmartPVRouterSensorDescription(
        key=key,
        translation_key=translation_key,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        **kwargs,
    )


def _percent(key: str, translation_key: str) -> SmartPVRouterSensorDescription:
    return SmartPVRouterSensorDescription(
        key=key,
        translation_key=translation_key,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    )


SENSORS: tuple[SmartPVRouterSensorDescription, ...] = (
    # Puissances
    _power("PIN", "grid_power"),
    _power("INJECT_I", "grid_export_power"),
    _power("PROD", "solar_power"),
    _power("POUT", "diverted_power"),
    _power("BATT", "battery_power"),
    _power("EVPOWER", "ev_charger_power"),
    # Réseau
    SmartPVRouterSensorDescription(
        key="VIN",
        translation_key="grid_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    SmartPVRouterSensorDescription(
        key="CIN",
        translation_key="grid_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    SmartPVRouterSensorDescription(
        key="COUT",
        translation_key="output_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    # Énergies du jour (tableau de bord Énergie)
    _energy("TOT_S", "grid_import_energy"),
    _energy("INJECT", "grid_export_energy"),
    _energy("TOT_PROD", "solar_energy"),
    _energy("TOTAL_POWER", "diverted_energy"),
    _energy("SAVED_POWER", "solar_diverted_energy"),
    # Taux du jour
    _percent("SUFFI", "self_sufficiency"),
    _percent("AUTO_C", "self_consumption"),
    _percent("EFF", "diversion_efficiency"),
    # Températures
    _temperature("TEMP1", "water_heater_temperature"),
    _temperature("TEMP2", "probe_2_temperature"),
    # Boost
    SmartPVRouterSensorDescription(
        key="BOOSTREM",
        translation_key="boost_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=_boost_remaining,
        exists_fn=lambda data: "BOOST" in data,
    ),
    # Diagnostic
    _power("LOAD1", "output_1_load", entity_category=EntityCategory.DIAGNOSTIC),
    _power("LOAD2", "output_2_load", entity_category=EntityCategory.DIAGNOSTIC),
    SmartPVRouterSensorDescription(
        key="GRID_ERR",
        translation_key="grid_alarm",
        device_class=SensorDeviceClass.ENUM,
        options=list(GRID_ALARMS.values()),
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_grid_alarm,
    ),
    SmartPVRouterSensorDescription(
        key="WIFI",
        translation_key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    _temperature(
        "T_RTC",
        "rtc_temperature",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPVRouterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Créer les capteurs dont la clé existe : elles dépendent des options du firmware."""
    coordinator = entry.runtime_data
    data = coordinator.data
    async_add_entities(
        SmartPVRouterSensor(coordinator, description)
        for description in SENSORS
        if (description.exists_fn or (lambda d, k=description.key: k in d))(data)
    )


class SmartPVRouterSensor(SmartPVRouterEntity, SensorEntity):
    """Capteur du Smart PV-Router."""

    entity_description: SmartPVRouterSensorDescription

    def __init__(self, coordinator, description: SmartPVRouterSensorDescription) -> None:
        """Créer le capteur."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Valeur lue dans /getjson."""
        data = self.coordinator.data
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(data)
        return to_float(data.get(self.entity_description.key))
