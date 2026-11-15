"""Calibration de la Sortie 2 et redémarrage du routeur."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import SmartPVRouterConnectionError, SmartPVRouterError
from .const import DOMAIN, LOGGER
from .coordinator import SmartPVRouterConfigEntry
from .entity import SmartPVRouterEntity


@dataclass(frozen=True, kw_only=True)
class SmartPVRouterButtonDescription(ButtonEntityDescription):
    """Bouton : /get?`key`=1."""

    restarts: bool = False


BUTTONS: tuple[SmartPVRouterButtonDescription, ...] = (
    # La calibration coupe les deux sorties, met la Sortie 2 en marche à pleine puissance le temps
    # de la mesure, puis remplace la puissance enregistrée de sa charge. Lancée quand la charge
    # est coupée par son thermostat, elle enregistre une valeur fausse : désactivée par défaut.
    SmartPVRouterButtonDescription(
        key="CALIBRATE2",
        translation_key="calibrate_output_2",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    # Le redémarrage remet à zéro les compteurs du jour non enregistrés : désactivé par défaut.
    SmartPVRouterButtonDescription(
        key="RESET",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        restarts=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartPVRouterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Créer les boutons."""
    coordinator = entry.runtime_data
    async_add_entities(SmartPVRouterButton(coordinator, description) for description in BUTTONS)


class SmartPVRouterButton(SmartPVRouterEntity, ButtonEntity):
    """Bouton du Smart PV-Router."""

    entity_description: SmartPVRouterButtonDescription

    def __init__(self, coordinator, description: SmartPVRouterButtonDescription) -> None:
        """Créer le bouton."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Envoyer la commande."""
        try:
            await self.coordinator.api.async_command(self.entity_description.key, "1")
        except SmartPVRouterConnectionError as err:
            # Le routeur redémarre sans répondre (ESP.restart() dans le gestionnaire /get).
            if not self.entity_description.restarts:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="command_failed"
                ) from err
            LOGGER.debug("Redémarrage demandé, pas de réponse du routeur : %s", err)
        except SmartPVRouterError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
