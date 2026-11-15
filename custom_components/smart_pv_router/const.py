"""Constantes de l'intégration Smart PV-Router by Smart Electromation Technology."""

from __future__ import annotations

from datetime import timedelta
import logging

DOMAIN = "smart_pv_router"
LOGGER = logging.getLogger(__package__)

# Pas plus d'une lecture de /getjson toutes les 5 s (limite fixée par le fabricant).
SCAN_INTERVAL = timedelta(seconds=5)

DEFAULT_HOST = "pvrouter.local"

MANUFACTURER = "Smart Electromation Technology"
MODEL = "Smart PV-Router"
DEVICE_NAME = "Smart PV-Router"

# Valeur de la clé MODEL de /getjson pour un routeur (METER pour un compteur).
ROUTER_MODEL = "ROUTER"

# Version d'API (clé « API » de /getjson) à partir de laquelle /get?BOOST=ON|OFF,
# /get?ECOMAX=ON|OFF et /get?DISPLAY=ON|OFF fixent l'état. Sans cette clé, BOOST et ECOMAX
# inversent l'état à chaque commande.
API_ON_OFF_COMMANDS = 1

# Propriété TXT mDNS annoncée par le firmware : "PVR-" + 12 caractères hexadécimaux.
ZEROCONF_MAC_PROPERTY = "pvr-mac"
ZEROCONF_MAC_PREFIX = "PVR-"

# Modes des sorties (settings.h : MODE_STOP ... MODE_D_MANUAL). Le mode 9 (Test) n'est
# pas proposé.
OUTPUT_MODES: dict[str, int] = {
    "stop": 0,
    "auto": 1,
    "forced": 2,
    "dimmer": 3,
    "manual_dimmer": 4,
}
