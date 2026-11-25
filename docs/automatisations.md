# Piloter le Smart PV-Router avec vos automatisations

[English version](automations.md) · [Retour au README](../README.md)

Le **Smart PV-Router by Smart Electromation Technology** est un routeur ouvert. Avec l'intégration
Home Assistant, vous pouvez le laisser travailler seul, ou bien **décider vous-même** de la puissance
envoyée à chaque sortie, selon vos propres règles : prix de l'électricité, heures creuses, batterie,
prévisions solaires, présence...

Cette page explique le principe, les entités utiles, comment créer une automatisation sans écrire de
code, puis donne des exemples à adapter. Ils sont là pour vous montrer le principe : **les
automatisations que vous pouvez écrire ne se limitent pas à ces exemples.**

## Sommaire

1. [Le principe en trois points](#1-le-principe-en-trois-points)
2. [Les modes des sorties](#2-les-modes-des-sorties)
3. [Les entités utiles](#3-les-entités-utiles)
4. [Trouver le nom de vos entités](#4-trouver-le-nom-de-vos-entités)
5. [Créer une automatisation sans écrire de code](#5-créer-une-automatisation-sans-écrire-de-code)
6. [Exemples à adapter](#6-exemples-à-adapter)
7. [Précautions](#7-précautions)

## 1. Le principe en trois points

1. **Passez la sortie en Modulation manuelle** (mode 4 du routeur), sur la carte « Smart PV-Router »
   ou par l'entité « Mode Sortie 1 ». Le routeur ne décide plus de la puissance de cette sortie.
2. **Réglez la puissance** avec l'entité **« Modulation manuelle Sortie 1 »** (ou Sortie 2), de 0 à
   100 %, au dixième près (exemple : 54,7 %). C'est ce que fait votre automatisation, aussi souvent
   que nécessaire.
3. **Rendez la main au routeur** en repassant la sortie en **Automatique** ou en **Modulation**.

L'état du routeur est relu toutes les 5 secondes ; une consigne envoyée par Home Assistant part
immédiatement.

## 2. Les modes des sorties

| Mode | Qui décide de la puissance ? |
|---|---|
| Arrêt | Personne : la sortie est coupée. |
| Automatique | Le routeur, en tout ou rien, selon le surplus et le **Seuil Auto**. |
| Marche forcée | Personne : la sortie est à pleine puissance. |
| Modulation | Le routeur, au watt près, pour tenir la **Cible Modulation** sur le réseau. |
| **Modulation manuelle** | **Home Assistant** : la sortie suit la valeur de « Modulation manuelle Sortie 1 / 2 ». |

## 3. Les entités utiles

Les noms sont ceux affichés par Home Assistant en français. Certaines entités n'existent que si le
routeur a l'option correspondante (production, batterie, borne, sonde de température, EcoMax...).

**Mesures instantanées**

| Entité | Ce qu'elle mesure |
|---|---|
| Puissance réseau | Puissance échangée avec le réseau : **positive** quand la maison soutire, **négative** quand elle injecte. C'est la mesure de base d'une automatisation de surplus. |
| Puissance injectée | La même mesure, quand elle part au réseau, en valeur positive. |
| Production solaire | Puissance produite par les panneaux. |
| Puissance routée | Puissance envoyée aux deux sorties ensemble. |
| Puissance Sortie 1 / Sortie 2 | Puissance de chaque sortie. |
| Consommation de la maison | Consommation hors chauffe-eau, Sortie 2 et borne. |
| Puissance batterie | Positive quand la batterie se charge, négative quand elle se décharge. |
| Niveau de la batterie | Niveau de charge en %, si le routeur lit la batterie ; « inconnu » quand elle ne lui répond plus. |
| Température du chauffe-eau | Avec une sonde ; « inconnue » sans sonde. |

**États**

| Entité | Signification |
|---|---|
| Sortie 1 / 2 active | La sortie envoie de la puissance. |
| Charge Sortie 1 / 2 saturée | La charge ne consomme plus (chauffe-eau coupé par son thermostat, eau chaude). |
| Période de nuit | Le routeur est dans sa plage de nuit. |

**Énergies du jour** (remises à zéro chaque jour à 6 h)

| Entité | Ce qu'elle compte |
|---|---|
| Énergie routée | Toute l'énergie envoyée dans les sorties, **y compris la nuit** (relance, Boost, marche forcée). |
| Énergie solaire routée | La part de cette énergie qui vient du soleil : à chaque instant, la puissance des sorties qui n'est pas prise au réseau. |
| Rendement du routage | Énergie solaire routée ÷ énergie routée, en % : la part de l'énergie des sorties qui vient du soleil. |

**Commandes et réglages**

| Entité | Rôle |
|---|---|
| Mode Sortie 1 / 2 | Choisit le mode (tableau du § 2). Dans une automatisation, l'option « Modulation manuelle » s'écrit `manual_dimmer`. |
| **Modulation manuelle Sortie 1 / 2** | **La consigne de 0 à 100 %** utilisée en Modulation manuelle. |
| Cible Modulation | En mode Modulation, la puissance que le routeur cherche à obtenir sur le réseau (0 W : ni soutirage ni injection ; −50 W : garder 50 W d'injection ; +50 W : accepter 50 W de soutirage). |
| Seuil Auto | Pour un appareil en tout ou rien : le surplus minimal, en % de sa puissance, pour le mettre en marche. Exemple : appareil de 2000 W et seuil de 60 % → il démarre dès 1200 W de surplus ; les 800 W manquants viennent du réseau, soit 40 % de sa consommation au plein tarif. |
| EcoMax | Pas de relance sur le réseau si le soleil a déjà chauffé l'eau à la température minimale depuis la plage précédente. |
| Boost, Durée du Boost | Chauffe à pleine puissance pendant la durée choisie. |
| Plages horaires, Température de relance, Puissance de délestage | Réglages du routeur (firmware récent). |

## 4. Trouver le nom de vos entités

Le nom technique d'une entité (par exemple `number.smart_pv_router_modulation_manuelle_sortie_1`)
dépend du nom de votre appareil et de la langue de Home Assistant au moment de l'installation.

- **Paramètres > Appareils et services > Smart PV-Router**, puis cliquez sur l'appareil : toutes ses
  entités sont listées. Cliquez sur une entité, puis sur la roue dentée : son **identifiant**
  s'affiche.
- Dans l'éditeur d'automatisations, vous n'avez pas besoin du nom technique : on choisit l'entité dans
  une liste.
- Dans les exemples YAML ci-dessous, remplacez les noms par les vôtres.

## 5. Créer une automatisation sans écrire de code

Exemple : « chaque jour à 13 h, envoyer 60 % au chauffe-eau ».

1. **Paramètres > Automatisations et scènes > Créer une automatisation > Créer une nouvelle
   automatisation.**
2. **Quand** : *Ajouter un déclencheur* > *Heure* > 13:00:00.
3. **Et si** (facultatif) : par exemple *Ajouter une condition* > *Entité* > *État* > « Mode Sortie 1 »
   est « Modulation manuelle », pour n'agir que si la sortie est dans ce mode.
4. **Alors faire** : *Ajouter une action* > cherchez **« Définir une valeur numérique »** > *Cibles* :
   « Modulation manuelle Sortie 1 » > *Valeur* : 60.
5. **Enregistrer**, et donnez un nom.

Pour changer le mode d'une sortie dans une action : **« Sélectionner une option »** sur « Mode Sortie 1 »,
option « Modulation manuelle ».

Chaque automatisation peut s'afficher en YAML (menu ⋮ > **Modifier en YAML**) : c'est utile pour coller
un exemple de cette page, puis revenir à l'éditeur visuel.

## 6. Exemples à adapter

Les noms d'entités des exemples sont ceux d'une installation neuve en français : adaptez-les (§ 4).
Les capteurs qui ne viennent pas du routeur (prix, batterie, prévisions) sont fournis par d'autres
intégrations ; leurs noms sont des exemples.

### 6.1 Annuler le surplus solaire (exemple fourni)

C'est l'exemple que le bouton **Automatiser** de la carte importe dans Home Assistant (blueprint).
Il refait la régulation du routeur dans Home Assistant, pour montrer le principe.

[![Importer l'exemple](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fsmartelectromation%2Fsmart-pv-router-homeassistant%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fsmart_pv_router%2Fannuler_surplus_sortie.yaml)

À chaque nouvelle mesure de « Puissance réseau » :

```
écart   = cible − puissance réseau          (W)
nouveau = actuel + réactivité × écart ÷ puissance de la charge × 100   (%)
```

borné entre 0 et 100 %. Exemple : 600 W injectés (réseau = −600 W), cible 0 W, chauffe-eau de
1800 W, réactivité 0,5 → la consigne monte de 0,5 × 600 ÷ 1800 × 100 ≈ 16,7 points. La correction
suivante est plus petite, et ainsi de suite jusqu'à ce que le réseau soit à la cible (essai réel :
de 18 à 53 % en 26 secondes, réseau à −4 W).

- La **zone morte** (20 W par défaut) évite de corriger des écarts insignifiants.
- La **réactivité** (0,5 par défaut) : baissez-la si la puissance oscille, montez-la si elle suit
  trop lentement.
- L'exemple n'agit qu'en Modulation manuelle et ne change jamais le mode lui-même.

Pour aller plus loin : ouvrez l'automatisation créée à partir de l'exemple, menu ⋮ > **Prendre le
contrôle**. Elle devient une automatisation normale, que vous pouvez modifier librement.

### 6.2 Chauffer à fond quand le prix est négatif

```yaml
alias: "Chauffe-eau à 100 % si prix négatif"
triggers:
  - trigger: numeric_state
    entity_id: sensor.prix_electricite          # votre capteur de prix (€/kWh)
    below: 0
actions:
  - action: select.select_option
    target:
      entity_id: select.smart_pv_router_mode_sortie_1
    data:
      option: manual_dimmer                      # Modulation manuelle
  - action: number.set_value
    target:
      entity_id: number.smart_pv_router_modulation_manuelle_sortie_1
    data:
      value: 100
```

Ajoutez une deuxième automatisation qui remet la sortie en `auto` (Automatique) quand le prix
redevient positif.

### 6.3 Puissance fixe pendant les heures creuses

```yaml
alias: "Heures creuses : chauffe-eau à 40 %"
triggers:
  - trigger: time
    at: "22:30:00"
    id: debut
  - trigger: time
    at: "06:30:00"
    id: fin
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: debut
        sequence:
          - action: select.select_option
            target:
              entity_id: select.smart_pv_router_mode_sortie_1
            data:
              option: manual_dimmer
          - action: number.set_value
            target:
              entity_id: number.smart_pv_router_modulation_manuelle_sortie_1
            data:
              value: 40
      - conditions:
          - condition: trigger
            id: fin
        sequence:
          - action: select.select_option
            target:
              entity_id: select.smart_pv_router_mode_sortie_1
            data:
              option: auto                       # le routeur reprend la main
```

### 6.4 La batterie d'abord

Si le routeur lit votre batterie (entité « Niveau de la batterie ») ou si une autre intégration la
suit, ne donnez le surplus au chauffe-eau qu'une fois qu'elle est presque pleine. Le plus simple :
partir de l'exemple 6.1 (*Prendre le contrôle*) et ajouter une condition :

```yaml
conditions:
  - condition: numeric_state
    entity_id: sensor.batterie_niveau_de_charge   # niveau de charge de votre batterie (%)
    above: 95
```

et une automatisation qui met la modulation à 0 % quand la batterie redescend sous 90 %.

### 6.5 Deux sorties, vos priorités

Exemple : le chauffe-eau d'abord, puis la piscine sur la Sortie 2 quand l'eau est chaude.

- Créez deux automatisations à partir de l'exemple 6.1, une par sortie.
- Dans celle de la Sortie 2, ajoutez la condition « Charge Sortie 1 saturée » est *activée*.
- Passez les deux sorties en Modulation manuelle.

## 7. Précautions

- **Le mode d'une sortie est enregistré dans la mémoire du routeur.** Changez-le de temps en temps
  (quelques fois par jour), jamais en boucle.
- **La consigne de Modulation manuelle peut changer aussi souvent que nécessaire** : c'est elle qu'une
  régulation doit faire varier, toutes les 5 secondes si besoin.
- **Si Home Assistant s'arrête** (mise à jour, panne, réseau coupé), plus rien ne corrige la consigne :
  la sortie garde la dernière valeur reçue. Avant une maintenance, repassez les sorties en Automatique.
- Les sorties sont faites pour des **charges résistives** (chauffe-eau, radiateur...) en Modulation.
  Un appareil avec un moteur ou un compresseur (pompe à chaleur, climatisation, pompe de piscine) se
  pilote en tout ou rien, pas en Modulation ni en Modulation manuelle.
- Une seule source de vérité : si une automatisation pilote une sortie en Modulation manuelle, ne
  faites pas piloter la même sortie par une autre automatisation (ou Solar Optimizer) en même temps.

---

Smart PV-Router by Smart Electromation Technology · [smartelectromation.com](https://smartelectromation.com)
· Home Assistant est une marque de son propriétaire.
