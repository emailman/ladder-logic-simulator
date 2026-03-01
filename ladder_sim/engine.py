import time
from elements import Contact, Coil, TON, TOF, CTU, CTD, TimerState, CounterState


class PLCEngine:
    def __init__(self, program: dict):
        self.rungs = program["rungs"]
        self.bit_meta = program["bits"]   # metadata (label, type) — not state

        # All boolean bit states: inputs, outputs, memory, timer done/tt, counter done
        self.bits: dict[str, bool] = {name: False for name in self.bit_meta}

        # Runtime state for timers and counters
        self.timers: dict[str, TimerState] = {}
        self.counters: dict[str, CounterState] = {}

        self._init_runtime()

    def _init_runtime(self):
        for rung in self.rungs:
            self._init_series(rung["series"])

    def _init_series(self, series):
        for elem in series:
            if isinstance(elem, dict) and "parallel" in elem:
                for branch in elem["parallel"]:
                    self._init_series(branch)
            elif isinstance(elem, TON):
                self.timers[elem.bit] = TimerState(preset_ms=elem.preset_ms)
                self.bits.setdefault(elem.bit + ".DN", False)
                self.bits.setdefault(elem.bit + ".TT", False)
            elif isinstance(elem, TOF):
                self.timers[elem.bit] = TimerState(preset_ms=elem.preset_ms)
                self.bits.setdefault(elem.bit + ".DN", False)
                self.bits.setdefault(elem.bit + ".TT", False)
            elif isinstance(elem, CTU) or isinstance(elem, CTD):
                if elem.bit not in self.counters:
                    self.counters[elem.bit] = CounterState(preset=elem.preset)
                self.bits.setdefault(elem.bit + ".DN", False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def toggle_input(self, bit: str):
        """Toggle a bit that has type 'input' in the program metadata."""
        meta = self.bit_meta.get(bit, {})
        if meta.get("type") == "input":
            self.bits[bit] = not self.bits.get(bit, False)

    def set_input(self, bit: str, state: bool):
        """Set a bit that has type 'input' to an explicit state."""
        meta = self.bit_meta.get(bit, {})
        if meta.get("type") == "input":
            self.bits[bit] = state

    def scan(self):
        """Run one PLC scan cycle."""
        now = time.monotonic()
        for rung in self.rungs:
            self._eval_series(rung["series"], now)

    # ------------------------------------------------------------------
    # Evaluation helpers
    # ------------------------------------------------------------------

    def _eval_series(self, series, now: float) -> bool:
        """Evaluate a series list; return the power rail state."""
        power = True
        for elem in series:
            if not power and not isinstance(elem, (Coil, TON, TOF, CTU, CTD)):
                # Short-circuit: skip contacts in a de-energised rung
                pass
            if isinstance(elem, dict) and "parallel" in elem:
                branch_power = any(self._eval_series(branch, now) for branch in elem["parallel"])
                power = power and branch_power
            elif isinstance(elem, Contact):
                bit_val = self.bits.get(elem.bit, False)
                if elem.type == "NC":
                    bit_val = not bit_val
                power = power and bit_val
            elif isinstance(elem, Coil):
                self._exec_coil(elem, power)
            elif isinstance(elem, TON):
                self._exec_ton(elem, power, now)
            elif isinstance(elem, TOF):
                self._exec_tof(elem, power, now)
            elif isinstance(elem, CTU):
                self._exec_ctu(elem, power)
            elif isinstance(elem, CTD):
                self._exec_ctd(elem, power)
        return power

    def _exec_coil(self, elem: Coil, power: bool):
        if elem.type == "coil":
            self.bits[elem.bit] = power
        elif elem.type == "set":
            if power:
                self.bits[elem.bit] = True
        elif elem.type == "reset":
            if power:
                self.bits[elem.bit] = False
                # Also reset counter accumulator if this bit is a counter
                if elem.bit in self.counters:
                    self.counters[elem.bit].count = 0
                    self.counters[elem.bit].done = False
                    self.bits[elem.bit + ".DN"] = False

    def _exec_ton(self, elem: TON, power: bool, now: float):
        ts = self.timers[elem.bit]
        if power:
            if ts.last_time is None:
                ts.last_time = now
            elapsed = (now - ts.last_time) * 1000.0  # ms
            ts.last_time = now
            ts.accumulated_ms = min(ts.accumulated_ms + elapsed, elem.preset_ms)
            ts.timing = ts.accumulated_ms < elem.preset_ms
            ts.done = ts.accumulated_ms >= elem.preset_ms
        else:
            ts.accumulated_ms = 0.0
            ts.done = False
            ts.timing = False
            ts.last_time = None

        ts.enabled = power
        self.bits[elem.bit + ".DN"] = ts.done
        self.bits[elem.bit + ".TT"] = ts.timing

    def _exec_tof(self, elem: TOF, power: bool, now: float):
        ts = self.timers[elem.bit]
        if power:
            ts.accumulated_ms = 0.0
            ts.done = True
            ts.timing = False
            ts.last_time = None
        else:
            if ts.last_time is None:
                ts.last_time = now
            elapsed = (now - ts.last_time) * 1000.0
            ts.last_time = now
            ts.accumulated_ms = min(ts.accumulated_ms + elapsed, elem.preset_ms)
            ts.timing = ts.accumulated_ms < elem.preset_ms
            ts.done = ts.accumulated_ms < elem.preset_ms  # output stays on while timing

        ts.enabled = power
        self.bits[elem.bit + ".DN"] = ts.done
        self.bits[elem.bit + ".TT"] = ts.timing

    def _exec_ctu(self, elem: CTU, power: bool):
        cs = self.counters[elem.bit]
        if power and not cs.prev_input:
            cs.count += 1
            cs.done = cs.count >= elem.preset
        cs.prev_input = power
        self.bits[elem.bit + ".DN"] = cs.done

    def _exec_ctd(self, elem: CTD, power: bool):
        cs = self.counters[elem.bit]
        if power and not cs.prev_input:
            cs.count = max(cs.count - 1, 0)
            cs.done = cs.count >= elem.preset
        cs.prev_input = power
        self.bits[elem.bit + ".DN"] = cs.done
