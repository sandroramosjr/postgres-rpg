from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Skill:
    id: int
    name: str
    description: str
    damage_percent: int
    mp_cost: int
    required_level: int
    class_id: int | None

    def multiplier(self) -> float:
        return self.damage_percent / 100.0
