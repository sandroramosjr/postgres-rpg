from __future__ import annotations

from rpg.combat import BattleLog, CombatEngine
from rpg.models.character import Character
from rpg.models.enemy import Enemy
from rpg.repositories.battle_repository import BattleRepository
from rpg.repositories.catalog_repository import CatalogRepository
from rpg.repositories.character_repository import CharacterRepository
from rpg.repositories.quest_repository import QuestRepository
from rpg.repositories.stats_repository import StatsRepository
from rpg.repositories.sale_repository import SaleRepository


class GameService:
    def __init__(
        self,
        conn,
        characters: CharacterRepository,
        catalog: CatalogRepository,
        quests: QuestRepository,
        battles: BattleRepository,
        stats: StatsRepository,
        sales: SaleRepository,
        combat: CombatEngine,
    ) -> None:
        self.conn = conn
        self.characters = characters
        self.catalog = catalog
        self.quests = quests
        self.battles = battles
        self.stats = stats
        self.sales = sales
        self.combat = combat

    def save(self, character: Character) -> None:
        self.characters.save(character)
        self.conn.commit()

    def buy(self, character: Character, equipment_id: int) -> str:
        catalog = {item.id: item for item in self.catalog.list_equipment()}
        item = catalog.get(equipment_id)
        if item is None:
            return "Esse item não é vendido aqui."
        if character.level < item.min_level:
            return f"Você precisa estar no nível {item.min_level} para comprar {item.name}."
        if not character.spend_gold(item.price):
            return "Ouro insuficiente."
        character.inventory.add(item)
        self.save(character)
        return f"Você comprou {item.name} por {item.price} de ouro."

    def rest(self, character: Character, cost: int = 50) -> str:
        if not character.spend_gold(cost):
            return f"O estalajadeiro pede {cost} de ouro."
        character.heal_full()
        self.save(character)
        return "Você descansou na estalagem. HP e MP restaurados."

    def sell(self, character: Character, equipment_id: int) -> str:
        item = character.inventory.get(equipment_id)
        if item is None:
            return "Esse item não está no seu inventário."
        equipped = character.equipped.get(item.slot)
        if equipped and equipped.id == item.id:
            return "Você não pode vender um item equipado."
        value = max(1, item.price // 2)
        character.inventory.remove(item.id)
        character.add_gold(value)
        self.sales.record(
            character_id=character.id,
            equipment_id=item.id,
            quantity=1,
            unit_price=value,
        )
        self.save(character)
        return f"Você vendeu {item.name} por {value} de ouro."

    def resolve_battle(
        self,
        character: Character,
        enemy: Enemy,
        log: BattleLog,
        *,
        loot_roll: bool,
    ) -> list[str]:
        notes, exp_gained, gold_gained = self._resolve_outcome(
            character, enemy, log.outcome, loot_roll
        )
        self._record_battle(character, enemy, log, exp_gained, gold_gained)
        self.save(character)
        return notes

    def _resolve_outcome(
        self, character: Character, enemy: Enemy, outcome: str, loot_roll: bool
    ) -> tuple[list[str], int, int]:
        if outcome == "win":
            return self._resolve_victory(character, enemy, loot_roll)
        if outcome == "loss":
            character.stats.hp = max(1, character.stats.max_hp // 4)
            return ["Você foi derrotado e voltou cambaleando para a cidade."], 0, 0
        return ["Você fugiu da batalha."], 0, 0

    def _resolve_victory(
        self, character: Character, enemy: Enemy, loot_roll: bool
    ) -> tuple[list[str], int, int]:
        exp_gained = enemy.exp_reward
        gold_gained = enemy.gold_reward
        levels = character.gain_exp(exp_gained)
        character.add_gold(gold_gained)
        notes = [f"Vitória! +{exp_gained} EXP, +{gold_gained} de ouro."]
        notes.extend(
            f"Você subiu para o nível {level}! +25 de ouro, atributos aumentados."
            for level in levels
        )
        notes.extend(self._resolve_loot(character, enemy, loot_roll))
        notes.extend(self._complete_quests(character, enemy))
        self.characters._sync_class_skills(character)
        return notes, exp_gained, gold_gained

    def _resolve_loot(self, character: Character, enemy: Enemy, loot_roll: bool) -> list[str]:
        if not loot_roll or enemy.loot is None:
            return []
        loot = enemy.loot
        if character.inventory.quantity(loot.id) == 0:
            character.inventory.add(loot)
            return [f"{enemy.name} deixou cair {loot.name}!"]
        sale_value = max(1, loot.price // 2)
        character.add_gold(sale_value)
        self.sales.record(
            character_id=character.id,
            equipment_id=loot.id,
            quantity=1,
            unit_price=sale_value,
        )
        return [
            f"{enemy.name} deixou cair {loot.name}, mas você já tinha uma cópia. "
            f"Item vendido automaticamente por {sale_value} de ouro."
        ]

    def _complete_quests(self, character: Character, enemy: Enemy) -> list[str]:
        completed = character.record_enemy_kill(enemy.id)
        return [
            f"Missão concluída: {progress.quest.name} "
            f"(+{progress.quest.exp_reward} EXP, +{progress.quest.gold_reward} de ouro)."
            for progress in completed
        ]

    def _record_battle(
        self,
        character: Character,
        enemy: Enemy,
        log: BattleLog,
        exp_gained: int,
        gold_gained: int,
    ) -> None:
        self.battles.record(
            character_id=character.id,
            enemy_id=enemy.id,
            outcome=log.outcome,
            turns=log.turns,
            damage_dealt=log.damage_dealt,
            damage_taken=log.damage_taken,
            exp_gained=exp_gained,
            gold_gained=gold_gained,
        )


def create_game_service(conn) -> GameService:
    return GameService(
        conn,
        characters=CharacterRepository(conn),
        catalog=CatalogRepository(conn),
        quests=QuestRepository(conn),
        battles=BattleRepository(conn),
        stats=StatsRepository(conn),
        sales=SaleRepository(conn),
        combat=CombatEngine(),
    )
