from __future__ import annotations

from typing import Any

import psycopg


class StatsRepository:
    """Read-only SQL used by the in-game statistics screen."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def character_overview(self, character_id: int) -> dict[str, Any] | None:
        return self.conn.execute(
            """
            SELECT
                c.name,
                cc.name AS class_name,
                c.level,
                c.exp,
                c.gold,
                COALESCE(s.battles_fought, 0) AS battles_fought,
                COALESCE(s.wins, 0) AS wins,
                COALESCE(s.losses, 0) AS losses,
                COALESCE(s.flees, 0) AS flees,
                COALESCE(s.total_damage_dealt, 0) AS total_damage_dealt,
                COALESCE(s.total_damage_taken, 0) AS total_damage_taken,
                COALESCE(s.avg_turns, 0) AS avg_turns,
                COALESCE(s.total_gold_from_battles, 0) AS total_gold_from_battles,
                COALESCE((
                    SELECT SUM(sale.quantity)
                    FROM item_sales sale
                    WHERE sale.character_id = c.id
                ), 0) AS items_sold,
                COALESCE((
                    SELECT SUM(sale.quantity * sale.unit_price)
                    FROM item_sales sale
                    WHERE sale.character_id = c.id
                ), 0) AS total_gold_from_sales,
                (
                    SELECT COUNT(*) FROM character_quests cq
                    WHERE cq.character_id = c.id AND cq.status = 'completed'
                ) AS quests_completed
            FROM characters c
            JOIN character_classes cc ON cc.id = c.class_id
            LEFT JOIN character_battle_stats s ON s.character_id = c.id
            WHERE c.id = %s
            """,
            (character_id,),
        ).fetchone()

    def sales_by_item(self, character_id: int) -> list[dict[str, Any]]:
        return self.conn.execute(
            """
            SELECT e.name, SUM(s.quantity) AS quantity,
                   SUM(s.quantity * s.unit_price) AS total_gold
            FROM item_sales s
            JOIN equipment e ON e.id = s.equipment_id
            WHERE s.character_id = %s
            GROUP BY e.id, e.name
            ORDER BY total_gold DESC, e.name
            """,
            (character_id,),
        ).fetchall()

    def leaderboard(self) -> list[dict[str, Any]]:
        return self.conn.execute(
            """
            SELECT name, battles_fought, wins, losses, flees,
                   total_damage_dealt, avg_turns
            FROM character_battle_stats
            ORDER BY wins DESC, battles_fought DESC, name
            """
        ).fetchall()

    def enemy_threats(self) -> list[dict[str, Any]]:
        return self.conn.execute(
            """
            SELECT name, times_fought, player_wins, player_losses, player_win_rate_pct
            FROM enemy_threat_stats
            ORDER BY player_win_rate_pct DESC, times_fought DESC, name
            """
        ).fetchall()

    def quest_funnel(self) -> list[dict[str, Any]]:
        return self.conn.execute(
            """
            SELECT name, times_accepted, times_completed, completion_rate_pct
            FROM quest_completion_stats
            ORDER BY completion_rate_pct DESC, name
            """
        ).fetchall()

    def inventory_value(self, character_id: int) -> list[dict[str, Any]]:
        return self.conn.execute(
            """
            SELECT e.slot, e.name, i.quantity, e.price,
                   i.quantity * e.price AS total_value
            FROM inventory i
            JOIN equipment e ON e.id = i.equipment_id
            WHERE i.character_id = %s
            ORDER BY e.slot, e.name
            """,
            (character_id,),
        ).fetchall()
