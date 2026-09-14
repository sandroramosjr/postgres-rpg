from __future__ import annotations

import psycopg


class SaleRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def record(
        self,
        *,
        character_id: int,
        equipment_id: int,
        quantity: int,
        unit_price: int,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO item_sales (character_id, equipment_id, quantity, unit_price)
            VALUES (%s, %s, %s, %s)
            """,
            (character_id, equipment_id, quantity, unit_price),
        )