# CLAUDE.md — Ladder Logic Simulator

Guidelines and architecture notes for AI-assisted development.

## Project Overview

Desktop Python PLC ladder logic simulator using Tkinter. Reads a JSON program file and runs a 100 ms scan loop that evaluates ladder rungs exactly as a real PLC would. The UI renders energised paths in green and allows the user to interact with input contacts using the mouse.

## Running the Simulator

```bash
cd ladder_sim
python main.py              # uses example.json
python main.py myprogram.json
```

Requires only the Python standard library (Python 3.10+, Tkinter included on Windows).

## File Structure

```
ladder_sim/
├── main.py       — LadderApp (Tk root), scan loop, mouse press/release handler
├── engine.py     — PLCEngine: scan(), toggle_input(), set_input(), reset_timers_and_counters()
├── elements.py   — Dataclasses: Contact, Coil, TON, TOF, CTU, CTD, TimerState, CounterState
├── renderer.py   — LadderRenderer: draw(), hit_test(), all canvas drawing logic
├── loader.py     — load(path) → parses JSON into element dataclasses
└── example.json  — Start/Stop + TON timer + CTU counter demo
```

## Architecture

### Scan Loop (`main.py`)

`LadderApp.scan_loop()` fires every 100 ms via `self.after(SCAN_MS, self.scan_loop)`. Each tick:
1. `engine.scan()` — evaluates all rungs and updates `engine.bits`
2. `renderer.draw()` — redraws the canvas using current bit states
3. `_update_scroll_region()` — adjusts scrollbars to fit content

### Engine (`engine.py`)

- `PLCEngine.bits: dict[str, bool]` — single source of truth for all tag values
- `PLCEngine.bit_meta: dict[str, dict]` — raw JSON metadata (label, type, momentary)
- `PLCEngine.timers / .counters` — `TimerState` / `CounterState` instances, keyed by bit name
- `scan()` calls `_eval_series()` for each rung; timers use `time.monotonic()` for elapsed ms
- `toggle_input(bit)` — flips a bit with `type == "input"` (used for latching inputs)
- `set_input(bit, state)` — sets a bit with `type == "input"` to an explicit state (used for momentary inputs)
- `reset_timers_and_counters()` — zeroes all timer accumulated values and counter counts, clears all `.DN`/`.TT` bits; called by the `reset_all` coil in the ladder program

### Renderer (`renderer.py`)

Reads energisation from `engine.bits` directly — no separate pass needed. Layout constants:

| Constant       | Value | Meaning                              |
|----------------|-------|--------------------------------------|
| `CELL_W`       | 90    | Pixels wide per element cell         |
| `CELL_H`       | 80    | Base rung height in pixels           |
| `BRANCH_H`     | 50    | Extra height per parallel branch     |
| `RAIL_X`       | 30    | X position of left power rail        |
| `RIGHT_MARGIN` | 40    | Gap between last element and right rail |
| `RUNG_TOP`     | 20    | Y offset for the first rung          |
| `COMMENT_H`    | 18    | Height reserved for rung comment text |

`hit_test(px, py)` searches `self.clickables` (populated during `draw()`) and returns the bit name for any input contact the mouse is over, or `None`.

### Loader (`loader.py`)

`load(path)` reads JSON and converts raw element dicts into typed dataclasses. Returns:
```python
{
    "title": str,
    "bits":  dict[str, dict],   # raw metadata — not converted
    "rungs": list[dict],         # each has "comment" and "series" (dataclass list)
}
```

Parallel blocks are left as `{"parallel": [[...], [...]]}` dicts in the series list so the engine and renderer can distinguish them from element dataclasses.

### Reset (`reset_all` coil)

There is no toolbar. Timers and counters are reset entirely from within the ladder program using the `reset_all` coil type. When a rung driving a `reset_all` coil is energised, the engine calls `reset_timers_and_counters()` as a side effect — no bit is written. In `example.json`, a momentary `I0.2` input contact drives the `reset_all` coil.

### Mouse Interaction (`main.py`)

Two bindings on the canvas:
- `<Button-1>` -> `on_click`: hits `renderer.hit_test()`; if the bit has `"momentary": true` in metadata, calls `engine.set_input(bit, True)` and stores bit in `self._held_momentary`; otherwise calls `engine.toggle_input(bit)`
- `<ButtonRelease-1>` -> `on_release`: if `_held_momentary` is set, calls `engine.set_input(bit, False)` to release it

## JSON Program Schema

### Top Level

```json
{
  "title": "string",
  "bits":  { "<tag>": { ... } },
  "rungs": [ { ... } ]
}
```

### Bit Declaration

```json
"<tag>": {
  "label":     "string",          // displayed on canvas
  "type":      "input|output|timer|counter",
  "momentary": true               // optional; input active only while mouse held
}
```

### Rung

```json
{
  "comment": "string",   // optional; shown above rung in italics
  "series":  [ <elements> ]
}
```

### Element Types

| JSON `type`  | Dataclass | Extra fields             |
|--------------|-----------|--------------------------|
| `NO`         | `Contact` | `bit`                    |
| `NC`         | `Contact` | `bit`                    |
| `coil`       | `Coil`    | `bit`                    |
| `set`        | `Coil`    | `bit`                    |
| `reset`      | `Coil`    | `bit`                    |
| `reset_all`  | `Coil`    | *(none)*                 |
| `TON`        | `TON`     | `bit`, `preset_ms`       |
| `TOF`        | `TOF`     | `bit`, `preset_ms`       |
| `CTU`        | `CTU`     | `bit`, `preset`          |
| `CTD`        | `CTD`     | `bit`, `preset`          |
| *(parallel)* | dict      | `"parallel": [[...]]`    |

### Bit Naming Conventions

| Prefix | Type    | Derived bits created by engine |
|--------|---------|-------------------------------|
| `I0.x` | Input   | —                             |
| `Q0.x` | Output  | —                             |
| `Mx`   | Memory  | —                             |
| `Tx`   | Timer   | `T0.DN`, `T0.TT`              |
| `Cx`   | Counter | `C0.DN`                       |

## Development Guidelines

### Adding a New Element Type

1. Add a dataclass to `elements.py`
2. Add a parsing branch in `loader.py:_parse_element()`
3. Add initialisation in `engine.py:_init_series()` if it has runtime state
4. Add evaluation in `engine.py:_eval_series()`
5. Add a draw method in `renderer.py` and call it from `_draw_series()`

### TON Timer Behaviour

The TON in this simulator does **not** follow standard IEC 61131-3 semantics:
- ACC accumulates freely while the input is energised (no cap at preset)
- DN is never set; the timer never fires automatically
- When the input de-energises, ACC **holds** its current value (does not reset)
- ACC only resets to zero via `reset_timers_and_counters()` (triggered by the `reset_all` coil)

The timer acts as a pausable run-time accumulator. `preset_ms` is stored but neither displayed nor used in control logic.

### Cycle Counter Pattern

The cycle counter (C0) uses a `NC Q0.0` contact feeding the CTU. Because the NC contact closes when Q0.0 goes False, the CTU sees a rising edge exactly when the motor transitions from running to stopped. This is pure ladder logic — no engine changes are needed to detect falling edges on output bits.

Counter counts start at 0. `CounterState` carries an `initialized` flag: on the first scan (and after any reset), the engine skips the rising-edge check and just records the initial input state. This prevents the NC contact's already-closed state from being counted as a spurious first edge on startup or after a reset.

Timer and counter blocks display only the type/bit header and live value (ACC ms or CNT). PRE and DN are not shown.

### Modifying the Scan Loop

Do not add blocking calls inside `scan_loop()`. All state updates must complete within the 100 ms window. Timer accuracy depends on `time.monotonic()` deltas, not on the Tkinter callback interval.

### Extending Bit Metadata

Bit metadata from the JSON `bits` section is passed through to `engine.bit_meta` as raw dicts. New flags (like `"momentary"`) can be added to the JSON and read in `main.py` or `renderer.py` without changes to `loader.py` or `engine.py`.

### Canvas Drawing

Always call `canvas.delete("all")` at the start of `draw()` and rebuild `self.clickables` from scratch. Do not cache canvas item IDs across frames.
