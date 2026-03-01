# Ladder Logic Simulator

A desktop PLC ladder logic simulator written in Python using Tkinter. Loads a ladder program from a JSON file and runs a continuous scan cycle — just like a real PLC.

![Ladder Logic Simulator](https://raw.githubusercontent.com/emailman/ladder-logic-simulator/master/docs/screenshot.png)

## Features

- **Continuous scan cycle** — 100 ms scan loop mimicking real PLC behaviour
- **Live energisation highlighting** — energised paths drawn in green, de-energised in grey
- **Clickable input contacts** — toggle inputs directly on the canvas
- **Supported instructions:**
  - `NO` / `NC` contacts (normally open / normally closed)
  - `coil` / `set` / `reset` output coils
  - `TON` / `TOF` timers (on-delay / off-delay) with live accumulated value display
  - `CTU` / `CTD` counters (up / down) with rising-edge detection
  - Parallel branches (any number of rungs in parallel)

## Requirements

- Python 3.10+ (uses `match`-free dataclasses; compatible with 3.10+)
- Tkinter (included with standard Python on Windows and most Linux distros)

No third-party packages required.

## Usage

```bash
cd ladder_sim
python main.py                  # loads example.json
python main.py myprogram.json   # loads a custom program
```

## JSON Program Format

Programs are defined in JSON. Example:

```json
{
  "title": "My Ladder Program",
  "bits": {
    "I0.0": {"label": "Start",  "type": "input"},
    "I0.1": {"label": "Stop",   "type": "input"},
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

### Bit naming

| Prefix | Type    | Example           |
|--------|---------|-------------------|
| `I0.x` | Input   | `I0.0` … `I0.15`  |
| `Q0.x` | Output  | `Q0.0` … `Q0.15`  |
| `Mx`   | Memory  | `M0`, `M1` …      |
| `Tx`   | Timer   | `T0`, `T0.DN`, `T0.TT` |
| `Cx`   | Counter | `C0`, `C0.DN`     |

## Project Structure

```
ladder_sim/
├── main.py       — Tkinter app, scan loop, click handler
├── engine.py     — PLC scan engine, timer/counter state
├── elements.py   — Dataclass definitions for each element type
├── renderer.py   — Canvas drawing and hit-test for clicks
├── loader.py     — JSON parser and validation
└── example.json  — Demo program (start/stop + timer + counter)
```

## Demo Walkthrough

1. Run `python main.py`
2. Click **I0.0 (Start)** — Motor `Q0.0` energises and seals itself
3. Click **I0.0** again to release — Motor stays on via the sealing contact
4. Click **I0.1 (Stop)** — Motor drops out
5. Re-latch and watch the **TON timer** accumulate toward 5000 ms
6. When `T0.DN` fires, the **CTU counter** increments
