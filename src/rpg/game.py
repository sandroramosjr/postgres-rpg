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
    def __init__(self, conn) -> None:
        self.conn = conn
        self.characters = CharacterRepository(conn)
        self.catalog = CatalogRepository(conn)
        self.quests = QuestRepository(conn)
        self.battles = BattleRepository(conn)
        self.stats = StatsRepository(conn)
        self.sales = SaleRepository(conn)
        self.combat = CombatEngine()

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
        notes: list[str] = []
        exp_gained = 0
        gold_gained = 0
        if log.outcome == "win":
            exp_gained = enemy.exp_reward
            gold_gained = enemy.gold_reward
            levels = character.gain_exp(exp_gained)
            character.add_gold(gold_gained)
            notes.append(f"Vitória! +{exp_gained} EXP, +{gold_gained} de ouro.")
            for level in levels:
                notes.append(f"Você subiu para o nível {level}! +25 de ouro, atributos aumentados.")
            if loot_roll and enemy.loot is not None:
                loot = enemy.loot
                if character.inventory.quantity(loot.id) > 0:
                    sale_value = max(1, loot.price // 2)
                    character.add_gold(sale_value)
                    self.sales.record(
                        character_id=character.id,
                        equipment_id=loot.id,
                        quantity=1,
                        unit_price=sale_value,
                    )
                    notes.append(
                        f"{enemy.name} deixou cair {loot.name}, mas você já tinha uma cópia. "
                        f"Item vendido automaticamente por {sale_value} de ouro."
                    )
                else:
                    character.inventory.add(loot)
                    notes.append(f"{enemy.name} deixou cair {loot.name}!")
            completed = character.record_enemy_kill(enemy.id)
            for progress in completed:
                notes.append(
                    f"Missão concluída: {progress.quest.name} "
                    f"(+{progress.quest.exp_reward} EXP, +{progress.quest.gold_reward} de ouro)."
                )
            self.characters._sync_class_skills(character)
        elif log.outcome == "loss":
            character.stats.hp = max(1, character.stats.max_hp // 4)
            notes.append("Você foi derrotado e voltou cambaleando para a cidade.")
        else:
            notes.append("Você fugiu da batalha.")

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
        self.save(character)
        return notes
