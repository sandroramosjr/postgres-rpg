from __future__ import annotations

import psycopg

from rpg.models.quest import Quest


class QuestRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def list_available(self, character_level: int, active_quest_ids: set[int]) -> list[Quest]:
        rows = self.conn.execute(
            """
            SELECT q.id, q.name, q.description, q.target_enemy_id, e.name AS target_enemy_name,
                   q.required_kills, q.exp_reward, q.gold_reward, q.min_level
            FROM quests q
            JOIN enemies e ON e.id = q.target_enemy_id
            WHERE q.min_level <= %s
            ORDER BY q.min_level, q.id
            """,
            (character_level,),
        ).fetchall()
        quests = [Quest(**row) for row in rows]
        return [quest for quest in quests if quest.id not in active_quest_ids]

    def list_locked(self, character_level: int) -> list[Quest]:
        rows = self.conn.execute(
            """
            SELECT q.id, q.name, q.description, q.target_enemy_id,
                   e.name AS target_enemy_name, q.required_kills,
                   q.exp_reward, q.gold_reward, q.min_level
            FROM quests q
            JOIN enemies e ON e.id = q.target_enemy_id
            WHERE q.min_level > %s
            ORDER BY q.min_level, q.id
            """,
            (character_level,),
        ).fetchall()
        return [Quest(**row) for row in rows]
