from __future__ import annotations

from dataclasses import dataclass

from rpg.models.entity import LivingEntity
from rpg.models.equipment import Equipment, Inventory
from rpg.models.quest import QuestProgress
from rpg.models.skill import Skill
from rpg.models.stats import Stats

EXP_PER_LEVEL = 100
GOLD_PER_LEVEL = 25


@dataclass(frozen=True, slots=True)
class CharacterClass:
    id: int
    name: str
    description: str
    base_hp: int
    base_mp: int
    base_attack: int
    base_defense: int
    base_speed: int


class Character(LivingEntity):
    def __init__(
        self,
        *,
        name: str,
        character_class: CharacterClass,
        stats: Stats,
        level: int = 1,
        exp: int = 0,
        gold: int = 0,
        character_id: int | None = None,
    ) -> None:
        super().__init__(name, stats)
        self.id = character_id
        self.character_class = character_class
        self.level = level
        self.exp = exp
        self.gold = gold
        self.inventory = Inventory()
        self.equipped: dict[str, Equipment] = {}
        self.skills: list[Skill] = []
        self.quests: list[QuestProgress] = []

    def effective_stats(self) -> Stats:
        bonuses = {"attack": 0, "defense": 0, "speed": 0, "hp": 0}
        for item in self.equipped.values():
            bonuses["attack"] += item.attack_bonus
            bonuses["defense"] += item.defense_bonus
            bonuses["speed"] += item.speed_bonus
            bonuses["hp"] += item.hp_bonus
        return self.stats.apply_bonuses(**bonuses)

    @property
    def is_alive(self) -> bool:
        return self.effective_stats().hp > 0

    def take_damage(self, amount: int) -> int:
        hp_bonus = sum(item.hp_bonus for item in self.equipped.values())
        current_hp = self.effective_stats().hp
        applied = max(0, min(amount, current_hp))
        self.stats.hp = current_hp - applied - hp_bonus
        return applied

    def exp_to_next_level(self) -> int:
        return self.level * EXP_PER_LEVEL

    def gain_exp(self, amount: int) -> list[int]:
        """Add EXP and return a list of new levels reached."""
        self.exp += max(0, amount)
        leveled: list[int] = []
        while self.exp >= self.exp_to_next_level():
            self.exp -= self.exp_to_next_level()
            self.level += 1
            self._apply_level_up()
            leveled.append(self.level)
        return leveled

    def _apply_level_up(self) -> None:
        self.stats.max_hp += 6
        self.stats.max_mp += 3
        self.stats.attack += 2
        self.stats.defense += 2
        self.stats.speed += 1
        self.gold += GOLD_PER_LEVEL
        self.heal_full()

    def add_gold(self, amount: int) -> None:
        self.gold += max(0, amount)

    def spend_gold(self, amount: int) -> bool:
        if amount > self.gold:
            return False
        self.gold -= amount
        return True

    def learn_skill(self, skill: Skill) -> bool:
        if any(existing.id == skill.id for existing in self.skills):
            return False
        if skill.class_id not in (None, self.character_class.id):
            return False
        if self.level < skill.required_level:
            return False
        self.skills.append(skill)
        return True

    def equip(self, equipment_id: int) -> Equipment | None:
        item = self.inventory.get(equipment_id)
        if item is None or self.level < item.min_level:
            return None
        self.equipped[item.slot] = item
        return item

    def unequip(self, slot: str) -> Equipment | None:
        return self.equipped.pop(slot, None)

    def accept_quest(self, quest) -> QuestProgress | None:
        if self.level < quest.min_level:
            return None
        if any(
            progress.quest.id == quest.id and progress.status == "active"
            for progress in self.quests
        ):
            return None
        progress = QuestProgress(
            quest=quest,
            status="active",
            kills=0,
            completed_before=any(
                previous.quest.id == quest.id and previous.is_complete
                for previous in self.quests
            ),
        )
        self.quests.append(progress)
        return progress

    def active_quests(self) -> list[QuestProgress]:
        return [quest for quest in self.quests if quest.status == "active"]

    def record_enemy_kill(self, enemy_id: int) -> list[QuestProgress]:
        completed: list[QuestProgress] = []
        for progress in self.active_quests():
            if progress.record_kill(enemy_id):
                self.gain_exp(progress.quest.exp_reward)
                self.add_gold(progress.quest.gold_reward)
                completed.append(progress)
        return completed
