"""Constantes de l'intégration Smart PV-Router by Smart Electromation Technology."""

from __future__ import annotations

from datetime import timedelta
import logging

DOMAIN = "smart_pv_router"
LOGGER = logging.getLogger(__package__)

# Pas plus d'une lecture de /getjson toutes les 5 s (limite fixée par le fabricant).
SCAN_INTERVAL = timedelta(seconds=5)

DEFAULT_HOST = "pvrouter.local"

# Carte « Smart PV-Router » : fichiers du dossier www/, servis sous cette adresse. La version
# (celle du manifest) est ajoutée à l'adresse du script pour que le navigateur recharge la
# carte après une mise à jour.
CARD_URL_BASE = "/smart_pv_router_card"
CARD_FILE = "smart-pv-router-card.js"
CARD_VERSION = "0.3.0"

# Charge branchée sur la Sortie 2 (options de l'intégration, comme dans l'application mobile) :
# type → icône. Le nom affiché est celui du type, sauf si l'utilisateur en saisit un.
CONF_OUTPUT_2_TYPE = "output_2_type"
CONF_OUTPUT_2_NAME = "output_2_name"
DEFAULT_OUTPUT_2_TYPE = "other"
OUTPUT_2_TYPES: dict[str, str] = {
    "other": "mdi:flash",
    "radiator": "mdi:radiator",
    "pool": "mdi:pool",
    "hot_tub": "mdi:hot-tub",
    "ev": "mdi:car-electric",
    "heat_pump": "mdi:heat-pump",
    "water_heater": "mdi:water-boiler",
    "air_conditioner": "mdi:air-conditioner",
    "socket": "mdi:power-socket-fr",
}

# Suivi graphique (tableau de bord Grafana de Smart Electromation Technology) : un tableau de bord
# par routeur, nommé d'après son adresse MAC. Modifiable dans les options (autre adresse ou vide).
CONF_GRAFANA_URL = "grafana_url"
GRAFANA_URL_TEMPLATE = "http://pvrouter.smartelectromation.com:49999/d/PVR-{mac}-R"


def default_grafana_url(mac: str | None) -> str:
    """Adresse du suivi graphique d'un routeur, d'après son adresse MAC ; vide si inconnue."""
    if not mac:
        return ""
    return GRAFANA_URL_TEMPLATE.format(mac=mac.replace(":", "").upper())


# Entrée « Smart PV-Router » de la barre latérale : la carte en pleine page, ajoutée dès qu'un
# routeur est configuré. Le tiret bas évite tout conflit avec un tableau de bord créé par
# l'utilisateur (leurs adresses contiennent un tiret).
PANEL_URL = "smart_pv_router"
PANEL_ELEMENT = "smart-pv-router-panel"
PANEL_TITLE = "Smart PV-Router"
PANEL_ICON = "mdi:solar-power-variant"

MANUFACTURER = "Smart Electromation Technology"
MODEL = "Smart PV-Router"
DEVICE_NAME = "Smart PV-Router"

# Valeur de la clé MODEL de /getjson pour un routeur (METER pour un compteur).
ROUTER_MODEL = "ROUTER"

# Version d'API (clé « API » de /getjson) à partir de laquelle /get?BOOST=ON|OFF,
# /get?ECOMAX=ON|OFF et /get?DISPLAY=ON|OFF fixent l'état. Sans cette clé, BOOST et ECOMAX
# inversent l'état à chaque commande.
API_ON_OFF_COMMANDS = 1

# Version d'API à partir de laquelle /getparams?pwd=0 répond SANS les identifiants MQTT. Un firmware
# plus ancien ignore le paramètre et renvoie le mot de passe : /getparams n'est jamais lue avant.
API_SETTINGS = 2

# Réglages lus dans /getparams?pwd=0 (seules ces clés sont gardées), relus toutes les 60 s et après
# chaque changement. Les clés présentes dépendent des options du firmware.
SETTINGS_KEYS = (
    "THPERCENTAGE",
    "OVERLOAD",
    "THDIMMER",
    "NIGHTTIME",
    "DAYTIME",
    "NIGHTTIME2",
    "DAYTIME2",
    "NIGHT_OUT2",
)
SETTINGS_INTERVAL_S = 60

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
