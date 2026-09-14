from __future__ import annotations

import random
from dataclasses import dataclass

from rpg.models.character import Character
from rpg.models.enemy import Enemy
from rpg.models.skill import Skill
from rpg.models.stats import Stats


@dataclass(slots=True)
class BattleLog:
    outcome: str
    turns: int
    damage_dealt: int
    damage_taken: int
    lines: list[str]


class CombatEngine:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    def roll_damage(self, attacker: Stats, defender: Stats, multiplier: float = 1.0) -> int:
        variance = self.rng.randint(-2, 2)
        raw = int((attacker.attack - defender.defense // 2 + variance) * multiplier)
        return max(1, raw)

    def player_basic_attack(self, player: Character, enemy: Enemy) -> tuple[int, str]:
        dmg = self.roll_damage(player.effective_stats(), enemy.effective_stats())
        applied = enemy.take_damage(dmg)
        return applied, f"{player.name} atingiu {enemy.name} e causou {applied} de dano."

    def player_skill_attack(
        self, player: Character, enemy: Enemy, skill: Skill
    ) -> tuple[int, str]:
        if player.stats.mp < skill.mp_cost:
            return 0, f"{player.name} não tem MP suficiente para {skill.name}."
        player.stats.mp -= skill.mp_cost
        dmg = self.roll_damage(
            player.effective_stats(), enemy.effective_stats(), skill.multiplier()
        )
        applied = enemy.take_damage(dmg)
        return applied, f"{player.name} usou {skill.name} em {enemy.name} e causou {applied} de dano."

    def enemy_attack(self, enemy: Enemy, player: Character) -> tuple[int, str]:
        dmg = self.roll_damage(enemy.effective_stats(), player.effective_stats())
        applied = player.take_damage(dmg)
        return applied, f"{enemy.name} atingiu {player.name} e causou {applied} de dano."

    def player_goes_first(self, player: Character, enemy: Enemy) -> bool:
        return player.effective_stats().speed >= enemy.effective_stats().speed
