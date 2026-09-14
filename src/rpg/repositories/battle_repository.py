from __future__ import annotations

import psycopg

from rpg.models.battle import BattleRecord


class BattleRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def record(
        self,
        *,
        character_id: int,
        enemy_id: int,
        outcome: str,
        turns: int,
        damage_dealt: int,
        damage_taken: int,
        exp_gained: int,
        gold_gained: int,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO battles (
                character_id, enemy_id, outcome, turns,
                damage_dealt, damage_taken, exp_gained, gold_gained
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                character_id,
                enemy_id,
                outcome,
                turns,
                damage_dealt,
                damage_taken,
                exp_gained,
                gold_gained,
            ),
        )

    def history_for(self, character_id: int, limit: int = 20) -> list[BattleRecord]:
        rows = self.conn.execute(
            """
            SELECT b.id, e.name AS enemy_name, b.outcome, b.turns,
                   b.damage_dealt, b.damage_taken, b.exp_gained, b.gold_gained, b.fought_at
            FROM battles b
            JOIN enemies e ON e.id = b.enemy_id
            WHERE b.character_id = %s
            ORDER BY b.fought_at DESC
            LIMIT %s
            """,
            (character_id, limit),
        ).fetchall()
        return [BattleRecord(**row) for row in rows]
