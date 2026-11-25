# Drive the Smart PV-Router with your own automations

[Version française](automatisations.md) · [Back to the README](../README.md)

The **Smart PV-Router by Smart Electromation Technology** is an open router. With the Home Assistant
integration you can let it work on its own, or **decide yourself** how much power goes to each
output, following your own rules: electricity price, off-peak hours, battery, solar forecast,
presence...

This page explains the principle, the useful entities, how to build an automation without writing
code, then gives examples to adapt. They are there to show the principle: **the automations you can
write are not limited to these examples.**

## Contents

1. [The principle in three points](#1-the-principle-in-three-points)
2. [Output modes](#2-output-modes)
3. [Useful entities](#3-useful-entities)
4. [Finding your entity names](#4-finding-your-entity-names)
5. [Building an automation without code](#5-building-an-automation-without-code)
6. [Examples to adapt](#6-examples-to-adapt)
7. [Precautions](#7-precautions)

## 1. The principle in three points

1. **Set the output to Manual dimmer** (router mode 4), on the "Smart PV-Router" card or with the
   "Output 1 mode" entity. The router no longer decides the power of that output.
2. **Set the power** with the **"Manual dimmer output 1"** (or output 2) entity, from 0 to 100 %, to a
   tenth (e.g. 54.7 %). This is what your automation does, as often as needed.
3. **Hand control back to the router** by setting the output to **Automatic** or **Dimmer**.

The router is read every 5 seconds; a setpoint sent by Home Assistant is applied at once.

## 2. Output modes

| Mode | Who decides the power? |
|---|---|
| Off | Nobody: the output is off. |
| Automatic | The router, on/off, from the surplus and the **Auto threshold**. |
| Forced on | Nobody: the output runs at full power. |
| Dimmer | The router, to the watt, to keep the **Dimmer target** on the grid. |
| **Manual dimmer** | **Home Assistant**: the output follows "Manual dimmer output 1 / 2". |

## 3. Useful entities

Names as shown by Home Assistant in English. Some entities only exist if the router has the matching
option (production, battery, EV charger, temperature probe, EcoMax...).

**Instant measurements**

| Entity | What it measures |
|---|---|
| Grid power | Power exchanged with the grid: **positive** when the house imports, **negative** when it exports. The basic measurement for a surplus automation. |
| Grid export power | The same measurement when power is exported, as a positive value. |
| Solar power | Power produced by the panels. |
| Diverted power | Power sent to both outputs together. |
| Output 1 / Output 2 power | Power of each output. |
| House consumption | Consumption excluding the water heater, Output 2 and the EV charger. |
| Battery power | Positive when the battery charges, negative when it discharges. |
| Battery level | State of charge in %, if the router reads the battery; "unknown" when it no longer answers. |
| Water heater temperature | With a probe; "unknown" without one. |

**States**

| Entity | Meaning |
|---|---|
| Output 1 / 2 active | The output is sending power. |
| Output 1 / 2 load saturated | The load no longer draws power (water heater cut by its thermostat, water hot). |
| Night period | The router is in its night slot. |

**Daily energy** (reset every day at 6 am)

| Entity | What it counts |
|---|---|
| Diverted energy | All energy sent to the outputs, **including at night** (reheat, Boost, forced on). |
| Solar diverted energy | The part of it that comes from the sun: at each moment, the output power not taken from the grid. |
| Diversion efficiency | Solar diverted energy ÷ diverted energy, in %: the share of the outputs' energy that comes from the sun. |

**Controls and settings**

| Entity | Role |
|---|---|
| Output 1 / 2 mode | Selects the mode (table in § 2). In an automation, "Manual dimmer" is written `manual_dimmer`. |
| **Manual dimmer output 1 / 2** | **The 0 to 100 % setpoint** used in Manual dimmer mode. |
| Dimmer target | In Dimmer mode, the grid power the router aims for (0 W: no import, no export; −50 W: keep 50 W of export; +50 W: allow 50 W of import). |
| Auto threshold | For an on/off appliance: the minimum surplus, as a % of its power, to switch it on. Example: 2000 W appliance and 60 % threshold → it starts from 1200 W of surplus; the missing 800 W come from the grid, i.e. 40 % of its consumption at full price. |
| EcoMax | No grid reheat if the sun has already heated the water to the minimum temperature since the previous slot. |
| Boost, Boost duration | Heats at full power for the chosen time. |
| Time slots, Night heating temperature, Load shedding power | Router settings (recent firmware). |

## 4. Finding your entity names

The technical name of an entity (e.g. `number.smart_pv_router_manual_dimmer_output_1`) depends on your
device name and on the Home Assistant language at installation time.

- **Settings > Devices & services > Smart PV-Router**, then click the device: all its entities are
  listed. Click an entity, then the cog: its **entity ID** is shown.
- In the automation editor you do not need the technical name: you pick the entity from a list.
- In the YAML examples below, replace the names with yours.

## 5. Building an automation without code

Example: "every day at 1 pm, send 60 % to the water heater".

1. **Settings > Automations & scenes > Create automation > Create new automation.**
2. **When**: *Add trigger* > *Time* > 13:00:00.
3. **And if** (optional): e.g. *Add condition* > *Entity* > *State* > "Output 1 mode" is "Manual
   dimmer", to act only when the output is in that mode.
4. **Then do**: *Add action* > search **"Set number value"** > *Targets*: "Manual dimmer output 1" >
   *Value*: 60.
5. **Save** and give it a name.

To change an output's mode in an action: **"Select option"** on "Output 1 mode", option "Manual
dimmer".

Any automation can be shown as YAML (⋮ menu > **Edit in YAML**): handy to paste an example from this
page, then go back to the visual editor.

## 6. Examples to adapt

Entity names in the examples are those of a fresh English installation: adapt them (§ 4). Sensors
that do not come from the router (price, battery, forecast) are provided by other integrations; their
names are examples.

### 6.1 Cancel the solar surplus (supplied example)

This is the example the card's **Automate** button imports into Home Assistant (blueprint). It
rebuilds the router's own regulation in Home Assistant, to show the principle.

[![Import the example](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fsmartelectromation%2Fsmart-pv-router-homeassistant%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fsmart_pv_router%2Fcancel_surplus_output.yaml)

On each new "Grid power" reading:

```
gap = target − grid power                    (W)
new = current + reactivity × gap ÷ load power × 100   (%)
```

kept between 0 and 100 %. Example: 600 W exported (grid = −600 W), target 0 W, 1800 W water heater,
reactivity 0.5 → the setpoint rises by 0.5 × 600 ÷ 1800 × 100 ≈ 16.7 points. The next correction is
smaller, and so on until the grid reaches the target (real test: from 18 to 53 % in 26 seconds, grid
at −4 W).

- The **deadband** (20 W by default) avoids correcting tiny gaps.
- **Reactivity** (0.5 by default): lower it if the power oscillates, raise it if it follows too slowly.
- The example only acts in Manual dimmer mode and never changes the mode itself.

To go further: open the automation created from the example, ⋮ menu > **Take control**. It becomes a
normal automation that you can change freely.

### 6.2 Full power when the price is negative

```yaml
alias: "Water heater at 100 % when price is negative"
triggers:
  - trigger: numeric_state
    entity_id: sensor.electricity_price          # your price sensor
    below: 0
actions:
  - action: select.select_option
    target:
      entity_id: select.smart_pv_router_output_1_mode
    data:
      option: manual_dimmer                      # Manual dimmer
  - action: number.set_value
    target:
      entity_id: number.smart_pv_router_manual_dimmer_output_1
    data:
      value: 100
```

Add a second automation that sets the output back to `auto` (Automatic) when the price is positive
again.

### 6.3 Fixed power during off-peak hours

```yaml
alias: "Off-peak: water heater at 40 %"
triggers:
  - trigger: time
    at: "22:30:00"
    id: start
  - trigger: time
    at: "06:30:00"
    id: end
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: start
        sequence:
          - action: select.select_option
            target:
              entity_id: select.smart_pv_router_output_1_mode
            data:
              option: manual_dimmer
          - action: number.set_value
            target:
              entity_id: number.smart_pv_router_manual_dimmer_output_1
            data:
              value: 40
      - conditions:
          - condition: trigger
            id: end
        sequence:
          - action: select.select_option
            target:
              entity_id: select.smart_pv_router_output_1_mode
            data:
              option: auto                       # the router takes over again
```

### 6.4 Battery first

If the router reads your battery ("Battery level" entity) or another integration tracks it, give the
surplus to the water heater only once it is almost full. The simplest way: start from example 6.1
(*Take control*) and add a condition:

```yaml
conditions:
  - condition: numeric_state
    entity_id: sensor.battery_state_of_charge    # your battery state of charge (%)
    above: 95
```

and an automation that sets the dimmer to 0 % when the battery drops below 90 %.

### 6.5 Two outputs, your priorities

Example: the water heater first, then the pool on Output 2 once the water is hot.

- Create two automations from example 6.1, one per output.
- In the Output 2 one, add the condition "Output 1 load saturated" is *on*.
- Set both outputs to Manual dimmer.

## 7. Precautions

- **An output's mode is stored in the router's memory.** Change it now and then (a few times a day),
  never in a loop.
- **The Manual dimmer setpoint can change as often as needed**: this is what a regulation should vary,
  every 5 seconds if needed.
- **If Home Assistant stops** (update, failure, network down), nothing corrects the setpoint any more:
  the output keeps the last value received. Before maintenance, set the outputs back to Automatic.
- In Dimmer and Manual dimmer modes, outputs are meant for **resistive loads** (water heater,
  radiator...). An appliance with a motor or a compressor (heat pump, air conditioning, pool pump) is
  driven on/off, not in Dimmer or Manual dimmer mode.
- One source of truth: if an automation drives an output in Manual dimmer mode, do not let another
  automation (or Solar Optimizer) drive the same output at the same time.

---

Smart PV-Router by Smart Electromation Technology · [smartelectromation.com](https://smartelectromation.com)
· Home Assistant is a trademark of its owner.
