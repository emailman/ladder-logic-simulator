import json
from elements import Contact, Coil, TON, TOF, CTU, CTD


def _parse_element(raw):
    """Convert a raw dict element into a dataclass instance, or return a parallel block dict."""
    if "parallel" in raw:
        return {"parallel": [_parse_series(branch) for branch in raw["parallel"]]}

    t = raw.get("type", "")
    if t in ("NO", "NC"):
        return Contact(type=t, bit=raw["bit"])
    if t in ("coil", "set", "reset"):
        return Coil(type=t, bit=raw["bit"])
    if t == "TON":
        return TON(bit=raw["bit"], preset_ms=raw["preset_ms"])
    if t == "TOF":
        return TOF(bit=raw["bit"], preset_ms=raw["preset_ms"])
    if t == "CTU":
        return CTU(bit=raw["bit"], preset=raw["preset"])
    if t == "CTD":
        return CTD(bit=raw["bit"], preset=raw["preset"])
    raise ValueError(f"Unknown element type: {t!r}")


def _parse_series(raw_list):
    return [_parse_element(e) for e in raw_list]


def load(path: str) -> dict:
    """Load and parse a ladder program JSON file.

    Returns a dict with keys:
      title  : str
      bits   : dict[str, dict]  — raw bit metadata from JSON
      rungs  : list[dict]       — each rung has 'comment' and 'series'
    """
    with open(path, "r") as f:
        data = json.load(f)

    rungs = []
    for raw_rung in data.get("rungs", []):
        rungs.append({
            "comment": raw_rung.get("comment", ""),
            "series": _parse_series(raw_rung["series"]),
        })

    return {
        "title": data.get("title", "Ladder Program"),
        "bits": data.get("bits", {}),
        "rungs": rungs,
    }
