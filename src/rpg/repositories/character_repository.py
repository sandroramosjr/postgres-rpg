from __future__ import annotations

import psycopg

from rpg.models.character import Character, CharacterClass
from rpg.models.equipment import Equipment
from rpg.models.quest import Quest, QuestProgress
from rpg.models.skill import Skill
from rpg.models.stats import Stats


def _class_from_row(row: dict) -> CharacterClass:
    return CharacterClass(
        id=row["class_id"],
        name=row["class_name"],
        description=row["class_description"],
        base_hp=row["base_hp"],
        base_mp=row["base_mp"],
        base_attack=row["base_attack"],
        base_defense=row["base_defense"],
        base_speed=row["base_speed"],
    )


def _equipment_from_row(row: dict, prefix: str = "") -> Equipment:
    return Equipment(
        id=row[f"{prefix}id"],
        name=row[f"{prefix}name"],
        slot=row[f"{prefix}slot"],
        attack_bonus=row[f"{prefix}attack_bonus"],
        defense_bonus=row[f"{prefix}defense_bonus"],
        speed_bonus=row[f"{prefix}speed_bonus"],
        hp_bonus=row[f"{prefix}hp_bonus"],
        price=row[f"{prefix}price"],
        min_level=row[f"{prefix}min_level"],
    )


class CharacterRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def list_names(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM characters ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]

    def delete_by_name(self, name: str) -> bool:
        row = self.conn.execute(
            "DELETE FROM characters WHERE name = %s RETURNING id",
            (name,),
        ).fetchone()
        return row is not None

    def create(self, name: str, character_class: CharacterClass) -> Character:
        stats = Stats(
            hp=character_class.base_hp,
            max_hp=character_class.base_hp,
            mp=character_class.base_mp,
            max_mp=character_class.base_mp,
            attack=character_class.base_attack,
            defense=character_class.base_defense,
            speed=character_class.base_speed,
        )
        row = self.conn.execute(
            """
            INSERT INTO characters (
                name, class_id, level, exp, gold,
                hp, max_hp, mp, max_mp, attack, defense, speed
            )
            VALUES (%s, %s, 1, 0, 20, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                name,
                character_class.id,
                stats.hp,
                stats.max_hp,
                stats.mp,
                stats.max_mp,
                stats.attack,
                stats.defense,
                stats.speed,
            ),
        ).fetchone()
        character = Character(
            name=name,
            character_class=character_class,
            stats=stats,
            gold=20,
            character_id=row["id"],
        )
        self._grant_starting_gear(character)
        self._sync_class_skills(character)
        self.save(character)
        return character

    def load_by_name(self, name: str) -> Character | None:
        row = self.conn.execute(
            """
            SELECT
                c.id, c.name, c.level, c.exp, c.gold,
                c.hp, c.max_hp, c.mp, c.max_mp, c.attack, c.defense, c.speed,
                cc.id AS class_id, cc.name AS class_name, cc.description AS class_description,
                cc.base_hp, cc.base_mp, cc.base_attack, cc.base_defense, cc.base_speed
            FROM characters c
            JOIN character_classes cc ON cc.id = c.class_id
            WHERE c.name = %s
            """,
            (name,),
        ).fetchone()
        if row is None:
            return None
        character = Character(
            name=row["name"],
            character_class=_class_from_row(row),
            stats=Stats(
                hp=row["hp"],
                max_hp=row["max_hp"],
                mp=row["mp"],
                max_mp=row["max_mp"],
                attack=row["attack"],
                defense=row["defense"],
                speed=row["speed"],
            ),
            level=row["level"],
            exp=row["exp"],
            gold=row["gold"],
            character_id=row["id"],
        )
        self._hydrate_inventory(character)
        self._hydrate_equipped(character)
        self._hydrate_skills(character)
        self._hydrate_quests(character)
        return character

    def save(self, character: Character) -> None:
        if character.id is None:
            raise ValueError("Cannot save a character without an id")
        character.stats.clamp_vitals()
        self.conn.execute(
            """
            UPDATE characters SET
                level = %s, exp = %s, gold = %s,
                hp = %s, max_hp = %s, mp = %s, max_mp = %s,
                attack = %s, defense = %s, speed = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                character.level,
                character.exp,
                character.gold,
                character.stats.hp,
                character.stats.max_hp,
                character.stats.mp,
                character.stats.max_mp,
                character.stats.attack,
                character.stats.defense,
                character.stats.speed,
                character.id,
            ),
        )
        self.conn.execute("DELETE FROM inventory WHERE character_id = %s", (character.id,))
        for item, quantity in character.inventory.all_items():
            self.conn.execute(
                """
                INSERT INTO inventory (character_id, equipment_id, quantity)
                VALUES (%s, %s, %s)
                """,
                (character.id, item.id, quantity),
            )
        self.conn.execute("DELETE FROM equipped_items WHERE character_id = %s", (character.id,))
        for slot, item in character.equipped.items():
            self.conn.execute(
                """
                INSERT INTO equipped_items (character_id, slot, equipment_id)
                VALUES (%s, %s, %s)
                """,
                (character.id, slot, item.id),
            )
        self.conn.execute("DELETE FROM character_skills WHERE character_id = %s", (character.id,))
        for skill in character.skills:
            self.conn.execute(
                """
                INSERT INTO character_skills (character_id, skill_id)
                VALUES (%s, %s)
                """,
                (character.id, skill.id),
            )
        for progress in character.quests:
            if progress.record_id is None:
                row = self.conn.execute(
                    """
                    INSERT INTO character_quests (
                        character_id, quest_id, status, kills, completed_at
                    )
                    VALUES (%s, %s, %s, %s,
                            CASE WHEN %s = 'completed' THEN NOW() ELSE NULL END)
                    RETURNING id
                    """,
                    (
                        character.id,
                        progress.quest.id,
                        progress.status,
                        progress.kills,
                        progress.status,
                    ),
                ).fetchone()
                progress.record_id = row["id"]
            else:
                self.conn.execute(
                    """
                    UPDATE character_quests
                    SET status = %s, kills = %s,
                        completed_at = CASE
                            WHEN %s = 'completed' AND completed_at IS NULL THEN NOW()
                            ELSE completed_at
                        END
                    WHERE id = %s
                    """,
                    (
                        progress.status,
                        progress.kills,
                        progress.status,
                        progress.record_id,
                    ),
                )

    def _grant_starting_gear(self, character: Character) -> None:
        starter = self.conn.execute(
            """
            SELECT id, name, slot, attack_bonus, defense_bonus, speed_bonus,
                   hp_bonus, price, min_level
            FROM equipment
            WHERE name IN ('Espada Enferrujada', 'Colete de Couro')
            """
        ).fetchall()
        for row in starter:
            item = _equipment_from_row(row)
            character.inventory.add(item)
            character.equip(item.id)

    def _sync_class_skills(self, character: Character) -> None:
        rows = self.conn.execute(
            """
            SELECT id, name, description, damage_percent, mp_cost, required_level, class_id
            FROM skills
            WHERE class_id = %s AND required_level <= %s
            """,
            (character.character_class.id, character.level),
        ).fetchall()
        for row in rows:
            character.learn_skill(Skill(**row))

    def _hydrate_inventory(self, character: Character) -> None:
        rows = self.conn.execute(
            """
            SELECT e.id, e.name, e.slot, e.attack_bonus, e.defense_bonus, e.speed_bonus,
                   e.hp_bonus, e.price, e.min_level, i.quantity
            FROM inventory i
            JOIN equipment e ON e.id = i.equipment_id
            WHERE i.character_id = %s
            """,
            (character.id,),
        ).fetchall()
        for row in rows:
            item = _equipment_from_row(row)
            character.inventory.add(item, row["quantity"])

    def _hydrate_equipped(self, character: Character) -> None:
        rows = self.conn.execute(
            """
            SELECT e.id, e.name, e.slot, e.attack_bonus, e.defense_bonus, e.speed_bonus,
                   e.hp_bonus, e.price, e.min_level
            FROM equipped_items eq
            JOIN equipment e ON e.id = eq.equipment_id
            WHERE eq.character_id = %s
            """,
            (character.id,),
        ).fetchall()
        for row in rows:
            item = _equipment_from_row(row)
            if character.inventory.get(item.id) is None:
                character.inventory.add(item)
            character.equipped[item.slot] = item

    def _hydrate_skills(self, character: Character) -> None:
        rows = self.conn.execute(
            """
            SELECT s.id, s.name, s.description, s.damage_percent, s.mp_cost,
                   s.required_level, s.class_id
            FROM character_skills cs
            JOIN skills s ON s.id = cs.skill_id
            WHERE cs.character_id = %s
            ORDER BY s.required_level, s.name
            """,
            (character.id,),
        ).fetchall()
        character.skills = [Skill(**row) for row in rows]
        self._sync_class_skills(character)

    def _hydrate_quests(self, character: Character) -> None:
        rows = self.conn.execute(
            """
            SELECT
                cq.id, q.id AS quest_id, q.name, q.description,
                q.target_enemy_id, e.name AS target_enemy_name,
                q.required_kills, q.exp_reward, q.gold_reward, q.min_level,
                                cq.status, cq.kills,
                                EXISTS (
                                        SELECT 1
                                        FROM character_quests previous
                                        WHERE previous.character_id = cq.character_id
                                            AND previous.quest_id = cq.quest_id
                                            AND previous.status = 'completed'
                                            AND previous.id <> cq.id
                                ) AS completed_before
            FROM character_quests cq
            JOIN quests q ON q.id = cq.quest_id
            JOIN enemies e ON e.id = q.target_enemy_id
            WHERE cq.character_id = %s
            ORDER BY q.id
            """,
            (character.id,),
        ).fetchall()
        for row in rows:
            quest = Quest(
                id=row["quest_id"],
                name=row["name"],
                description=row["description"],
                target_enemy_id=row["target_enemy_id"],
                target_enemy_name=row["target_enemy_name"],
                required_kills=row["required_kills"],
                exp_reward=row["exp_reward"],
                gold_reward=row["gold_reward"],
                min_level=row["min_level"],
            )
            character.quests.append(
                QuestProgress(
                    quest=quest,
                    status=row["status"],
                    kills=row["kills"],
                    record_id=row["id"],
                    completed_before=row["completed_before"],
                )
            )
