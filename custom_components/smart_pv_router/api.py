"""Client de l'API HTTP locale du Smart PV-Router.

Adresses utilisées (firmware V12_36 et suivants) :

- ``GET /getjson`` : mesures et états. La clé ``API`` (absente des anciens firmwares) donne
  la version de l'API : voir ``SmartPVRouterCoordinator.api_version`` ;
- ``GET /get?CLE=valeur`` : commandes simples, une seule clé par requête ;
- ``POST /rest/api`` : réglages en JSON. Le routeur répond 503 avec ``Retry-After``
  quand il est occupé, ``{"status": 1}`` si un réglage a été appliqué, ``{"status": 0}``
  sinon.

``/getparams`` n'est jamais lue telle quelle : elle contient le mot de passe MQTT en clair. Avec
``API`` ≥ 2, ``/getparams?pwd=0`` répond sans ``Login`` ni ``Passwd`` ; seules les clés de
``SETTINGS_KEYS`` en sont gardées.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import SETTINGS_KEYS

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)
REST_ATTEMPTS = 3


class SmartPVRouterError(Exception):
    """Erreur de l'API du routeur."""


class SmartPVRouterConnectionError(SmartPVRouterError):
    """Routeur injoignable ou réponse illisible."""


class SmartPVRouterCommandError(SmartPVRouterError):
    """Commande refusée par le routeur."""


class SmartPVRouterApi:
    """Accès à un Smart PV-Router sur le réseau local."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        """Préparer le client pour l'hôte donné (nom ou adresse IP)."""
        self._session = session
        self.host = host
        # Le serveur web du routeur traite mal les requêtes simultanées : une à la fois.
        self._lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        """Adresse de base du routeur."""
        host = self.host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"http://{host}"

    async def async_get_json(self) -> dict[str, Any]:
        """Lire /getjson."""
        async with self._lock:
            try:
                async with self._session.get(
                    f"{self.base_url}/getjson", timeout=REQUEST_TIMEOUT
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                raise SmartPVRouterConnectionError(str(err) or repr(err)) from err
        if not isinstance(data, dict):
            raise SmartPVRouterConnectionError("réponse /getjson inattendue")
        return data

    async def async_get_settings(self) -> dict[str, Any]:
        """Réglages du routeur, lus dans /getparams?pwd=0.

        À n'appeler qu'avec ``API`` ≥ 2 : un firmware plus ancien ignore ``pwd=0`` et renverrait le
        mot de passe MQTT. Par précaution, seules les clés de ``SETTINGS_KEYS`` sont gardées ; le
        reste de la réponse n'est ni conservé ni journalisé.
        """
        async with self._lock:
            try:
                async with self._session.get(
                    f"{self.base_url}/getparams", params={"pwd": "0"}, timeout=REQUEST_TIMEOUT
                ) as resp:
                    resp.raise_for_status()
                    raw = await resp.json(content_type=None)
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                raise SmartPVRouterConnectionError(str(err) or repr(err)) from err
        if not isinstance(raw, dict):
            raise SmartPVRouterConnectionError("réponse /getparams inattendue")
        return {key: raw[key] for key in SETTINGS_KEYS if key in raw}

    async def async_command(self, key: str, value: str) -> str:
        """Envoyer une commande /get?key=value."""
        async with self._lock:
            try:
                async with self._session.get(
                    f"{self.base_url}/get", params={key: value}, timeout=REQUEST_TIMEOUT
                ) as resp:
                    resp.raise_for_status()
                    return await resp.text()
            except (aiohttp.ClientError, TimeoutError) as err:
                raise SmartPVRouterConnectionError(str(err) or repr(err)) from err

    async def async_rest(self, payload: dict[str, Any]) -> None:
        """Envoyer des réglages par POST /rest/api, avec renvoi si le routeur est occupé."""
        async with self._lock:
            for attempt in range(1, REST_ATTEMPTS + 1):
                try:
                    async with self._session.post(
                        f"{self.base_url}/rest/api", json=payload, timeout=REQUEST_TIMEOUT
                    ) as resp:
                        if resp.status == 503 and attempt < REST_ATTEMPTS:
                            delay = _retry_after(resp.headers.get("Retry-After"))
                        else:
                            resp.raise_for_status()
                            result = await resp.json(content_type=None)
                            break
                except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                    raise SmartPVRouterConnectionError(str(err) or repr(err)) from err
                await asyncio.sleep(delay)
        if not isinstance(result, dict) or result.get("status") != 1:
            raise SmartPVRouterCommandError(f"réglage refusé : {payload}")


def _retry_after(value: str | None) -> float:
    """Délai demandé par l'en-tête Retry-After, borné entre 1 et 5 s."""
    try:
        return min(max(float(value or 1), 1.0), 5.0)
    except ValueError:
        return 1.0
