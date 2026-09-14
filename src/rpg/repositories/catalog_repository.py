from __future__ import annotations

import psycopg

from rpg.models.character import CharacterClass
from rpg.models.enemy import Enemy
from rpg.models.equipment import Equipment
from rpg.models.skill import Skill
from rpg.models.stats import Stats


class CatalogRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def list_classes(self) -> list[CharacterClass]:
        rows = self.conn.execute(
            """
            SELECT id, name, description, base_hp, base_mp, base_attack, base_defense, base_speed
            FROM character_classes
            ORDER BY id
            """
        ).fetchall()
        return [CharacterClass(**row) for row in rows]

    def list_equipment(self) -> list[Equipment]:
        rows = self.conn.execute(
            """
            SELECT id, name, slot, attack_bonus, defense_bonus, speed_bonus,
                   hp_bonus, price, min_level
            FROM equipment
            ORDER BY min_level, price, name
            """
        ).fetchall()
        return [Equipment(**row) for row in rows]

    def list_enemies(self) -> list[Enemy]:
        rows = self.conn.execute(
            """
            SELECT
                en.id, en.name, en.level, en.hp, en.attack, en.defense, en.speed,
                en.exp_reward, en.gold_reward,
                eq.id AS loot_id, eq.name AS loot_name, eq.slot AS loot_slot,
                eq.attack_bonus AS loot_attack_bonus, eq.defense_bonus AS loot_defense_bonus,
                eq.speed_bonus AS loot_speed_bonus, eq.hp_bonus AS loot_hp_bonus,
                eq.price AS loot_price, eq.min_level AS loot_min_level
            FROM enemies en
            LEFT JOIN equipment eq ON eq.id = en.loot_equipment_id
            ORDER BY en.level, en.name
            """
        ).fetchall()
        enemies: list[Enemy] = []
        for row in rows:
            loot = None
            if row["loot_id"] is not None:
                loot = Equipment(
                    id=row["loot_id"],
                    name=row["loot_name"],
                    slot=row["loot_slot"],
                    attack_bonus=row["loot_attack_bonus"],
                    defense_bonus=row["loot_defense_bonus"],
                    speed_bonus=row["loot_speed_bonus"],
                    hp_bonus=row["loot_hp_bonus"],
                    price=row["loot_price"],
                    min_level=row["loot_min_level"],
                )
            stats = Stats(
                hp=row["hp"],
                max_hp=row["hp"],
                mp=0,
                max_mp=0,
                attack=row["attack"],
                defense=row["defense"],
                speed=row["speed"],
            )
            enemies.append(
                Enemy(
                    enemy_id=row["id"],
                    name=row["name"],
                    level=row["level"],
                    stats=stats,
                    exp_reward=row["exp_reward"],
                    gold_reward=row["gold_reward"],
                    loot=loot,
                )
            )
        return enemies

    def list_skills_for_class(self, class_id: int) -> list[Skill]:
        rows = self.conn.execute(
            """
            SELECT id, name, description, damage_percent, mp_cost, required_level, class_id
            FROM skills
            WHERE class_id = %s
            ORDER BY required_level, name
            """,
            (class_id,),
        ).fetchall()
        return [Skill(**row) for row in rows]
