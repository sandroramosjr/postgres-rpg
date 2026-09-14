from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Quest:
    id: int
    name: str
    description: str
    target_enemy_id: int
    target_enemy_name: str
    required_kills: int
    exp_reward: int
    gold_reward: int
    min_level: int


@dataclass(slots=True)
class QuestProgress:
    quest: Quest
    status: str
    kills: int
    record_id: int | None = None
    completed_before: bool = False

    @property
    def is_complete(self) -> bool:
        return self.status == "completed"

    def record_kill(self, enemy_id: int) -> bool:
        """Return True if this kill just completed the quest."""
        if self.status != "active" or enemy_id != self.quest.target_enemy_id:
            return False
        self.kills += 1
        if self.kills >= self.quest.required_kills:
            self.status = "completed"
            return True
        return False
