from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class Contact:
    type: str   # "NO" | "NC"
    bit: str


@dataclass
class Coil:
    type: str   # "coil" | "set" | "reset" | "reset_all"
    bit: str = ""


@dataclass
class TimerState:
    preset_ms: int
    accumulated_ms: float = 0.0
    enabled: bool = False
    done: bool = False
    timing: bool = False
    last_time: Optional[float] = None


@dataclass
class TON:
    bit: str
    preset_ms: int


@dataclass
class TOF:
    bit: str
    preset_ms: int


@dataclass
class CounterState:
    preset: int
    count: int = 0
    done: bool = False
    prev_input: bool = False
    initialized: bool = False


@dataclass
class CTU:
    bit: str
    preset: int


@dataclass
class CTD:
    bit: str
    preset: int
