from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BattleRecord:
    id: int
    enemy_name: str
    outcome: str
    turns: int
    damage_dealt: int
    damage_taken: int
    exp_gained: int
    gold_gained: int
    fought_at: datetime
