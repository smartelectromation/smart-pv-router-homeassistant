"""Ajout du Smart PV-Router : découverte zeroconf ou saisie de l'adresse."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import SmartPVRouterApi, SmartPVRouterError
from .const import (
    CONF_GRAFANA_URL,
    CONF_OUTPUT_2_NAME,
    CONF_OUTPUT_2_TYPE,
    DEFAULT_HOST,
    DEFAULT_OUTPUT_2_TYPE,
    DEVICE_NAME,
    DOMAIN,
    LOGGER,
    OUTPUT_2_TYPES,
    ROUTER_MODEL,
    ZEROCONF_MAC_PREFIX,
    ZEROCONF_MAC_PROPERTY,
    default_grafana_url,
)


class NotRouterError(Exception):
    """L'appareil répond, mais ce n'est pas un routeur (MODEL différent de ROUTER)."""


def _mac_from_hex(value: Any) -> str | None:
    """Adresse MAC au format Home Assistant à partir de 12 caractères hexadécimaux."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.upper().startswith(ZEROCONF_MAC_PREFIX):
        value = value[len(ZEROCONF_MAC_PREFIX) :]
    if len(value) != 12:
        return None
    try:
        int(value, 16)
    except ValueError:
        return None
    return format_mac(value)


# Options : charge branchée sur la Sortie 2 (icône et nom sur la carte et dans l'application).
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OUTPUT_2_TYPE, default=DEFAULT_OUTPUT_2_TYPE): SelectSelector(
            SelectSelectorConfig(
                options=list(OUTPUT_2_TYPES),
                translation_key=CONF_OUTPUT_2_TYPE,
                mode=SelectSelectorMode.LIST,
            )
        ),
        vol.Optional(CONF_OUTPUT_2_NAME): TextSelector(),
        vol.Optional(CONF_GRAFANA_URL): TextSelector(),
    }
)


class SmartPVRouterOptionsFlow(OptionsFlow):
    """Réglages de l'intégration : charge de la Sortie 2."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choisir le type et, si besoin, le nom de la charge de la Sortie 2."""
        if user_input is not None:
            name = (user_input.get(CONF_OUTPUT_2_NAME) or "").strip()
            grafana = (user_input.get(CONF_GRAFANA_URL) or "").strip()
            return self.async_create_entry(
                data={
                    CONF_OUTPUT_2_TYPE: user_input[CONF_OUTPUT_2_TYPE],
                    CONF_OUTPUT_2_NAME: name,
                    CONF_GRAFANA_URL: grafana,
                }
            )
        # Adresse du suivi graphique proposée d'après l'adresse MAC, tant qu'aucune n'est saisie.
        suggested = {
            CONF_GRAFANA_URL: default_grafana_url(self.config_entry.unique_id),
            **{key: value for key, value in self.config_entry.options.items() if value != ""},
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, suggested),
        )


class SmartPVRouterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Assistant d'ajout du Smart PV-Router."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SmartPVRouterOptionsFlow:
        """Réglages de l'intégration (Configurer)."""
        return SmartPVRouterOptionsFlow()

    def __init__(self) -> None:
        """Préparer l'assistant."""
        self._host: str | None = None

    async def _async_check_router(self, host: str) -> dict[str, Any]:
        """Lire /getjson et vérifier qu'il s'agit d'un routeur."""
        api = SmartPVRouterApi(async_get_clientsession(self.hass), host)
        data = await api.async_get_json()
        if data.get("MODEL") != ROUTER_MODEL:
            raise NotRouterError
        return data

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Saisie de l'adresse du routeur."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            self._async_abort_entries_match({CONF_HOST: host})
            try:
                data = await self._async_check_router(host)
            except SmartPVRouterError:
                errors["base"] = "cannot_connect"
            except NotRouterError:
                errors["base"] = "not_router"
            except Exception:
                LOGGER.exception("Erreur inattendue")
                errors["base"] = "unknown"
            else:
                # Clé "MAC" de /getjson, absente des anciens firmwares : l'entrée reste alors
                # sans identifiant unique, jusqu'à ce que la découverte automatique le donne.
                mac = _mac_from_hex(data.get("MAC"))
                if mac:
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(title=DEVICE_NAME, data={CONF_HOST: host})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=(user_input or {}).get(CONF_HOST, DEFAULT_HOST),
                    ): str
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Routeur trouvé par son annonce mDNS (propriété pvr-mac)."""
        mac = _mac_from_hex(discovery_info.properties.get(ZEROCONF_MAC_PROPERTY))
        if mac is None:
            return self.async_abort(reason="not_router")
        host = discovery_info.host

        # Routeur déjà ajouté à la main, sans adresse MAC : on le reconnaît à son adresse
        # (IP ou pvrouter.local) et on lui attribue l'adresse MAC.
        hostnames = {host, discovery_info.hostname.rstrip(".")}
        for entry in self._async_current_entries(include_ignore=False):
            if entry.unique_id is None and entry.data.get(CONF_HOST) in hostnames:
                self.hass.config_entries.async_update_entry(entry, unique_id=mac)
                return self.async_abort(reason="already_configured")

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        try:
            await self._async_check_router(host)
        except SmartPVRouterError:
            return self.async_abort(reason="cannot_connect")
        except NotRouterError:
            return self.async_abort(reason="not_router")

        self._host = host
        self.context["title_placeholders"] = {"host": host}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirmation de l'ajout du routeur découvert."""
        assert self._host is not None
        if user_input is not None:
            return self.async_create_entry(title=DEVICE_NAME, data={CONF_HOST: self._host})
        self._set_confirm_only()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"host": self._host},
        )
