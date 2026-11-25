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


def _split_outputs(data: dict[str, Any]) -> tuple[float, float]:
    """Part de chaque sortie dans POUT, mesure commune aux deux sorties.

    Même règle que le pont MQTT → InfluxDB de SET (POUT1 / POUT2) et que l'application mobile :
    la Sortie 1 prend jusqu'à sa charge LOAD1, le reste va à la Sortie 2 ; une Sortie 1 saturée
    (chauffe-eau chaud) ne consomme rien ; la Sortie 2 ne compte que relais fermé (STATUS_OUT2).
    Une charge inconnue (LOAD ≤ 0, pendant la calibration) prend toute la mesure.
    """
    pout = max(to_float(data.get("POUT")) or 0.0, 0.0)
    load1 = to_float(data.get("LOAD1")) or 0.0
    load2 = to_float(data.get("LOAD2")) or 0.0
    if not to_bool(data.get("LOAD1_SATURED")):
        out1 = load1 if 0 < load1 < pout else pout
        out2 = pout - out1
    else:
        out1 = 0.0
        out2 = 0.0 if to_bool(data.get("LOAD2_SATURED")) else (load2 if 0 < load2 < pout else pout)
    if not to_bool(data.get("STATUS_OUT2")):
        out2 = 0.0
    return out1, out2


def _has_battery(data: dict[str, Any]) -> bool:
    """Le firmware annonce une batterie : mesurée par le routeur (BATT) ou externe (HIBAT_OK)."""
    return "BATT" in data or "HIBAT_OK" in data


def _battery_power(data: dict[str, Any]) -> float | None:
    """Puissance de la batterie, > 0 en charge et < 0 en décharge (convention de BATT).

    Batterie externe lue par le routeur (clés HIBAT_*) : HIBAT_P est NÉGATIVE en charge, donc
    inversée ici, et ne vaut que si HIBAT_OK ; sinon la batterie ne répond plus au routeur et la
    puissance est inconnue. Sans ces clés : BATT, batterie mesurée par le routeur.
    """
    if "HIBAT_OK" in data:
        if not to_bool(data.get("HIBAT_OK")):
            return None
        power = to_float(data.get("HIBAT_P"))
        return None if power is None else 0.0 - power  # 0.0 - x : jamais « -0 »
    return to_float(data.get("BATT"))


def _battery_level(data: dict[str, Any]) -> StateType:
    """Niveau de charge de la batterie externe (HIBAT_SOC, %).

    Le firmware envoie 0 quand la batterie ne répond plus : « inconnu » plutôt qu'un faux 0 %.
    """
    if not to_bool(data.get("HIBAT_OK")):
        return None
    level = to_float(data.get("HIBAT_SOC"))
    return None if level is None else min(max(level, 0.0), 100.0)


def _house_power(data: dict[str, Any]) -> StateType:
    """Maison hors chauffe-eau, Sortie 2 et borne VE (même calcul que l'application mobile).

    Consommation = production + réseau (+ soutiré / − injecté) − charge de la batterie (> 0 en
    charge, voir _battery_power), ou réseau seul sans mesure de production.
    """
    grid = to_float(data.get("PIN"))
    if grid is None:
        return None
    if "PROD" in data:
        battery = _battery_power(data) or 0.0
        consumption = max((to_float(data.get("PROD")) or 0.0) + grid - battery, 0.0)
    else:
        consumption = max(grid, 0.0)
    out1, out2 = _split_outputs(data)
    return round(max(consumption - out1 - out2 - (to_float(data.get("EVPOWER")) or 0.0), 0.0))


def _router_time(data: dict[str, Any]) -> StateType:
    """Heure du routeur toujours sur deux chiffres : « 9:5 » devient « 09:05 »."""
    raw = data.get("TIME")
    if not isinstance(raw, str) or not raw.strip():
        return None
    parts = raw.strip().split(":")
    try:
        hours, minutes = int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        return raw.strip()
    return f"{hours:02d}:{minutes:02d}"


# CAR_MODE (firmware avec borne) : 0 débranchée, 1 branchée sans charge, 2 en charge,
# 3 ventilation, 4 inconnu. Clé absente si la borne ne communique plus depuis 3 min.
CAR_MODES = {0: "unplugged", 1: "plugged", 2: "charging", 3: "ventilation", 4: "unknown"}


def _car_mode(data: dict[str, Any]) -> StateType:
    code = to_int(data.get("CAR_MODE"))
    return None if code is None else CAR_MODES.get(code)


def _water_heater_temperature(data: dict[str, Any]) -> StateType:
    """TEMP1 vaut 0 (ou −127) sans sonde : « inconnu » plutôt qu'une fausse mesure à 0 °C."""
    value = to_float(data.get("TEMP1"))
    return None if value is None or value in (0, -127) else value


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
    # Clé BATT gardée pour l'entité (identifiant, carte), que la batterie soit mesurée par le
    # routeur (BATT) ou externe (HIBAT_P, signe inversé).
    _power("BATT", "battery_power", value_fn=_battery_power, exists_fn=_has_battery),
    _power("EVPOWER", "ev_charger_power"),
    _power(
        "POUT1",
        "output_1_power",
        value_fn=lambda data: round(_split_outputs(data)[0]),
        exists_fn=lambda data: "POUT" in data,
    ),
    _power(
        "POUT2",
        "output_2_power",
        value_fn=lambda data: round(_split_outputs(data)[1]),
        exists_fn=lambda data: "POUT" in data,
    ),
    _power(
        "HOUSE",
        "house_power",
        value_fn=_house_power,
        exists_fn=lambda data: "PIN" in data and "POUT" in data,
    ),
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
    _temperature("TEMP1", "water_heater_temperature", value_fn=_water_heater_temperature),
    _temperature("TEMP2", "probe_2_temperature"),
    # Niveau de charge de la batterie externe lue par le routeur
    SmartPVRouterSensorDescription(
        key="HIBAT_SOC",
        translation_key="battery_level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value_fn=_battery_level,
        exists_fn=lambda data: "HIBAT_OK" in data,
    ),
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
    # État de la voiture, donné par la borne (firmware avec borne)
    SmartPVRouterSensorDescription(
        key="CAR_MODE",
        translation_key="car_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(CAR_MODES.values()),
        value_fn=_car_mode,
    ),
    # Heure du routeur (« HH:MM », texte) : vérifie que son horloge est juste (heures creuses,
    # remise à zéro des compteurs à 6 h).
    SmartPVRouterSensorDescription(
        key="TIME",
        translation_key="router_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_router_time,
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
