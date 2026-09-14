from __future__ import annotations

from rpg.models.entity import LivingEntity
from rpg.models.equipment import Equipment
from rpg.models.stats import Stats


class Enemy(LivingEntity):
    def __init__(
        self,
        *,
        enemy_id: int,
        name: str,
        level: int,
        stats: Stats,
        exp_reward: int,
        gold_reward: int,
        loot: Equipment | None = None,
    ) -> None:
        super().__init__(name, stats)
        self.id = enemy_id
        self.level = level
        self.exp_reward = exp_reward
        self.gold_reward = gold_reward
        self.loot = loot

    def effective_stats(self) -> Stats:
        return self.stats

    def clone(self) -> Enemy:
        """Fresh combat instance so catalog rows are not mutated."""
        fresh = Stats(
            hp=self.stats.max_hp,
            max_hp=self.stats.max_hp,
            mp=0,
            max_mp=0,
            attack=self.stats.attack,
            defense=self.stats.defense,
            speed=self.stats.speed,
        )
        return Enemy(
            enemy_id=self.id,
            name=self.name,
            level=self.level,
            stats=fresh,
            exp_reward=self.exp_reward,
            gold_reward=self.gold_reward,
            loot=self.loot,
        )
