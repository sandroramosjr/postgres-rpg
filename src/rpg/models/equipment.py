from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Equipment:
    id: int
    name: str
    slot: str
    attack_bonus: int
    defense_bonus: int
    speed_bonus: int
    hp_bonus: int
    price: int
    min_level: int


class Inventory:
    def __init__(self) -> None:
        self._items: dict[int, tuple[Equipment, int]] = {}

    def add(self, item: Equipment, quantity: int = 1) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        existing = self._items.get(item.id)
        if existing:
            _, count = existing
            self._items[item.id] = (item, count + quantity)
        else:
            self._items[item.id] = (item, quantity)

    def quantity(self, equipment_id: int) -> int:
        entry = self._items.get(equipment_id)
        return entry[1] if entry else 0

    def get(self, equipment_id: int) -> Equipment | None:
        entry = self._items.get(equipment_id)
        return entry[0] if entry else None

    def remove(self, equipment_id: int, quantity: int = 1) -> Equipment | None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        entry = self._items.get(equipment_id)
        if entry is None or entry[1] < quantity:
            return None
        item, current_quantity = entry
        remaining = current_quantity - quantity
        if remaining:
            self._items[equipment_id] = (item, remaining)
        else:
            del self._items[equipment_id]
        return item

    def all_items(self) -> list[tuple[Equipment, int]]:
        return list(self._items.values())

    def total_value(self) -> int:
        return sum(item.price * qty for item, qty in self._items.values())
