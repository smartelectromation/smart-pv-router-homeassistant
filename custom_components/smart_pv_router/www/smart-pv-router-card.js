/*
 * Carte « Smart PV-Router » pour Home Assistant.
 * Smart PV-Router by Smart Electromation Technology - https://smartelectromation.com
 * Code sous licence MIT. Photos de la maison (scene_*.jpg) : © Smart Electromation Technology.
 *
 * Même scène que l'application mobile SET : une photo de la maison par configuration (batterie,
 * voiture), où circulent les flux d'énergie entre le routeur et chaque élément.
 * La carte lit les entités de l'intégration smart_pv_router (liste donnée par le websocket
 * « smart_pv_router/routers ») et commande uniquement par les services de Home Assistant :
 * elle n'adresse jamais le routeur directement.
 */

const CARD_VERSION = "0.3.1";
const CARD_BASE = "/smart_pv_router_card";
const DOMAIN = "smart_pv_router";
const ACTIVE_W = 30; // En dessous, pas de flux affiché (comme l'application).

const COLORS = {
  pv: "#F59E0B", grid: "#6366F1", house: "#10B981", ecs: "#EF3E35", ev: "#06B6D4",
  batt: "#8B5CF6", out2: "#0EA5E9", ok: "#16A34A", muted: "#6B6B6B", sat: "#E08600",
};

// Photo selon (batterie, voiture). Même cadrage pour les quatre : une seule géométrie.
const SCENES = {
  "true,true": "scene_full.jpg", "true,false": "scene_batt.jpg",
  "false,true": "scene_ev.jpg", "false,false": "scene_min.jpg",
};

// Trajets de l'élément vers le routeur (tableau électrique, vers 0,625 ; 0,705), en fraction du côté.
const PATHS = {
  pv: [[0.45, 0.40], [0.56, 0.50], [0.615, 0.60], [0.623, 0.688]],
  grid: [[0.09, 0.33], [0.165, 0.53], [0.43, 0.60], [0.59, 0.63], [0.615, 0.69]],
  ecs: [[0.546, 0.75], [0.60, 0.75], [0.625, 0.72]],
  out2: [[0.80, 0.90], [0.70, 0.86], [0.645, 0.72]],
  batt: [[0.395, 0.79], [0.44, 0.82], [0.60, 0.82], [0.635, 0.715]],
  ev: [[0.80, 0.755], [0.737, 0.73], [0.645, 0.705]],
};

// Centre des pastilles : dans le ciel ou sur la pelouse.
const CHIPS = {
  pv: [0.50, 0.20], grid: [0.16, 0.24], ecs: [0.44, 0.90], house: [0.86, 0.32],
  out2: [0.81, 0.90], batt: [0.14, 0.78], ev: [0.86, 0.52],
};

const TEXT = {
  fr: {
    solar: "Solaire", grid: "Réseau", import: "Soutirage", export: "Injection", house: "Maison",
    water_heater: "Chauffe-eau", hot: "Chaud", output_2: "Sortie 2", output_1: "Sortie 1",
    stopped: "Arrêt", waiting: "Attente", battery: "Batterie", standby: "Veille", car: "Voiture",
    charger: "Borne", no_car: "Pas de charge", charts: "Suivi graphique", settings: "Réglages", car_unplugged: "Débranchée", car_plugged: "Branchée",
    car_ventilation: "Ventilation", st_on: "Marche", st_sat: "Saturée", pick_type: "Choisir la charge de la Sortie 2",
    types: { other: "Sortie 2", radiator: "Radiateur", pool: "Piscine", hot_tub: "Spa / jacuzzi",
      ev: "Voiture (Green'Up)", heat_pump: "Pompe à chaleur", water_heater: "Chauffe-eau 2",
      air_conditioner: "Climatisation", socket: "Prise" },
    boost: "Boost", boost_rem: "Boost · {n} min", boost_on: "Boost en cours", boost_off: "Boost",
    duration: "Durée", min: "min", start: "Lancer", stop: "Arrêter", ecomax: "EcoMax",
    dimmer: "Puissance", dimmer_hint: "Modulation manuelle : puissance envoyée à la sortie",
    dimmer_edit: "Cliquer pour saisir une valeur précise (ex. 54,7), puis Entrée",
    automate: "Automatiser",
    automate_hint: "Piloter cette sortie par vos automatisations : importer un exemple (annuler le surplus solaire) à adapter à vos besoins",
    night: "Nuit", not_found: "Aucun Smart PV-Router trouvé.", today: "Aujourd'hui",
    s_prod: "Production", s_autoc: "Autoconsommation", s_suffi: "Autoproduction",
    s_import: "Soutirée", s_export: "Injectée", s_routed: "Routée", s_eff: "Rendement du routage",
    ws_error: "L'intégration Smart PV-Router ne répond pas : mettez-la à jour puis redémarrez Home Assistant.",
    loading: "Chargement…",
    f_title: "Titre (vide : sans titre)", f_device: "Routeur", f_out1_name: "Nom de la Sortie 1",
    f_out2_name: "Nom de la Sortie 2", f_out2_icon: "Icône de la Sortie 2",
  },
  en: {
    solar: "Solar", grid: "Grid", import: "Import", export: "Export", house: "House",
    water_heater: "Water heater", hot: "Hot", output_2: "Output 2", output_1: "Output 1",
    stopped: "Off", waiting: "Waiting", battery: "Battery", standby: "Standby", car: "Car",
    charger: "Charger", no_car: "Not charging", charts: "Online charts", settings: "Settings", car_unplugged: "Unplugged", car_plugged: "Plugged in",
    car_ventilation: "Ventilation", st_on: "On", st_sat: "Saturated", pick_type: "Choose the Output 2 load",
    types: { other: "Output 2", radiator: "Radiator", pool: "Pool", hot_tub: "Hot tub",
      ev: "Car (Green'Up)", heat_pump: "Heat pump", water_heater: "Water heater 2",
      air_conditioner: "Air conditioning", socket: "Socket" },
    boost: "Boost", boost_rem: "Boost · {n} min", boost_on: "Boost running", boost_off: "Boost",
    duration: "Duration", min: "min", start: "Start", stop: "Stop", ecomax: "EcoMax",
    dimmer: "Power", dimmer_hint: "Manual dimmer: power sent to the output",
    dimmer_edit: "Click to type an exact value (e.g. 54.7), then Enter",
    automate: "Automate",
    automate_hint: "Drive this output with your own automations: import an example (cancel the solar surplus) to adapt to your needs",
    night: "Night", not_found: "No Smart PV-Router found.", today: "Today",
    s_prod: "Production", s_autoc: "Self-consumption", s_suffi: "Self-sufficiency",
    s_import: "Imported", s_export: "Exported", s_routed: "Diverted", s_eff: "Diversion efficiency",
    ws_error: "The Smart PV-Router integration does not answer: update it, then restart Home Assistant.",
    loading: "Loading…",
    f_title: "Title (empty: no title)", f_device: "Router", f_out1_name: "Output 1 name",
    f_out2_name: "Output 2 name", f_out2_icon: "Output 2 icon",
  },
  de: {
    solar: "Solar", grid: "Netz", import: "Bezug", export: "Einspeisung", house: "Haus",
    water_heater: "Warmwasser", hot: "Heiß", output_2: "Ausgang 2", output_1: "Ausgang 1",
    stopped: "Aus", waiting: "Wartet", battery: "Batterie", standby: "Standby", car: "Auto",
    charger: "Wallbox", no_car: "Lädt nicht", charts: "Online-Diagramme", settings: "Einstellungen", car_unplugged: "Abgesteckt", car_plugged: "Angesteckt",
    car_ventilation: "Lüftung", st_on: "Ein", st_sat: "Gesättigt", pick_type: "Verbraucher an Ausgang 2 wählen",
    types: { other: "Ausgang 2", radiator: "Heizkörper", pool: "Pool", hot_tub: "Whirlpool",
      ev: "Auto (Green'Up)", heat_pump: "Wärmepumpe", water_heater: "Warmwasser 2",
      air_conditioner: "Klimaanlage", socket: "Steckdose" },
    boost: "Boost", boost_rem: "Boost · {n} min", boost_on: "Boost läuft", boost_off: "Boost",
    duration: "Dauer", min: "min", start: "Starten", stop: "Stoppen", ecomax: "EcoMax",
    dimmer: "Leistung", dimmer_hint: "Manuelle Dimmung: Leistung am Ausgang",
    dimmer_edit: "Klicken, um einen genauen Wert einzugeben (z. B. 54,7), dann Enter",
    automate: "Automatisieren",
    automate_hint: "Diesen Ausgang mit eigenen Automatisierungen steuern: ein Beispiel (Solarüberschuss ausgleichen) importieren und anpassen",
    night: "Nacht", not_found: "Kein Smart PV-Router gefunden.", today: "Heute",
    s_prod: "Erzeugung", s_autoc: "Eigenverbrauch", s_suffi: "Autarkie",
    s_import: "Bezogen", s_export: "Eingespeist", s_routed: "Umgeleitet", s_eff: "Wirkungsgrad",
    ws_error: "Die Smart-PV-Router-Integration antwortet nicht: aktualisieren und Home Assistant neu starten.",
    loading: "Laden…",
    f_title: "Titel (leer: ohne Titel)", f_device: "Router", f_out1_name: "Name von Ausgang 1",
    f_out2_name: "Name von Ausgang 2", f_out2_icon: "Symbol von Ausgang 2",
  },
};

const DEFAULT_OUT2_ICON = "mdi:flash";

// Clés de /getjson (ou de commande) dont la carte lit l'entité.
const KEYS = [
  "PIN", "PROD", "POUT", "POUT1", "POUT2", "HOUSE", "BATT", "EVPOWER", "LOAD2", "TEMP1",
  "BOOSTREM", "GRID_ERR", "STATUS_OUT1", "STATUS_OUT2", "LOAD1_SATURED", "LOAD2_SATURED", "NIGHT", "Out1_mode", "Out2_mode",
  "BOOST", "ECOMAX", "BOOSTTIME", "TOT_PROD", "TOT_S", "INJECT", "TOTAL_POWER", "AUTO_C", "SUFFI",
  "EFF", "TIME", "CAR_MODE", "DIMMER1", "DIMMER2",
];

// Mode « Modulation manuelle » (mode 4 du routeur) : la carte affiche alors un curseur 0-100 %.
const MANUAL_DIMMER = "manual_dimmer";

// Modèle d'automatisation (blueprint) qui annule le surplus en faisant varier la modulation manuelle.
// Le lien « Automatiser » de la carte ouvre son import dans Home Assistant.
const BLUEPRINT_BASE = "https://github.com/smartelectromation/smart-pv-router-homeassistant/blob/main/blueprints/automation/smart_pv_router/";
const BLUEPRINTS = { fr: "annuler_surplus_sortie.yaml", en: "cancel_surplus_output.yaml" };

// Pourcentage au dixième, sans zéro inutile : 54.7 → "54.7", 45 → "45".
function pct1(v) {
  return String(Math.round(parseFloat(v) * 10) / 10);
}

// Bilan du jour (compteurs du routeur, remis à zéro à 6 h) : clé, texte, icône, couleur, unité.
const STATS = [
  // Les deux taux en dernier, sur la même ligne (2 ou 3 colonnes).
  ["TOT_PROD", "s_prod", "mdi:solar-power-variant", "pv", "kWh"],
  ["TOT_S", "s_import", "mdi:transmission-tower-import", "grid", "kWh"],
  ["INJECT", "s_export", "mdi:transmission-tower-export", "grid", "kWh"],
  ["TOTAL_POWER", "s_routed", "mdi:water-boiler", "ecs", "kWh"],
  ["AUTO_C", "s_autoc", "mdi:home-import-outline", "house", "%"],
  ["SUFFI", "s_suffi", "mdi:home-lightning-bolt-outline", "house", "%"],
];

function language(hass) {
  const lang = (hass && ((hass.locale && hass.locale.language) || hass.language)) ||
    document.documentElement.lang || "en";
  return lang.slice(0, 2).toLowerCase();
}

function text(lang) {
  return TEXT[lang] || TEXT.en;
}

function pathLength(points) {
  let len = 0;
  for (let i = 1; i < points.length; i++) {
    len += Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
  }
  return len;
}

const STYLE = `
  :host { display: block; }
  ha-card { overflow: hidden; container-type: inline-size; container-name: pvr; }
  .layout { display: block; }
  .side { min-width: 0; }
  /* Grand écran : la maison à gauche, à la hauteur de la fenêtre (--pvr-scene-max, donnée par la
     page de la barre latérale), les commandes et le bilan du jour à droite. */
  @container pvr (min-width: 820px) {
    .layout { display: grid; align-items: stretch;
      grid-template-columns: min(62cqw, var(--pvr-scene-max, 62cqw)) minmax(0, 1fr); }
    .side { padding: 12px 4px 8px; display: flex; flex-direction: column; }
    .commands { margin-top: auto; border-top: 1px solid var(--divider-color); }
    .side .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  .today { padding: 12px 16px 4px; }
  .today[hidden] { display: none; }
  .today-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 4px 0 8px; }
  .today-title { font-size: .95em; font-weight: 600; }
  .charts { display: inline-flex; align-items: center; gap: 4px; font-size: .8em; font-weight: 600;
    padding: 3px 10px; border-radius: 999px; text-decoration: none; color: ${COLORS.grid};
    border: 1px solid ${COLORS.grid}66; }
  .charts[hidden] { display: none; }
  .charts.settings { color: var(--secondary-text-color); border-color: var(--divider-color); cursor: pointer; }
  .charts ha-icon { --mdc-icon-size: 16px; }
  .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
  @container pvr (max-width: 400px) { .side .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  /* Très petit écran : une valeur par ligne, libellés entiers */
  @container pvr (max-width: 340px) { .side .stats { grid-template-columns: minmax(0, 1fr); } }
  .stat { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 12px;
    border: 1px solid var(--divider-color); cursor: pointer; min-width: 0; }
  .stat[hidden] { display: none; }
  .stat ha-icon { --mdc-icon-size: 22px; flex: none; }
  .stat .txt { display: flex; flex-direction: column; min-width: 0; }
  .stat .lab { font-size: .75em; color: var(--secondary-text-color); line-height: 1.2;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .stat .num { font-weight: 700; white-space: nowrap; }
  .title { padding: 12px 16px 8px; font-size: 1.15em; font-weight: 500; }
  .scene { position: relative; aspect-ratio: 1 / 1; container-type: inline-size;
    background: #cfe0ef center / cover no-repeat; }
  svg.flows { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
  svg.flows path { fill: none; stroke-linecap: round; stroke-linejoin: round; }
  .track { stroke: rgba(255, 255, 255, .45); stroke-width: 7.7; }
  .dots, .halo { stroke-dasharray: 0 25; display: none; }
  .halo { stroke: #fff; stroke-width: 24; }
  .dots { stroke-width: 17; }
  g.active .dots, g.active .halo { display: inline; animation: pvr-flow linear infinite; }
  g.reverse .dots, g.reverse .halo { animation-direction: reverse; }
  g[hidden] { display: none; }
  @keyframes pvr-flow { from { stroke-dashoffset: 0; } to { stroke-dashoffset: -25; } }
  @media (prefers-reduced-motion: reduce) { g.active .dots, g.active .halo { animation: none; } }
  .chip { position: absolute; display: flex; align-items: center; gap: .35em; max-width: 44%;
    box-sizing: border-box; padding: .3em .8em .3em .6em; border-radius: 999px; cursor: pointer;
    background: rgba(255, 255, 255, .93); box-shadow: 0 1px 6px rgba(51, 65, 85, .2);
    color: #323232; font-size: clamp(10px, 3.1cqw, 14px); line-height: 1.15;
    font-family: var(--paper-font-body1_-_font-family, inherit); }
  .chip[hidden] { display: none; }
  .chip ha-icon { --mdc-icon-size: 1.25em; flex: none; }
  .chip.node { padding-left: .3em; }
  .chip.node ha-icon { --mdc-icon-size: 1.15em; color: #fff; background: currentColor;
    border-radius: 50%; padding: .3em; }
  .chip .icon-bg { display: flex; border-radius: 50%; padding: .28em; flex: none; }
  .chip .icon-bg ha-icon { color: #fff; }
  .chip .txt { display: flex; flex-direction: column; min-width: 0; }
  .chip .cap { font-size: .76em; color: #6B6B6B; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; }
  .chip .val { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 12px 16px 4px; }
  .controls[hidden] { display: none; }
  .ctl { display: flex; align-items: center; gap: 6px; font-size: .9em; }
  .ctl[hidden] { display: none; }
  .ctl { position: relative; flex-wrap: wrap; }
  .dim { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; flex-basis: 100%; font-weight: 600;
    color: var(--primary-text-color); }
  .dim[hidden] { display: none; }
  .dim .range { flex: 1; min-width: 120px; max-width: 280px; margin: 0; cursor: pointer; }
  #d-out1 .range { accent-color: ${COLORS.ecs}; }
  #d-out2 .range { accent-color: ${COLORS.out2}; }
  /* Valeur affichée comme un simple texte « 45 % » ; un clic la rend modifiable (saisie au dixième). */
  .pctbox { display: inline-flex; align-items: center; gap: 2px; }
  .dim .pct { width: 3.6em; font: inherit; font-weight: 600; padding: 2px 4px; margin: 0;
    text-align: right; font-variant-numeric: tabular-nums; border-radius: 6px; cursor: text;
    border: 1px solid transparent; background: none; color: var(--primary-text-color);
    -moz-appearance: textfield; appearance: textfield; }
  .dim .pct::-webkit-outer-spin-button, .dim .pct::-webkit-inner-spin-button {
    -webkit-appearance: none; margin: 0; }
  .dim .pct:hover { border-color: var(--divider-color); }
  .dim .pct:focus { outline: none; background: var(--card-background-color, #fff); }
  .dim .auto { display: inline-flex; align-items: center; gap: 4px; font-size: .85em; font-weight: 600;
    padding: 3px 10px 3px 7px; border-radius: 999px; text-decoration: none; cursor: pointer;
    white-space: nowrap; color: ${COLORS.grid}; border: 1px solid ${COLORS.grid}66; }
  .dim .auto[hidden] { display: none; }
  .dim .auto:hover { background: ${COLORS.grid}14; }
  .dim .auto ha-icon { --mdc-icon-size: 16px; }
  #d-out1 .pct:focus { border-color: ${COLORS.ecs}; }
  #d-out2 .pct:focus { border-color: ${COLORS.out2}; }
  .led { display: inline-flex; align-items: center; gap: 5px; font-size: .85em; font-weight: 600;
    color: var(--secondary-text-color); white-space: nowrap; cursor: pointer; }
  .led[hidden] { display: none; }
  .led i { width: 12px; height: 12px; border-radius: 50%; box-sizing: border-box; flex: none;
    background: #fff; border: 1px solid #9e9e9e; }
  .led.on i { background: #FFD600; border-color: #E0B800; box-shadow: 0 0 6px #FFD60099; }
  .led.on { color: var(--primary-text-color); }
  .led.sat i { background: #FF9800; border-color: #E08600; box-shadow: 0 0 6px #FF980099; }
  .led.sat { color: #E08600; }
  .lab-chip { display: inline-flex; align-items: center; gap: 5px; font: inherit; font-weight: 600;
    padding: 4px 10px 4px 7px; border-radius: 999px; border: none; cursor: pointer; white-space: nowrap; }
  .lab-chip ha-icon { --mdc-icon-size: 18px; }
  .lab-chip.ecs { background: ${COLORS.ecs}1f; color: ${COLORS.ecs}; }
  .lab-chip.out2 { background: ${COLORS.out2}1f; color: ${COLORS.out2}; }
  .lab-chip .caret { font-size: .8em; opacity: .7; }
  .lab-chip .caret[hidden] { display: none; }
  #k-out1 select { border-color: ${COLORS.ecs}66; }
  #k-out2 select { border-color: ${COLORS.out2}66; }
  .picker { position: absolute; left: 0; bottom: calc(100% + 6px); z-index: 5; display: grid;
    grid-template-columns: repeat(2, minmax(150px, 1fr)); gap: 2px; padding: 6px; border-radius: 12px;
    background: var(--card-background-color, #fff); border: 1px solid var(--divider-color);
    box-shadow: 0 4px 16px rgba(0, 0, 0, .18); }
  .picker[hidden] { display: none; }
  .picker button { display: flex; align-items: center; gap: 8px; font: inherit; text-align: left;
    padding: 6px 10px; border: none; border-radius: 8px; background: none; cursor: pointer;
    color: var(--primary-text-color); }
  .picker button:hover { background: ${COLORS.out2}14; }
  .picker button.sel { background: ${COLORS.out2}26; color: ${COLORS.out2}; font-weight: 600; }
  .picker ha-icon { --mdc-icon-size: 20px; color: ${COLORS.out2}; }
  select { font: inherit; padding: 4px 6px; border-radius: 8px; cursor: pointer;
    border: 1px solid var(--divider-color); background: var(--card-background-color, #fff);
    color: var(--primary-text-color); }
  .badges { display: flex; gap: 6px; margin-left: auto; flex-wrap: wrap; }
  .badge { font-size: .8em; padding: 3px 10px; border-radius: 999px; cursor: pointer; user-select: none;
    border: 1px solid var(--divider-color); color: var(--secondary-text-color); background: none; }
  .badge[hidden] { display: none; }
  .badge.on { border-color: ${COLORS.ok}; color: ${COLORS.ok}; font-weight: 600; }
  .badge.night { border-color: ${COLORS.grid}; color: ${COLORS.grid}; }
  .badge.time { display: inline-flex; align-items: center; gap: 4px; }
  .badge.time[hidden] { display: none; }
  .badge.time ha-icon { --mdc-icon-size: 14px; }
  .badge.alarm { border-color: #B91C1C; color: #B91C1C; font-weight: 600; }
  .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; padding: 8px 16px 14px; }
  .boost { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px; }
  .boost[hidden], .eco[hidden] { display: none; }
  /* Boost : bouton bascule, rempli en rouge pendant le Boost */
  .boost-btn { display: inline-flex; align-items: center; gap: 6px; font: inherit; font-weight: 600;
    padding: 7px 16px; border-radius: 999px; cursor: pointer; border: 2px solid ${COLORS.ecs};
    background: none; color: ${COLORS.ecs}; transition: background .2s, color .2s; }
  .boost-btn ha-icon { --mdc-icon-size: 20px; }
  .boost-btn[aria-pressed="true"] { background: ${COLORS.ecs}; color: #fff; }
  /* EcoMax : interrupteur */
  .eco { display: inline-flex; align-items: center; gap: 8px; margin-left: auto; cursor: pointer;
    font-weight: 600; user-select: none; }
  .eco-lab { display: inline-flex; align-items: center; gap: 4px; }
  .eco-lab ha-icon { --mdc-icon-size: 20px; color: ${COLORS.ok}; }
  .switch { position: relative; width: 40px; height: 22px; padding: 0; border-radius: 11px; border: none;
    cursor: pointer; background: var(--switch-unchecked-track-color, #9e9e9e); transition: background .2s; }
  .switch .knob { position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%;
    background: #fff; box-shadow: 0 1px 2px rgba(0, 0, 0, .3); transition: left .2s; }
  .switch[aria-checked="true"] { background: ${COLORS.ok}; }
  .switch[aria-checked="true"] .knob { left: 21px; }
  .bstate { display: flex; align-items: center; gap: 4px; font-size: .9em; font-weight: 600;
    color: var(--secondary-text-color); cursor: pointer; }
  .bstate.on { color: ${COLORS.ecs}; }
  .bstate ha-icon { --mdc-icon-size: 20px; }
  .bctl { display: flex; align-items: center; gap: 6px; font-size: .9em; }
  .bctl [hidden] { display: none; }
  .bctl label, .bctl .unit { color: var(--primary-text-color); font-weight: 700; }
  .bctl input { width: 4.2em; font: inherit; padding: 4px 6px; text-align: center; border-radius: 8px;
    border: 1px solid var(--divider-color); background: var(--card-background-color, #fff);
    color: var(--primary-text-color); }
  .bctl button { font: inherit; font-weight: 600; padding: 5px 14px; border-radius: 8px; cursor: pointer;
    border: 1px solid ${COLORS.ecs}; background: ${COLORS.ecs}; color: #fff; }
  .bctl button.secondary { background: none; color: ${COLORS.ecs}; }
  .msg { padding: 16px; color: var(--secondary-text-color); }
`;

class SmartPVRouterCard extends HTMLElement {
  static getStubConfig() {
    return {};
  }

  static getConfigForm() {
    const t = text(language(document.querySelector("home-assistant")?.hass));
    const labels = {
      title: t.f_title, device_id: t.f_device, output_1_name: t.f_out1_name,
      output_2_name: t.f_out2_name, output_2_icon: t.f_out2_icon,
    };
    return {
      schema: [
        { name: "title", selector: { text: {} } },
        { name: "device_id", selector: { device: { integration: DOMAIN } } },
        { name: "output_1_name", selector: { text: {} } },
        {
          type: "grid", name: "", schema: [
            { name: "output_2_name", selector: { text: {} } },
            { name: "output_2_icon", selector: { icon: {} } },
          ],
        },
      ],
      computeLabel: (schema) => labels[schema.name] || schema.name,
    };
  }

  setConfig(config) {
    if (!config) throw new Error("Configuration invalide / invalid configuration");
    this._config = { ...config };
    this._built = null;
    this._sig = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 9;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  connectedCallback() {
    if (this._resize) this._resize.observe(this);
  }

  disconnectedCallback() {
    if (this._resize) this._resize.disconnect();
  }

  // ---------------------------------------------------------------- données

  async _loadRouters() {
    if (this._loading) return;
    this._loading = true;
    try {
      const result = await this._hass.callWS({ type: `${DOMAIN}/routers` });
      this._routers = (result && result.routers) || [];
      this._error = false;
      if (!this._routers.length) {
        // Intégration encore en cours de chargement : nouvel essai dans 10 s.
        setTimeout(() => { this._routers = null; this._render(); }, 10000);
      }
    } catch (err) {
      console.warn("Smart PV-Router card:", err);
      this._error = true;
    }
    this._loading = false;
    this._render();
  }

  _router() {
    const list = this._routers || [];
    return list.find((r) => r.device_id && r.device_id === this._config.device_id) || list[0];
  }

  // Charge de la Sortie 2 : réglage de la carte, sinon option de l'intégration, sinon « Sortie 2 ».
  _out2(t) {
    const c = this._config;
    const o2 = (this._routerEntry && this._routerEntry.output_2) || {};
    const type = o2.type || "other";
    const typeName = type !== "other" && t.types ? t.types[type] : "";
    return {
      icon: c.output_2_icon || o2.icon || DEFAULT_OUT2_ICON,
      name: c.output_2_name || o2.name || typeName || t.output_2,
      chosen: !!(c.output_2_name || c.output_2_icon || o2.name || type !== "other"),
    };
  }

  async _setOutput2(type, icon) {
    const router = this._routerEntry;
    if (!router) return;
    try {
      await this._hass.callWS({ type: `${DOMAIN}/set_output_2`, entry_id: router.entry_id,
        output_2_type: type });
      router.output_2 = { ...(router.output_2 || {}), type, icon };
      this._built = null;
      this._sig = null;
      this._render();
    } catch (err) {
      console.error("Smart PV-Router card:", err);
      this.dispatchEvent(new CustomEvent("hass-notification", {
        bubbles: true, composed: true, detail: { message: String((err && err.message) || err) },
      }));
    }
  }

  _id(key) {
    const id = this._entities && this._entities[key];
    return id && this._hass.states[id] ? id : null;
  }

  _state(key) {
    const id = this._id(key);
    return id ? this._hass.states[id] : null;
  }

  _num(key) {
    const s = this._state(key);
    if (!s) return null;
    const v = parseFloat(s.state);
    return Number.isFinite(v) ? v : null;
  }

  _on(key) {
    const s = this._state(key);
    return !!s && s.state === "on";
  }

  // ---------------------------------------------------------------- affichage

  _root() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    return this.shadowRoot;
  }

  _message(msg) {
    this._built = null;
    this._sig = null;
    this._root().innerHTML = `<style>${STYLE}</style><ha-card><div class="msg"></div></ha-card>`;
    this._root().querySelector(".msg").textContent = msg;
  }

  _render() {
    if (!this._hass || !this._config) return;
    const lang = language(this._hass);
    const t = text(lang);
    if (this._error) return this._message(t.ws_error);
    if (!this._routers) {
      this._loadRouters();
      if (!this._built) this._message(t.loading);
      return;
    }
    const router = this._router();
    if (!router) return this._message(t.not_found);
    this._entities = router.entities || {};
    this._routerEntry = router;
    const o2 = router.output_2 || {};
    const builtFor = `${router.device_id}|${lang}|${o2.type}|${o2.name}|${router.grafana_url}`;
    if (this._built !== builtFor) this._build(t, builtFor);
    const sig = KEYS.map((k) => {
      const s = this._state(k);
      return s ? s.state : "-";
    }).join("|");
    if (sig === this._sig) return;
    this._sig = sig;
    this._update(lang, t);
  }

  _build(t, builtFor) {
    const c = this._config;
    const root = this._root();
    const flows = Object.entries(PATHS).map(([name, pts]) => {
      const d = "M" + pts.map(([x, y]) => `${x * 1000} ${y * 1000}`).join(" L");
      return `<g id="f-${name}" style="color:${COLORS[name]}">
        <path class="track" d="${d}"></path>
        <path class="halo" d="${d}" pathLength="100"></path>
        <path class="dots" d="${d}" pathLength="100" stroke="currentColor"></path></g>`;
    }).join("");
    const chip = (name, node = false) =>
      `<div class="chip${node ? " node" : ""}" id="c-${name}" hidden>
        <ha-icon></ha-icon><span class="txt"><span class="cap"></span><span class="val"></span></span></div>`;
    const dimmer = (n) => `<span class="dim" id="d-out${n}" hidden><span class="dim-lab"></span>
      <input class="range" type="range" min="0" max="100" step="0.1">
      <span class="pctbox"><input class="pct" type="number" min="0" max="100" step="0.1"
        inputmode="decimal"><span>%</span></span>
      <a class="auto" hidden><ha-icon icon="mdi:robot-outline"></ha-icon><span></span></a></span>`;
    root.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="title" hidden></div>
        <div class="layout">
        <div class="scene">
          <svg class="flows" viewBox="0 0 1000 1000" aria-hidden="true">${flows}</svg>
          ${chip("pv")}${chip("grid")}${chip("house")}${chip("ecs")}${chip("out2")}
          ${chip("batt")}${chip("ev")}
        </div>
        <div class="side">
        <div class="today" id="today" hidden>
          <div class="today-head"><span class="today-title"></span>
            <a class="charts" id="charts" target="_blank" rel="noopener noreferrer" hidden>
              <ha-icon icon="mdi:chart-line"></ha-icon><span></span></a>
            <span class="badges">
              <span class="badge alarm" id="b-alarm" hidden></span>
              <span class="badge night" id="b-night" hidden></span>
              <a class="charts settings" id="settings" hidden>
                <ha-icon icon="mdi:cog-outline"></ha-icon><span></span></a>
              <span class="badge time" id="b-time" hidden><ha-icon icon="mdi:clock-outline"></ha-icon><span></span></span>
            </span>
          </div>
          <div class="stats">${STATS.map(([key, , icon]) => `<div class="stat" id="s-${key}" hidden>
            <ha-icon icon="${icon}"></ha-icon><span class="txt"><span class="lab"></span><span class="num"></span></span>
          </div>`).join("")}</div>
        </div>
        <div class="commands">
        <div class="controls">
          <span class="ctl" id="k-out1"><button class="lab-chip ecs" id="l-out1">
            <ha-icon icon="mdi:water-boiler"></ha-icon><span></span></button><select id="m-out1"></select>
            <span class="led" id="led-out1" hidden><i></i><span></span></span>
            ${dimmer("1")}</span>
          <span class="ctl" id="k-out2"><button class="lab-chip out2" id="l-out2">
            <ha-icon></ha-icon><span></span><span class="caret" hidden>▾</span></button><select id="m-out2"></select>
            <span class="led" id="led-out2" hidden><i></i><span></span></span>
            ${dimmer("2")}
            <div class="picker" id="picker" hidden></div></span>
        </div>
        <div class="actions">
          <span class="boost" id="boost" hidden>
            <button class="boost-btn" id="bo-btn" aria-pressed="false">
              <ha-icon icon="mdi:rocket-launch"></ha-icon><span></span></button>
            <span class="bctl">
              <label for="bo-dur" id="bo-dur-label"></label>
              <input id="bo-dur" type="number" min="1" max="1440" step="1" inputmode="numeric">
              <span class="unit" id="bo-unit"></span>
            </span>
          </span>
          <label class="eco" id="eco" hidden>
            <button class="switch" id="eco-sw" role="switch" aria-checked="false"><span class="knob"></span></button>
            <span class="eco-lab"><ha-icon icon="mdi:leaf"></ha-icon><span></span></span>
          </label>
        </div>
        </div>
        </div>
        </div>
      </ha-card>`;

    const $ = (sel) => root.querySelector(sel);
    const title = c.title === undefined ? "Smart PV-Router" : c.title;
    $(".title").textContent = title;
    $(".title").hidden = !title;
    const out2 = this._out2(t);
    $("#l-out1 span").textContent = c.output_1_name || t.water_heater;
    $("#l-out2 span").textContent = out2.name;
    $("#l-out2 ha-icon").setAttribute("icon", out2.icon);
    $("#l-out1").addEventListener("click", () => this._moreInfo("POUT1"));
    $("#led-out1").addEventListener("click", () => this._moreInfo("STATUS_OUT1"));
    $("#led-out2").addEventListener("click", () => this._moreInfo("STATUS_OUT2"));
    // Sortie 2 : un administrateur choisit la charge (radiateur, piscine...) ; sinon, détail de l'entité.
    const canPick = !!(this._hass.user && this._hass.user.is_admin) && !!this._routerEntry
      && !c.output_2_icon;
    $("#l-out2 .caret").hidden = !canPick;
    $("#l-out2").title = canPick ? t.pick_type : "";
    const picker = $("#picker");
    if (canPick) {
      const current = (this._routerEntry.output_2 || {}).type || "other";
      for (const [type, icon] of Object.entries(this._routerEntry.output_2_types || {})) {
        const b = document.createElement("button");
        b.className = type === current ? "sel" : "";
        const ic = document.createElement("ha-icon");
        ic.setAttribute("icon", icon);
        const lab = document.createElement("span");
        lab.textContent = (t.types && t.types[type]) || type;
        b.append(ic, lab);
        b.addEventListener("click", (ev) => {
          ev.stopPropagation();
          picker.hidden = true;
          this._setOutput2(type, icon);
        });
        picker.appendChild(b);
      }
    }
    $("#l-out2").addEventListener("click", (ev) => {
      ev.stopPropagation();
      if (canPick) picker.hidden = !picker.hidden;
      else this._moreInfo("POUT2");
    });
    if (!this._closePicker) {
      // Un seul écouteur sur la racine (elle survit aux reconstructions) : un clic ailleurs ferme la liste.
      this._closePicker = () => { const p = root.querySelector("#picker"); if (p) p.hidden = true; };
      root.addEventListener("click", this._closePicker);
    }
    $(".eco-lab span").textContent = t.ecomax;
    $("#b-night").textContent = t.night;
    $("#bo-dur-label").textContent = t.duration;
    $("#bo-unit").textContent = t.min;
    $(".today-title").textContent = t.today;
    // Suivi graphique (Grafana SET) : nouvel onglet, adresse donnée par l'intégration.
    const charts = $("#charts");
    const url = this._routerEntry && this._routerEntry.grafana_url;
    charts.hidden = !url || !/^https?:\/\//.test(url);
    if (!charts.hidden) charts.href = url;
    charts.querySelector("span").textContent = t.charts;
    // Réglages : fiche de l'appareil (carte Configuration), réservée aux administrateurs. Retour à la
    // maison par l'entrée « Smart PV-Router » de la barre latérale.
    const settings = $("#settings");
    const deviceId = this._routerEntry && this._routerEntry.device_id;
    settings.hidden = !deviceId || !(this._hass.user && this._hass.user.is_admin);
    settings.querySelector("span").textContent = t.settings;
    if (!settings.hidden) {
      const path = `/config/devices/device/${deviceId}`;
      settings.href = path;
      settings.addEventListener("click", (ev) => {
        ev.preventDefault();
        history.pushState(null, "", path);
        window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
      });
    }
    for (const [key, label, , color] of STATS) {
      $(`#s-${key} .lab`).textContent = t[label];
      $(`#s-${key} ha-icon`).style.color = COLORS[color];
      $(`#s-${key}`).addEventListener("click", () => this._moreInfo(key));
    }

    for (const file of Object.values(SCENES)) new Image().src = `${CARD_BASE}/${file}?v=${CARD_VERSION}`;

    // Longueur de chaque trajet : la vitesse des points suit la puissance, comme l'application.
    this._lengths = Object.fromEntries(Object.entries(PATHS).map(([k, p]) => [k, pathLength(p)]));

    const moreInfo = {
      "c-pv": "PROD", "c-grid": "PIN", "c-house": "HOUSE", "c-ecs": "POUT1", "c-out2": "POUT2",
      "c-batt": "BATT", "c-ev": "EVPOWER", "b-night": "NIGHT", "b-alarm": "GRID_ERR", "b-time": "TIME",
    };
    for (const [elId, key] of Object.entries(moreInfo)) {
      $(`#${elId}`).addEventListener("click", () => this._moreInfo(key));
    }
    $("#eco-sw").addEventListener("click", (ev) => {
      ev.preventDefault();
      const id = this._id("ECOMAX");
      if (id) this._call("switch", this._on("ECOMAX") ? "turn_off" : "turn_on", { entity_id: id });
    });
    for (const [n, key] of [["1", "Out1_mode"], ["2", "Out2_mode"]]) {
      $(`#m-out${n}`).addEventListener("change", (ev) => {
        const id = this._id(key);
        if (id) this._call("select", "select_option", { entity_id: id, option: ev.target.value });
      });
    }
    // Modulation manuelle : curseur (consigne envoyée au relâchement) ou valeur précise au dixième
    // tapée dans la case (envoyée par Entrée ou en quittant la case ; Échap annule).
    for (const [n, key] of [["1", "DIMMER1"], ["2", "DIMMER2"]]) {
      const box = $(`#d-out${n}`);
      const range = box.querySelector(".range");
      const num = box.querySelector(".pct");
      const out = n === "1" ? t.output_1 : t.output_2;
      box.querySelector(".dim-lab").textContent = t.dimmer;
      box.title = t.dimmer_hint;
      range.setAttribute("aria-label", `${t.dimmer} (${out})`);
      num.setAttribute("aria-label", `${t.dimmer} (${out}), %`);
      num.title = t.dimmer_edit;
      const send = (value) => {
        delete box.dataset.busy;
        const id = this._id(key);
        if (id) this._call("number", "set_value", { entity_id: id, value });
      };
      range.addEventListener("input", () => {
        box.dataset.busy = "1";
        num.value = pct1(range.value);
      });
      range.addEventListener("change", () => send(parseFloat(pct1(range.value))));
      num.addEventListener("focus", () => { box.dataset.busy = "1"; num.select(); });
      num.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") num.blur();
        else if (ev.key === "Escape") {
          num.value = num.dataset.sent || "";
          delete box.dataset.busy;
          num.blur();
        }
      });
      num.addEventListener("change", () => {
        const v = parseFloat(String(num.value).replace(",", "."));
        if (!Number.isFinite(v)) { num.value = num.dataset.sent || ""; return; }
        const value = parseFloat(pct1(Math.min(100, Math.max(0, v))));
        num.value = range.value = value;
        send(value);
      });
      num.addEventListener("blur", () => delete box.dataset.busy);
      // « Automatiser » (administrateurs) : import du modèle qui annule le surplus avec cette sortie.
      const auto = box.querySelector(".auto");
      auto.hidden = !(this._hass.user && this._hass.user.is_admin);
      auto.querySelector("span").textContent = t.automate;
      auto.title = t.automate_hint;
      const bp = BLUEPRINT_BASE + (BLUEPRINTS[language(this._hass)] || BLUEPRINTS.en);
      auto.href = `/_my_redirect/blueprint_import?blueprint_url=${encodeURIComponent(bp)}`;
      auto.addEventListener("click", (ev) => {
        ev.preventDefault();
        history.pushState(null, "", auto.getAttribute("href"));
        window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
      });
    }
    $("#bo-dur").addEventListener("change", (ev) => {
      const id = this._id("BOOSTTIME");
      const value = parseInt(ev.target.value, 10);
      if (id && value >= 1) this._call("number", "set_value", { entity_id: id, value });
    });
    $("#bo-btn").addEventListener("click", () => {
      const id = this._id("BOOST");
      if (id) this._call("switch", this._on("BOOST") ? "turn_off" : "turn_on", { entity_id: id });
    });

    if (!this._resize && window.ResizeObserver) {
      this._resize = new ResizeObserver(() => this._placeChips());
      this._resize.observe(this);
    }
    this._built = builtFor;
    this._sig = null;
  }

  _update(lang, t) {
    const root = this._root();
    const $ = (sel) => root.querySelector(sel);
    const c = this._config;
    const nf0 = new Intl.NumberFormat(lang, { maximumFractionDigits: 0 });
    const nf1 = new Intl.NumberFormat(lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const nf2 = new Intl.NumberFormat(lang, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const power = (w) => {
      if (w === null) return "—";
      return Math.abs(w) >= 1000 ? `${nf2.format(w / 1000)} kW` : `${nf0.format(w)} W`;
    };
    const val = (key) => this._num(key) || 0;

    const hasProd = !!this._id("PROD");
    const hasBatt = !!this._id("BATT");
    const hasEv = !!this._id("EVPOWER");
    const mode2 = this._state("Out2_mode");
    const out2Cfg = this._out2(t);
    const showOut2 = !!mode2 && (mode2.state !== "stop" || val("LOAD2") > 0 || out2Cfg.chosen);

    // La voiture n'est dans le garage (ouvert) que pendant une charge : /getjson ne dit pas si elle
    // est branchée, seule la puissance de la borne le montre. Sinon, garage fermé.
    const charging = hasEv && val("EVPOWER") > ACTIVE_W;
    // Voiture au garage (ouvert) : branchée ou en charge selon CAR_MODE, donné par la borne. Sans
    // cette clé (ancien firmware, borne muette depuis 3 min), seule une charge en cours le montre.
    const carState = this._state("CAR_MODE");
    const car = carState && !["unknown", "unavailable"].includes(carState.state) ? carState.state : null;
    const carHere = car ? ["plugged", "charging"].includes(car) : charging;
    $(".scene").style.backgroundImage =
      `url("${CARD_BASE}/${SCENES[`${hasBatt},${hasEv && carHere}`]}?v=${CARD_VERSION}")`;

    // Flux : (puissance, vers le routeur, affiché)
    const pv = val("PROD");
    const grid = val("PIN");
    const batt = val("BATT"); // > 0 : charge
    const ecs = val("POUT1");
    const out2 = val("POUT2");
    const ev = val("EVPOWER");
    this._flow("pv", hasProd ? pv : 0, true, hasProd);
    this._flow("grid", Math.abs(grid), grid > 0, true);
    this._flow("ecs", ecs, false, true);
    this._flow("out2", out2, false, showOut2);
    this._flow("batt", Math.abs(batt), batt < 0, hasBatt);
    this._flow("ev", ev, false, charging && carHere);

    // Pastilles
    if (hasProd) this._chip("pv", "mdi:white-balance-sunny", COLORS.pv, t.solar, power(pv));
    else this._hide("pv");
    if (grid > ACTIVE_W) this._chip("grid", "mdi:transmission-tower-import", COLORS.grid, t.import, power(grid));
    else if (grid < -ACTIVE_W) {
      this._chip("grid", "mdi:transmission-tower-export", COLORS.grid, t.export, power(-grid));
    } else this._chip("grid", "mdi:transmission-tower", COLORS.grid, t.grid, power(Math.abs(grid)));
    this._chip("house", "mdi:home", COLORS.house, t.house, power(this._num("HOUSE")));

    const temp = this._num("TEMP1");
    const mode1 = this._state("Out1_mode");
    // En marche forcée, la ligne du haut le dit (sinon routage et marche forcée se ressemblent).
    const ecsName = mode1 && mode1.state === "forced" ? this._format(mode1, "forced")
      : c.output_1_name || t.water_heater;
    const ecsCap = temp === null ? ecsName : `${ecsName} · ${nf0.format(temp)} °C`;
    if (this._on("BOOST")) {
      const rem = this._num("BOOSTREM");
      this._chip("ecs", "mdi:rocket-launch", COLORS.ecs,
        t.boost_rem.replace("{n}", rem === null ? "—" : nf0.format(rem)), power(ecs));
    } else if (this._on("LOAD1_SATURED") && ecs < ACTIVE_W) {
      // Même rouge que l'étiquette « Chauffe-eau » sous la photo ; l'état se lit dans la valeur.
      this._chip("ecs", "mdi:water-boiler", COLORS.ecs, ecsCap, t.hot, false, COLORS.ok);
    } else if (ecs > ACTIVE_W) {
      this._chip("ecs", "mdi:fire", COLORS.ecs, ecsCap, power(ecs));
    } else {
      // Ne chauffe pas : « Arrêt » si le mode est Arrêt, « Attente » sinon (comme la Sortie 2).
      const idle = mode1 && mode1.state === "stop" ? t.stopped : t.waiting;
      this._chip("ecs", "mdi:water-boiler", COLORS.ecs, ecsCap, idle, false, COLORS.muted);
    }

    if (showOut2) {
      // Même logique que le chauffe-eau : Saturée, puissance (routage ou marche forcée), Arrêt, Attente.
      // Toujours le bleu de l'étiquette « Sortie 2 » sous la photo ; l'état se lit dans la valeur.
      const out2Cap = mode2.state === "forced" ? this._format(mode2, "forced") : out2Cfg.name;
      if (this._on("LOAD2_SATURED") && out2 < ACTIVE_W) {
        this._chip("out2", out2Cfg.icon, COLORS.out2, out2Cap, t.st_sat, false, COLORS.sat);
      } else if (out2 > ACTIVE_W) {
        this._chip("out2", out2Cfg.icon, COLORS.out2, out2Cap, power(out2), false, COLORS.out2);
      } else {
        const idle = mode2.state === "stop" ? t.stopped : t.waiting;
        this._chip("out2", out2Cfg.icon, COLORS.out2, out2Cap, idle, false, COLORS.muted);
      }
    } else this._hide("out2");

    if (hasBatt) {
      const icon = batt > ACTIVE_W ? "mdi:battery-charging" : "mdi:battery";
      this._chip("batt", icon, COLORS.batt, t.battery,
        Math.abs(batt) > ACTIVE_W ? power(Math.abs(batt)) : t.standby);
    } else this._hide("batt");
    if (!hasEv) this._hide("ev");
    else if (charging && carHere) this._chip("ev", "mdi:car-electric", COLORS.ev, t.car, power(ev));
    else if (car === "plugged") {
      this._chip("ev", "mdi:car-electric-outline", COLORS.ev, t.car, t.car_plugged, false, COLORS.muted);
    } else if (car === "unplugged") {
      this._chip("ev", "mdi:ev-station", COLORS.ev, t.charger, t.car_unplugged, false, COLORS.muted);
    } else if (car === "ventilation") {
      this._chip("ev", "mdi:fan-alert", COLORS.ev, t.charger, t.car_ventilation, false, COLORS.sat);
    } else this._chip("ev", "mdi:ev-station", COLORS.ev, t.charger, t.no_car, false, COLORS.muted);

    // Modes des sorties, EcoMax, nuit, alarme
    this._updateMode("#m-out1", "#k-out1", "Out1_mode");
    this._updateMode("#m-out2", "#k-out2", "Out2_mode");
    this._updateDimmer("1", "Out1_mode", "DIMMER1");
    this._updateDimmer("2", "Out2_mode", "DIMMER2");
    for (const [n, statusKey, satKey] of [["1", "STATUS_OUT1", "LOAD1_SATURED"], ["2", "STATUS_OUT2", "LOAD2_SATURED"]]) {
      const led = $(`#led-out${n}`);
      led.hidden = !this._id(statusKey) && !this._id(satKey);
      const sat = this._on(satKey);
      const on = this._on(statusKey);
      led.classList.toggle("sat", sat);
      led.classList.toggle("on", on && !sat);
      led.querySelector("span").textContent = sat ? t.st_sat : on ? t.st_on : t.stopped;
    }
    const ecomax = this._state("ECOMAX");
    $("#eco").hidden = !ecomax;
    $("#eco-sw").setAttribute("aria-checked", String(!!ecomax && ecomax.state === "on"));
    $("#b-night").hidden = !this._on("NIGHT");
    const alarm = this._state("GRID_ERR");
    const alarmOn = !!alarm && !["none", "unknown", "unavailable"].includes(alarm.state);
    $("#b-alarm").hidden = !alarmOn;
    if (alarmOn) $("#b-alarm").textContent = this._format(alarm);

    // Heure du routeur
    const time = this._state("TIME");
    const timeOk = !!time && !["unknown", "unavailable"].includes(time.state);
    $("#b-time").hidden = !timeOk;
    if (timeOk) $("#b-time span").textContent = time.state;

    // Boost
    const boost = this._state("BOOST");
    $("#boost").hidden = !boost;
    if (boost) {
      const on = boost.state === "on";
      const rem = this._num("BOOSTREM");
      $("#bo-btn span").textContent = on && rem !== null
        ? `${t.boost} · ${nf0.format(rem)} ${t.min}` : t.boost;
      $("#bo-btn").setAttribute("aria-pressed", String(on));
      $("#bo-btn").title = on ? t.stop : t.start;
      const hasDur = !!this._id("BOOSTTIME");
      for (const sel of ["#bo-dur", "#bo-dur-label", "#bo-unit"]) $(sel).hidden = !hasDur || on;
      const dur = this._num("BOOSTTIME");
      if (hasDur && root.activeElement !== $("#bo-dur")) $("#bo-dur").value = dur === null ? "" : dur;
    }

    // Bilan du jour
    let anyStat = false;
    for (const [key, , , , unit] of STATS) {
      const v = this._num(key);
      const el = $(`#s-${key}`);
      el.hidden = !this._id(key);
      if (el.hidden) continue;
      anyStat = true;
      el.querySelector(".num").textContent = v === null ? "—"
        : unit === "%" ? `${nf0.format(v)} %` : `${nf2.format(v)} kWh`;
    }

    // Le bloc reste visible s'il n'a que des indicateurs (nuit, alarme, heure).
    $("#today").hidden = !anyStat && $("#b-time").hidden && $("#b-night").hidden && $("#b-alarm").hidden;
    this._placeChips();
  }

  // Flux de w watts ; toRouter : de l'élément vers le routeur.
  _flow(name, w, toRouter, shown) {
    const g = this._root().querySelector(`#f-${name}`);
    g.style.display = shown ? "" : "none"; // élément SVG : pas de propriété « hidden »
    const active = shown && w > ACTIVE_W;
    g.classList.toggle("active", active);
    g.classList.toggle("reverse", active && !toRouter);
    if (!active) return;
    // Vitesse en côtés par seconde, plus rapide avec la puissance (comme l'application).
    const speed = 0.06 + 0.16 * Math.min(1, w / 5000);
    const seconds = (this._lengths[name] / 4) / speed; // un quart du trajet par cycle (4 points)
    for (const p of g.querySelectorAll(".dots, .halo")) p.style.animationDuration = `${seconds.toFixed(2)}s`;
  }

  // color : icône (couleur de l'élément) ; valueColor : valeur, si elle doit différer (état).
  _chip(name, icon, color, caption, value, node = false, valueColor = null) {
    const el = this._root().querySelector(`#c-${name}`);
    el.hidden = false;
    const ic = el.querySelector("ha-icon");
    if (ic.getAttribute("icon") !== icon) ic.setAttribute("icon", icon);
    ic.style.color = node ? "#fff" : color;
    if (node) ic.style.background = color;
    el.querySelector(".cap").textContent = caption;
    const v = el.querySelector(".val");
    v.textContent = value;
    v.style.color = valueColor || (node ? "#323232" : color);
  }

  _hide(name) {
    this._root().querySelector(`#c-${name}`).hidden = true;
  }

  // Pastilles centrées sur leur point, gardées dans la photo.
  _placeChips() {
    const scene = this._root().querySelector(".scene");
    if (!scene) return;
    const size = scene.clientWidth;
    if (!size) return;
    const margin = 4;
    for (const [name, [x, y]] of Object.entries(CHIPS)) {
      const el = this._root().querySelector(`#c-${name}`);
      if (!el || el.hidden) continue;
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      const left = Math.min(Math.max(x * size - w / 2, margin), Math.max(margin, size - w - margin));
      const top = Math.min(Math.max(y * size - h / 2, margin), Math.max(margin, size - h - margin));
      el.style.left = `${left}px`;
      el.style.top = `${top}px`;
    }
  }

  _updateMode(sel, wrap, key) {
    const root = this._root();
    const select = root.querySelector(sel);
    const s = this._state(key);
    root.querySelector(wrap).hidden = !s;
    if (!s) return;
    const options = s.attributes.options || [];
    const signature = options.join("|");
    if (select.dataset.options !== signature) {
      select.innerHTML = "";
      for (const option of options) {
        const el = document.createElement("option");
        el.value = option;
        el.textContent = this._format(s, option);
        select.appendChild(el);
      }
      select.dataset.options = signature;
    }
    if (root.activeElement !== select) select.value = s.state;
  }

  // Curseur 0-100 % sous la sortie, seulement en Modulation manuelle (mode 4).
  _updateDimmer(n, modeKey, key) {
    const box = this._root().querySelector(`#d-out${n}`);
    const mode = this._state(modeKey);
    const s = this._state(key);
    box.hidden = !s || !mode || mode.state !== MANUAL_DIMMER;
    if (box.hidden || box.dataset.busy) return;
    const v = parseFloat(s.state);
    const num = box.querySelector(".pct");
    box.querySelector(".range").value = Number.isFinite(v) ? v : 0;
    num.value = num.dataset.sent = Number.isFinite(v) ? pct1(v) : "";
  }

  _format(stateObj, value) {
    if (this._hass.formatEntityState) {
      return value === undefined
        ? this._hass.formatEntityState(stateObj)
        : this._hass.formatEntityState(stateObj, value);
    }
    return value === undefined ? stateObj.state : value;
  }

  _call(domain, service, data) {
    this._hass.callService(domain, service, data).catch((err) => {
      console.error("Smart PV-Router card:", err);
      this.dispatchEvent(new CustomEvent("hass-notification", {
        bubbles: true, composed: true, detail: { message: String((err && err.message) || err) },
      }));
    });
  }

  _moreInfo(key) {
    const entityId = this._id(key);
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: true, composed: true, detail: { entityId },
    }));
  }
}

// Page « Smart PV-Router » de la barre latérale, ajoutée par l'intégration : la carte, centrée,
// sous la barre de titre habituelle de Home Assistant. Rien à configurer pour l'utilisateur.
class SmartPVRouterPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    this._render();
  }

  set panel(panel) {
    this._panel = panel;
  }

  set route(route) {
    this._route = route;
  }

  _render() {
    if (!this._hass) return;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; min-height: 100vh; background: var(--primary-background-color); }
          .toolbar { display: flex; align-items: center; gap: 4px; height: var(--header-height, 56px);
            padding: 0 12px; box-sizing: border-box; font-size: 20px;
            background: var(--app-header-background-color, var(--primary-color));
            color: var(--app-header-text-color, var(--text-primary-color, #fff));
            border-bottom: var(--app-header-border-bottom, none); }
          /* Toute la largeur, jusqu'à 1400 px ; sur grand écran, la maison prend la hauteur de la
             fenêtre sous la barre de titre, le reste va aux commandes et au bilan du jour. */
          .content { max-width: 1400px; margin: 0 auto; padding: 16px; box-sizing: border-box;
            --pvr-scene-max: calc(100vh - var(--header-height, 56px) - 34px); }
          :host([narrow]) .content { padding: 8px; }
        </style>
        <div class="toolbar"><ha-menu-button></ha-menu-button><span class="name">Smart PV-Router</span></div>
        <div class="content"></div>`;
      this._card = document.createElement("smart-pv-router-card");
      this._card.setConfig({ title: "" });
      this.shadowRoot.querySelector(".content").appendChild(this._card);
    }
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    menu.hass = this._hass;
    menu.narrow = !!this._narrow;
    this.toggleAttribute("narrow", !!this._narrow);
    this._card.hass = this._hass;
  }
}

if (!customElements.get("smart-pv-router-panel")) {
  customElements.define("smart-pv-router-panel", SmartPVRouterPanel);
}

if (!customElements.get("smart-pv-router-card")) {
  customElements.define("smart-pv-router-card", SmartPVRouterCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "smart-pv-router-card",
    name: "Smart PV-Router",
    description: "Smart PV-Router by Smart Electromation Technology",
    preview: true,
    documentationURL: "https://github.com/smartelectromation/smart-pv-router-homeassistant",
  });
  console.info(`%c SMART-PV-ROUTER-CARD %c ${CARD_VERSION} `,
    "color: #fff; background: #EF3E35; font-weight: 700;", "color: inherit;");
}
