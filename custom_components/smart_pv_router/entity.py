"""Entité de base et conversions des valeurs de /getjson."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL
from .coordinator import SmartPVRouterCoordinator


def to_float(value: Any) -> float | None:
    """Nombre ou texte numérique ("1.234", "-67") ; None si vide ou illisible."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> int | None:
    """Entier, ou None."""
    number = to_float(value)
    return None if number is None else int(number)


def to_bool(value: Any) -> bool | None:
    """Booléen JSON, 0/1 ou texte ; None si absent."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "on")
    return None


class SmartPVRouterEntity(CoordinatorEntity[SmartPVRouterCoordinator]):
    """Entité rattachée au Smart PV-Router."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartPVRouterCoordinator, key: str) -> None:
        """Rattacher l'entité à l'appareil.

        Les identifiants reposent sur l'entrée de configuration, qui ne change pas même si
        l'adresse MAC n'est connue que plus tard (routeur ajouté à la main).
        """
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        connections: set[tuple[str, str]] = set()
        if entry.unique_id:
            connections.add((CONNECTION_NETWORK_MAC, entry.unique_id))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            connections=connections,
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=DEVICE_NAME,
            sw_version=coordinator.data.get("Version"),
            configuration_url=coordinator.api.base_url,
        )
