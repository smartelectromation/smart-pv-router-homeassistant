"""Carte « Smart PV-Router » pour les tableaux de bord.

L'intégration sert le dossier www/ (script de la carte, photo du routeur), charge le script
dans l'interface de Home Assistant et répond à la carte, par le websocket, avec la liste des
routeurs et de leurs entités. La carte n'adresse jamais le routeur directement : elle lit les
entités et commande par les services de Home Assistant.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.frontend import add_extra_js_url, async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import (
    CARD_FILE,
    CONF_GRAFANA_URL,
    CONF_OUTPUT_2_NAME,
    CONF_OUTPUT_2_TYPE,
    DEFAULT_OUTPUT_2_TYPE,
    OUTPUT_2_TYPES,
    CARD_URL_BASE,
    CARD_VERSION,
    DOMAIN,
    LOGGER,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL,
    default_grafana_url,
)

WWW_DIR = Path(__file__).parent / "www"


def _card_url() -> str:
    """Adresse du script, avec la version et l'empreinte du fichier.

    Le navigateur recharge ainsi la carte dès que le fichier change, même sans changement de
    version (sinon il peut garder l'ancien script en cache et afficher une page blanche).
    """
    try:
        digest = hashlib.sha1((WWW_DIR / CARD_FILE).read_bytes()).hexdigest()[:8]
    except OSError:
        digest = "0"
    return f"{CARD_URL_BASE}/{CARD_FILE}?v={CARD_VERSION}-{digest}"


# Calculé à l'import du module (fait hors de la boucle d'événements par Home Assistant).
CARD_URL = _card_url()


async def async_register_card(hass: HomeAssistant) -> None:
    """Servir les fichiers de la carte, la charger dans l'interface, ouvrir le websocket.

    Appelé une seule fois par démarrage de Home Assistant (async_setup de l'intégration).
    """
    websocket_api.async_register_command(hass, websocket_routers)
    websocket_api.async_register_command(hass, websocket_set_output_2)
    if hass.http is None:  # Home Assistant sans serveur web (tests)
        LOGGER.debug("Pas de serveur web : carte non servie")
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_BASE, str(WWW_DIR), cache_headers=False)]
    )
    add_extra_js_url(hass, CARD_URL)


async def async_add_panel(hass: HomeAssistant) -> None:
    """Ajouter « Smart PV-Router » à la barre latérale (la carte en pleine page).

    Rien à faire pour l'utilisateur : l'entrée apparaît dès qu'un routeur est configuré. Elle
    peut être masquée comme toute autre entrée (profil > barre latérale).
    """
    if hass.http is None or PANEL_URL in hass.data.get("frontend_panels", {}):
        return
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=CARD_URL,
        require_admin=False,
    )


@callback
def async_remove_panel_if_unused(hass: HomeAssistant) -> None:
    """Retirer l'entrée de la barre latérale quand plus aucun routeur n'est chargé."""
    if any(
        entry.state is ConfigEntryState.LOADED
        for entry in hass.config_entries.async_entries(DOMAIN)
    ):
        return
    async_remove_panel(hass, PANEL_URL)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/routers"})
@callback
def websocket_routers(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Routeurs chargés et leurs entités, repérées par la clé de /getjson.

    Exemple : {"routers": [{"device_id": "…", "name": "Smart PV-Router",
    "entities": {"PIN": "sensor.…", "Out1_mode": "select.…", …}}]}
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    routers = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is not ConfigEntryState.LOADED:
            continue
        device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
        prefix = f"{entry.entry_id}_"
        entities = {
            reg.unique_id.removeprefix(prefix): reg.entity_id
            for reg in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
            if reg.unique_id.startswith(prefix) and reg.disabled_by is None
        }
        output_2_type = entry.options.get(CONF_OUTPUT_2_TYPE, DEFAULT_OUTPUT_2_TYPE)
        if output_2_type not in OUTPUT_2_TYPES:
            output_2_type = DEFAULT_OUTPUT_2_TYPE
        routers.append(
            {
                "entry_id": entry.entry_id,
                "device_id": device.id if device else None,
                "name": (device.name_by_user or device.name) if device else entry.title,
                "entities": entities,
                "output_2": {
                    "type": output_2_type,
                    "icon": OUTPUT_2_TYPES[output_2_type],
                    "name": entry.options.get(CONF_OUTPUT_2_NAME, ""),
                },
                "output_2_types": OUTPUT_2_TYPES,
                # Suivi graphique : adresse saisie dans les options, sinon celle du routeur.
                "grafana_url": entry.options.get(CONF_GRAFANA_URL)
                or default_grafana_url(entry.unique_id),
            }
        )
    connection.send_result(msg["id"], {"routers": routers})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/set_output_2",
        vol.Required("entry_id"): str,
        vol.Required("output_2_type"): vol.In(list(OUTPUT_2_TYPES)),
        vol.Optional("output_2_name"): str,
    }
)
@callback
def websocket_set_output_2(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Changer la charge de la Sortie 2 depuis la carte (administrateurs seulement).

    Même réglage que les options de l'intégration (Configurer).
    """
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "not_found", "Smart PV-Router introuvable")
        return
    options = {**entry.options, CONF_OUTPUT_2_TYPE: msg["output_2_type"]}
    if "output_2_name" in msg:
        options[CONF_OUTPUT_2_NAME] = msg["output_2_name"].strip()
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(msg["id"])
