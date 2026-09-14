from __future__ import annotations

from abc import ABC, abstractmethod

from rpg.models.stats import Stats


class LivingEntity(ABC):
    """Shared combatant contract for player characters and enemies."""

    def __init__(self, name: str, stats: Stats) -> None:
        self.name = name
        self.stats = stats

    @property
    def is_alive(self) -> bool:
        return self.stats.hp > 0

    def take_damage(self, amount: int) -> int:
        applied = max(0, amount)
        self.stats.hp = max(0, self.stats.hp - applied)
        return applied

    def heal_full(self) -> None:
        self.stats.hp = self.stats.max_hp
        self.stats.mp = self.stats.max_mp

    @abstractmethod
    def effective_stats(self) -> Stats:
        """Stats after equipment or other modifiers."""
