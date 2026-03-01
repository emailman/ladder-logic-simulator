# Ladder Logic Simulator

A desktop PLC ladder logic simulator written in Python using Tkinter. Loads a ladder program from a JSON file and runs a continuous scan cycle — just like a real PLC.

## Features

- **Continuous scan cycle** — 100 ms scan loop mimicking real PLC behaviour
- **Live energisation highlighting** — energised paths drawn in green, de-energised in grey
- **Clickable input contacts** — inputs can be configured as momentary (active while held) or latching toggle
- **Reset button** — zeroes all timer accumulated values and counter counts; the only way to reset either
- **Supported instructions:**
  - `NO` / `NC` contacts (normally open / normally closed)
  - `coil` / `set` / `reset` output coils
  - `TON` / `TOF` timers (on-delay / off-delay) with live accumulated value display
  - `CTU` / `CTD` counters (up / down) with rising-edge detection
  - Parallel branches (any number of rungs in parallel)

## Requirements

- Python 3.10+
- Tkinter (included with standard Python on Windows and most Linux distros)

No third-party packages required.

## Usage

```bash
cd ladder_sim
python main.py                  # loads example.json
python main.py myprogram.json   # loads a custom program
```

## JSON Program Format

Programs are defined in JSON with two top-level sections: `bits` (tag declarations) and `rungs` (ladder logic).

```json
{
  "title": "My Ladder Program",
  "bits": {
    "I0.0": {"label": "Start",  "type": "input",  "momentary": true},
    "I0.1": {"label": "Stop",   "type": "input",  "momentary": true},
    "Q0.0": {"label": "Motor",  "type": "output"},
    "T0":   {"label": "Timer",  "type": "timer"},
    "C0":   {"label": "Counter","type": "counter"}
  },
  "rungs": [
    {
      "comment": "Start-Stop Sealing Circuit",
      "series": [
        {"parallel": [
          [{"type": "NO", "bit": "I0.0"}],
          [{"type": "NO", "bit": "Q0.0"}]
        ]},
        {"type": "NC",   "bit": "I0.1"},
        {"type": "coil", "bit": "Q0.0"}
      ]
    },
    {
      "comment": "Run Timer (5 s on-delay)",
      "series": [
        {"type": "NO",  "bit": "Q0.0"},
        {"type": "TON", "bit": "T0", "preset_ms": 5000}
      ]
    },
    {
      "comment": "Count cycles",
      "series": [
        {"type": "NO",  "bit": "T0.DN"},
        {"type": "CTU", "bit": "C0", "preset": 10}
      ]
    }
  ]
}
```

### Bit declarations (`bits`)

Each key is the tag name. Fields:

| Field       | Required | Values                              | Description                                          |
|-------------|----------|-------------------------------------|------------------------------------------------------|
| `label`     | yes      | any string                          | Human-readable name shown on the canvas              |
| `type`      | yes      | `input`, `output`, `timer`, `counter` | Controls click behaviour and engine handling       |
| `momentary` | no       | `true`                              | Input is active only while the mouse button is held  |

Omitting `momentary` (or setting it to `false`) makes an input latch on each click.

### Bit naming

| Prefix | Type    | Example                    | Derived bits          |
|--------|---------|----------------------------|-----------------------|
| `I0.x` | Input   | `I0.0` … `I0.15`          | —                     |
| `Q0.x` | Output  | `Q0.0` … `Q0.15`          | —                     |
| `Mx`   | Memory  | `M0`, `M1` …              | —                     |
| `Tx`   | Timer   | `T0`, `T1` …              | `T0.DN`, `T0.TT`      |
| `Cx`   | Counter | `C0`, `C1` …              | `C0.DN`               |

Timer and counter derived bits (`.DN`, `.TT`) are created automatically by the engine and do not need to be declared in `bits`.

### Element types in `series`

| JSON `type` | Element      | Extra fields            |
|-------------|--------------|-------------------------|
| `NO`        | Contact (NO) | `bit`                   |
| `NC`        | Contact (NC) | `bit`                   |
| `coil`      | Output coil  | `bit`                   |
| `set`       | Set coil     | `bit`                   |
| `reset`     | Reset coil   | `bit`                   |
| `TON`       | On-delay timer | `bit`, `preset_ms`    |
| `TOF`       | Off-delay timer | `bit`, `preset_ms`   |
| `CTU`       | Count-up counter | `bit`, `preset`     |
| `CTD`       | Count-down counter | `bit`, `preset`   |

Parallel branches are expressed as a dict inside a `series` list:

```json
{"parallel": [
  [ {"type": "NO", "bit": "I0.0"} ],
  [ {"type": "NO", "bit": "Q0.0"} ]
]}
```

## Project Structure

```
ladder_sim/
├── main.py       — Tkinter app, 100 ms scan loop, mouse press/release handler
├── engine.py     — PLC scan engine, timer/counter state, input control
├── elements.py   — Dataclass definitions for Contact, Coil, TON, TOF, CTU, CTD
├── renderer.py   — Canvas drawing, hit-testing, layout constants
├── loader.py     — JSON parser: converts raw dicts to element dataclasses
└── example.json  — Demo program (start/stop + 5 s timer + cycle counter)
```

## Demo Walkthrough

1. Run `python main.py` from the `ladder_sim/` directory.
2. **Press and hold I0.0 (Start)** — Motor `Q0.0` energises; the `Q0.0` sealing contact latches.
3. **Release I0.0** — Motor stays on through the sealing contact.
4. Watch the **TON timer** accumulate run time.
5. **Press and hold I0.1 (Stop)** — the NC Stop contact opens, Motor drops out; the timer pauses and holds its value.
6. **Release I0.1** and press Start again — the timer resumes from where it left off.
7. Click **Reset** in the toolbar to zero the timer and counter at any time.
