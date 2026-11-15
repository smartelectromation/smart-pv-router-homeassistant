# Smart PV-Router by Smart Electromation Technology pour Home Assistant

[Français](#français) · [English](#english)

## Français

Intégration Home Assistant du **Smart PV-Router by Smart Electromation Technology**, routeur solaire conçu et
fabriqué en France par Smart Electromation Technology. Site officiel :
[smartelectromation.com](https://smartelectromation.com).

Elle lit le routeur sur le réseau local, sans cloud et sans broker MQTT : mesures, énergies du jour
pour le tableau de bord Énergie, modes des Sorties 1 et 2, Boost, et une carte animée de la maison.

Comme elle passe par HTTP, le routeur garde sa liaison MQTT avec le serveur Smart Electromation : le
tableau de bord en ligne (Grafana) et le suivi par smartelectromation.com restent disponibles.

### Prérequis

- Smart PV-Router avec le firmware **V12_36** ou plus récent.
- Home Assistant **2026.3** ou plus récent, sur le même réseau local que le routeur.

### Installation

[![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=smartelectromation&repository=smart-pv-router-homeassistant&category=integration)

1. Cliquez sur le bouton ci-dessus : HACS s'ouvre dans votre Home Assistant, sur cette intégration.
   Cliquez sur **Télécharger**, puis redémarrez Home Assistant (Paramètres > Système > Redémarrer).
2. Le routeur est **découvert tout seul** : Paramètres > Appareils et services > **Configurer**.
3. C'est tout : **« Smart PV-Router » apparaît dans la barre latérale**, avec la maison animée.

Si le routeur n'est pas découvert :

[![Ajouter l'intégration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=smart_pv_router)

puis saisissez `pvrouter.local` ou l'adresse IP du routeur.

<details>
<summary>Sans le bouton : ajout à la main dans HACS</summary>

HACS > menu **⋮** > **Dépôts personnalisés** > adresse
`https://github.com/smartelectromation/smart-pv-router-homeassistant`, catégorie **Intégration**, puis
**Télécharger**.
</details>

<details>
<summary>Sans HACS : installation manuelle</summary>

1. Téléchargez `smart_pv_router.zip` dans la [dernière version](https://github.com/smartelectromation/smart-pv-router-homeassistant/releases/latest).
2. Décompressez-le dans `config/custom_components/smart_pv_router/` (avec le module complémentaire
   Samba ou Studio Code Server), puis redémarrez Home Assistant.

Les mises à jour ne sont alors pas proposées : il faut refaire la copie à chaque version.
</details>

### Entités

| Type | Entités |
|---|---|
| Puissances | réseau (+ soutirée / − injectée), injectée, production solaire, routée, Sortie 1, Sortie 2, maison, batterie, borne VE |
| Énergies du jour (kWh) | soutirée au réseau, injectée au réseau, solaire produite, routée, solaire routée |
| Autres mesures | tension, courants, autoproduction et autoconsommation du jour, rendement du routage, température du ballon, Boost restant |
| États | Sortie 1 / Sortie 2 active, charge saturée, période de nuit, cycle anti-bactéries |
| Commandes | mode de la Sortie 1 et de la Sortie 2 (Arrêt, Automatique, Marche forcée, Gradation, Gradation manuelle), Boost, durée du Boost, EcoMax, consigne de nuit, écran |
| Désactivées par défaut | signal WiFi, température RTC, MQTT connecté, redémarrage, calibration de la Sortie 2, gradation manuelle Sortie 1 / Sortie 2 |

Seules les entités que le firmware fournit sont créées : certaines dépendent des options du routeur
(production, batterie, borne VE, sondes de température, EcoMax). La durée du Boost et l'écran demandent
un firmware qui annonce la version de son API (clé `API` de `/getjson`).

### Carte Smart PV-Router

Elle s'affiche dans la barre latérale (**Smart PV-Router**) dès que le routeur est ajouté. Pour la
mettre aussi dans un de vos tableaux de bord : **Modifier** > **Ajouter une carte** > « Smart PV-Router ».

- Photo de la maison, avec la batterie et la voiture si le routeur les mesure.
- Flux d'énergie animés entre le routeur et le solaire, le réseau, le chauffe-eau, la Sortie 2, la
  batterie et la borne VE ; pastilles avec la puissance de chacun.
- Mode de chaque sortie, EcoMax, Boost et sa durée, directement sur la carte.
- Nom et icône de la Sortie 2 au choix, dans l'éditeur de la carte.

La puissance de chaque sortie est déduite de la puissance routée, mesure commune aux deux sorties : la
Sortie 1 prend jusqu'à la puissance de sa charge, le reste va à la Sortie 2 (même calcul que
l'application et le tableau de bord en ligne).

### Tableau de bord Énergie

| Rubrique | Entité |
|---|---|
| Consommation réseau | Énergie soutirée au réseau |
| Retour au réseau | Énergie injectée au réseau |
| Production solaire | Énergie solaire produite |
| Appareil individuel | Énergie routée |

Les compteurs du routeur repartent de zéro chaque jour à 6 h : Home Assistant le gère.

### Bon à savoir

- Le routeur est interrogé toutes les 5 secondes.
- Un seul Smart PV-Router par installation.
- **Découverte MQTT** : si le routeur est déjà dans Home Assistant par la découverte MQTT, il y apparaît
  une seconde fois avec l'intégration. Les deux fonctionnent ensemble, mais n'utilisez qu'une seule des
  deux sources dans le tableau de bord Énergie.
- **Version MQTT** : cette intégration lit le routeur en HTTP. Pour passer par un broker MQTT, il existe
  [PvRouter NRI](https://github.com/nri04/ha-pvrouter-nri), développée indépendamment et non éditée par
  Smart Electromation Technology. Installées ensemble, les deux intégrations font apparaître le routeur
  deux fois.
- **Gradation manuelle** : le réglage n'agit qu'en mode Gradation manuelle. Avec un firmware plus ancien,
  qui ne renvoie pas cette valeur, Home Assistant affiche la dernière valeur envoyée.
- **Redémarrage** : il remet à zéro une partie des compteurs du jour.
- **Calibration de la Sortie 2** : elle coupe le routage, met la Sortie 2 en marche à pleine puissance
  le temps de la mesure, puis enregistre la puissance de la charge. À lancer seulement quand la charge
  peut consommer (chauffe-eau non coupé par son thermostat).
- Compatible avec [Solar Optimizer](https://github.com/jmcollin78/solar_optimizer) : modes des sorties
  et gradation manuelle.

### Support

Signaler un problème : [tickets du dépôt](https://github.com/smartelectromation/smart-pv-router-homeassistant/issues),
en joignant les diagnostics de l'intégration (Paramètres > Appareils et services > Smart PV-Router >
⋮ > Télécharger les diagnostics).

## English

Home Assistant integration for the **Smart PV-Router by Smart Electromation Technology**, a solar router designed
and made in France by Smart Electromation Technology. Official website:
[smartelectromation.com](https://smartelectromation.com).

It reads the router on your local network, with no cloud and no MQTT broker: measurements, daily
energy for the Energy dashboard, Output 1 and Output 2 modes, Boost, and an animated house card.

Because it uses HTTP, the router keeps its MQTT link to the Smart Electromation server: the online
dashboard (Grafana) and the follow-up by smartelectromation.com remain available.

### Requirements

- Smart PV-Router with firmware **V12_36** or later.
- Home Assistant **2026.3** or later, on the same local network as the router.

### Installation

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=smartelectromation&repository=smart-pv-router-homeassistant&category=integration)

1. Click the button above: HACS opens in your Home Assistant, on this integration. Click
   **Download**, then restart Home Assistant (Settings > System > Restart).
2. The router is **discovered automatically**: Settings > Devices & services > **Configure**.
3. That's all: **"Smart PV-Router" appears in the sidebar**, with the animated house.

If the router is not discovered:

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=smart_pv_router)

then enter `pvrouter.local` or the router's IP address.

<details>
<summary>Without the button: add it by hand in HACS</summary>

HACS > **⋮** menu > **Custom repositories** > URL
`https://github.com/smartelectromation/smart-pv-router-homeassistant`, category **Integration**, then
**Download**.
</details>

<details>
<summary>Without HACS: manual installation</summary>

1. Download `smart_pv_router.zip` from the [latest release](https://github.com/smartelectromation/smart-pv-router-homeassistant/releases/latest).
2. Unzip it into `config/custom_components/smart_pv_router/` (with the Samba or Studio Code Server
   add-on), then restart Home Assistant.

Updates are then not offered: copy it again for each release.
</details>

### Entities

| Type | Entities |
|---|---|
| Power | grid (+ import / − export), export, solar, diverted, Output 1, Output 2, house, battery, EV charger |
| Daily energy (kWh) | grid import, grid export, solar, diverted, solar diverted |
| Other measurements | voltage, currents, self-sufficiency and self-consumption today, diversion efficiency, water heater temperature, Boost remaining |
| States | Output 1 / Output 2 active, load saturated, night period, anti-bacteria cycle |
| Controls | Output 1 and Output 2 mode (Off, Automatic, Forced on, Dimmer, Manual dimmer), Boost, Boost duration, EcoMax, night setpoint, display |
| Disabled by default | WiFi signal, RTC temperature, MQTT connected, restart, Output 2 calibration, manual dimmer Output 1 / Output 2 |

Only the entities provided by the firmware are created: some depend on the router's options
(production, battery, EV charger, temperature probes, EcoMax). Boost duration and display need a
firmware that reports its API version (`API` key in `/getjson`).

### Smart PV-Router card

It shows in the sidebar (**Smart PV-Router**) as soon as the router is added. To also put it on one of
your dashboards: **Edit** > **Add card** > "Smart PV-Router".

- Picture of the house, with the battery and the car if the router measures them.
- Animated energy flows between the router and the solar panels, the grid, the water heater, Output 2,
  the battery and the EV charger; a chip with the power of each.
- Mode of each output, EcoMax, Boost and its duration, right on the card.
- Name and icon of Output 2 of your choice, in the card editor.

The power of each output is derived from the diverted power, a single measurement for both outputs:
Output 1 takes up to the power of its load, the rest goes to Output 2 (same calculation as the app and
the online dashboard).

### Energy dashboard

| Section | Entity |
|---|---|
| Grid consumption | Grid import energy |
| Return to grid | Grid export energy |
| Solar production | Solar energy |
| Individual device | Diverted energy |

The router's counters restart from zero every day at 6 am: Home Assistant handles it.

### Good to know

- The router is polled every 5 seconds.
- One Smart PV-Router per installation.
- **MQTT discovery**: if the router is already in Home Assistant through MQTT discovery, it shows up a
  second time with the integration. Both work together, but use only one of the two sources in the
  Energy dashboard.
- **MQTT version**: this integration reads the router over HTTP. To go through an MQTT broker, there is
  [PvRouter NRI](https://github.com/nri04/ha-pvrouter-nri), developed independently and not published by
  Smart Electromation Technology. If both integrations are installed, the router shows up twice.
- **Manual dimmer**: only acts in Manual dimmer mode. With an older firmware, which does not report
  this value, Home Assistant shows the last value sent.
- **Restart**: it resets part of the daily counters.
- **Output 2 calibration**: it pauses diversion, switches Output 2 fully on while measuring, then
  stores the load power. Only run it when the load can draw power (water heater not cut off by its
  thermostat).
- Works with [Solar Optimizer](https://github.com/jmcollin78/solar_optimizer): output modes and manual
  dimmer.

### Support

Report a problem: [repository issues](https://github.com/smartelectromation/smart-pv-router-homeassistant/issues),
with the integration diagnostics attached (Settings > Devices & services > Smart PV-Router > ⋮ >
Download diagnostics).

---

© 2026 Smart Electromation Technology · Code : licence [MIT](LICENSE) · Photos de la carte
(`www/scene_*.jpg`) : © Smart Electromation Technology, tous droits réservés, hors licence MIT /
card pictures: all rights reserved, not covered by the MIT licence.
