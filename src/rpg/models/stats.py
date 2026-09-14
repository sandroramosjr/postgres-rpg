from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Stats:
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    attack: int
    defense: int
    speed: int

    def apply_bonuses(self, attack: int = 0, defense: int = 0, speed: int = 0, hp: int = 0) -> Stats:
        max_hp = self.max_hp + hp
        return Stats(
            hp=min(self.hp + hp, max_hp),
            max_hp=max_hp,
            mp=self.mp,
            max_mp=self.max_mp,
            attack=self.attack + attack,
            defense=self.defense + defense,
            speed=self.speed + speed,
        )

    def clamp_vitals(self) -> None:
        self.hp = min(self.hp, self.max_hp)
        self.mp = max(0, min(self.mp, self.max_mp))
