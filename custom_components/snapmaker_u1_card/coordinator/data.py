"""Snapshot of the printer state handed to entities and the card."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class U1Data:
    """Everything the entities and the card need from one poll."""
    online: bool = False
    slots: list[dict[str, Any]] = field(default_factory=list)
    preferences: dict[str, bool] = field(default_factory=dict)
    map_table: list[int] = field(default_factory=list)
    files: list[dict[str, Any]] = field(default_factory=list)
    files_updated: float | None = None
    # Tool changes: None if the firmware provides no counters.
    tool_changes: dict[str, Any] | None = None
    print_state: str | None = None
    temperatures: list[float] = field(default_factory=list)
    targets: list[float] = field(default_factory=list)
    # {"current": {switches, energy, energy_cost}, "active": {...} | None, "last": {...} | None}
    prints: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    timelapses: list[dict[str, Any]] = field(default_factory=list)
    # Spoolman: None if not configured
    spoolman: dict[str, Any] | None = None
    # Open firmware exceptions in plain language (errors.py)
    errors: list[dict[str, Any]] = field(default_factory=list)
    queue: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] | None = None
    maintenance: list[dict[str, Any]] = field(default_factory=list)
    print_hours: float | None = None
    archive: dict[str, Any] | None = None
    # Active head according to the firmware (toolhead.extruder), 0-3; None = unknown
    active_head: int | None = None
    cpu_count: int | None = None
    all_files: list[dict[str, Any]] = field(default_factory=list)
    backup: dict[str, Any] | None = None
    # Running print: file progress 0-1, duration in s, layer (for voice answers)
    progress: float | None = None
    # Remaining time in s (file time profile, else file progress) and finish time
    remaining: float | None = None
    eta: float | None = None
    # Spool runs out during the print: {head: {"minutes", "takeover"}}
    runout: dict[int, dict[str, Any]] = field(default_factory=dict)
    print_duration: float | None = None
    layer: int | None = None
    total_layers: int | None = None
    # Machine controls (machine.py): flow in %, loaded bed mesh, top cover, head park states
    flow: float | None = None
    bed_mesh: dict[str, Any] | None = None
    purifier: dict[str, Any] | None = None
    head_states: list[str | None] = field(default_factory=list)
    # Chamber heater (Panda Breath / DragonBreath via paxx12): None without one
    chamber: dict[str, Any] | None = None
