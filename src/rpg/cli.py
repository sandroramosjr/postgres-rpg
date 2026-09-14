from __future__ import annotations

import sys
import os

import psycopg

from rpg.combat import BattleLog
from rpg.db import get_connection, initialize_schema
from rpg.game import GameService, create_game_service
from rpg.models.character import Character
from rpg.models.enemy import Enemy
from rpg.models.skill import Skill

SLOT_NAMES = {"weapon": "arma", "armor": "armadura", "accessory": "acessório"}
QUEST_STATUS_NAMES = {"active": "ativa", "completed": "concluída"}
BATTLE_OUTCOME_NAMES = {"win": "VITÓRIA", "loss": "DERROTA", "flee": "FUGA"}


def _prompt(text: str) -> str:
    return input(text).strip()


def _pause() -> None:
    print("\nPressione qualquer tecla para continuar...", end="", flush=True)
    if os.name == "nt":
        import msvcrt

        msvcrt.getwch()
    else:
        input()
    print()


def _equipment_description(item) -> str:
    effects: list[str] = []
    if item.attack_bonus:
        effects.append(f"+{item.attack_bonus} ataque")
    if item.defense_bonus:
        effects.append(f"+{item.defense_bonus} defesa")
    if item.speed_bonus:
        effects.append(f"{item.speed_bonus:+} velocidade")
    if item.hp_bonus:
        effects.append(f"+{item.hp_bonus} HP máximo")
    return ", ".join(effects) if effects else "sem bônus de atributos"


def _pick(options: list, label: str):
    if not options:
        print(f"Nenhum(a) {label} disponível.")
        return None
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option}")
    prompt = (
        "Escolha uma opção (ou 0 para cancelar): "
        if label == "opção"
        else f"Escolha o número do(a) {label} (ou 0 para cancelar): "
    )
    choice = _prompt(prompt)
    if not choice.isdigit():
        return None
    number = int(choice)
    if number == 0:
        return None
    if 1 <= number <= len(options):
        return options[number - 1]
    return None


def _sheet(character: Character) -> None:
    stats = character.effective_stats()
    print(f"\n=== {character.name}, {character.character_class.name} ===")
    print(
        f"Nível {character.level}  EXP {character.exp}/{character.exp_to_next_level()}  "
        f"Ouro {character.gold}"
    )
    print(
        f"HP {character.stats.hp}/{character.stats.max_hp}  "
        f"MP {character.stats.mp}/{character.stats.max_mp}"
    )
    print(
        f"ATK {stats.attack}  DEF {stats.defense}  SPD {stats.speed}  "
        f"(inclui equipamentos)"
    )
    if character.equipped:
        print("Equipado:")
        for slot, item in character.equipped.items():
            print(f"  {SLOT_NAMES.get(slot, slot)}: {item.name}")
    else:
        print("Equipado: nada")


def _inventory(game: GameService, character: Character) -> None:
    items = character.inventory.all_items()
    if not items:
        print("O inventário está vazio.")
        _pause()
        return
    labels = []
    for item, qty in items:
        equipped = character.equipped.get(item.slot)
        mark = " (equipado)" if equipped and equipped.id == item.id else ""
        labels.append(
            f"{item.name} x{qty}  {SLOT_NAMES.get(item.slot, item.slot)}  "
            f"+ATK {item.attack_bonus} +DEF {item.defense_bonus} "
            f"+SPD {item.speed_bonus} +HP {item.hp_bonus}{mark}"
        )
    picked = _pick(labels, "item para equipar")
    if picked is None:
        return
    item = items[labels.index(picked)][0]
    item = character.equip(item.id)
    if item is None:
        print("Não foi possível equipar esse item (inexistente ou nível insuficiente).")
        _pause()
        return
    game.save(character)
    print(f"{item.name} equipado.")
    _pause()


def _shop(game: GameService, character: Character) -> None:
    stock = game.catalog.list_equipment()
    print(f"\nLoja  (você tem {character.gold} de ouro)")
    action = _pick(["Comprar", "Vender", "Voltar"], "opção")
    if action == "Vender":
        _sell_items(game, character)
        return
    if action != "Comprar":
        return
    labels = [
        f"{item.name} ({SLOT_NAMES.get(item.slot, item.slot)})\n"
            f"      {_equipment_description(item)}\n"
            f"      Preço: {item.price} ouro | Nível mínimo: {item.min_level}"
        for item in stock
    ]
    picked = _pick(labels, "item para comprar")
    if picked is None:
        return
    print(game.buy(character, stock[labels.index(picked)].id))
    _pause()


def _sell_items(game: GameService, character: Character) -> None:
    items = [
        (item, quantity)
        for item, quantity in character.inventory.all_items()
        if character.equipped.get(item.slot, None) is None
        or character.equipped[item.slot].id != item.id
    ]
    if not items:
        print("Você não tem itens disponíveis para vender.")
        _pause()
        return
    labels = [
        f"{item.name} x{quantity} — recebe {max(1, item.price // 2)} ouro"
        for item, quantity in items
    ]
    picked = _pick(labels, "item para vender")
    if picked is None:
        return
    item = items[labels.index(picked)][0]
    print(game.sell(character, item.id))
    _pause()


def _quests(game: GameService, character: Character) -> None:
    print("\nSuas missões:")
    if not character.quests:
        print("  (nenhuma)")
    for progress in character.quests:
        repeat_note = " (já concluída anteriormente)" if progress.completed_before else ""
        print(
            f"  {progress.quest.name} [{QUEST_STATUS_NAMES.get(progress.status, progress.status)}] "
            f"{progress.kills}/{progress.quest.required_kills} "
            f"{progress.quest.target_enemy_name}{repeat_note}"
        )
    active_ids = {
        progress.quest.id
        for progress in character.quests
        if progress.status == "active"
    }
    completed_ids = {
        progress.quest.id
        for progress in character.quests
        if progress.status == "completed"
    }
    available = game.quests.list_available(character.level, active_ids)
    locked = game.quests.list_locked(character.level)
    if locked:
        print("\nMissões bloqueadas por nível:")
        for quest in locked:
            print(f"  {quest.name} — disponível no nível {quest.min_level}")
    if not available:
        print("Nenhuma missão nova.")
        _pause()
        return
    print("Disponíveis:")
    labels = [
        f"{q.name}{' (já concluída anteriormente)' if q.id in completed_ids else ''}"
        f" — {q.description} (derrote {q.required_kills} {q.target_enemy_name}; "
        f"recompensa: {q.exp_reward} EXP e {q.gold_reward} ouro)"
        for q in available
    ]
    picked = _pick(labels, "missão")
    if picked is None:
        return
    quest = available[labels.index(picked)]
    accepted = character.accept_quest(quest)
    if accepted is None:
        print("Não foi possível aceitar essa missão.")
        _pause()
        return
    game.save(character)
    print(f"Aceita: {quest.name}")
    _pause()


def _skills(character: Character) -> None:
    print("\nHabilidades:")
    if not character.skills:
        print("  (nenhuma ainda — suba de nível para aprender mais)")
        return
    for skill in character.skills:
        print(
            f"  {skill.name}  {skill.damage_percent}% dano  {skill.mp_cost} MP  "
            f"— {skill.description}"
        )


def _history(game: GameService, character: Character) -> None:
    rows = game.battles.history_for(character.id)
    print("\nHistórico de batalhas (últimas 20):")
    if not rows:
        print("  (nenhuma batalha ainda)")
        return
    for record in rows:
        print(
            f"  {record.fought_at:%Y-%m-%d %H:%M}  "
            f"{BATTLE_OUTCOME_NAMES.get(record.outcome, record.outcome):7} contra "
            f"{record.enemy_name}  {record.turns} turnos  "
            f"causado {record.damage_dealt}  recebido {record.damage_taken}  "
            f"+{record.exp_gained} EXP +{record.gold_gained} ouro"
        )


def _stats(game: GameService, character: Character) -> None:
    overview = game.stats.character_overview(character.id)
    print("\n=== Estatísticas ===")
    if overview:
        print(
            f"{overview['name']} ({overview['class_name']})  "
            f"Lv {overview['level']}  "
            f"V/D/F {overview['wins']}/{overview['losses']}/{overview['flees']}  "
            f"missões concluídas {overview['quests_completed']}"
        )
        print(
            f"Dano causado {overview['total_damage_dealt']}  "
            f"recebido {overview['total_damage_taken']}  "
            f"média de turnos {overview['avg_turns']}  "
            f"ouro em batalhas {overview['total_gold_from_battles']}"
        )
        print(
            f"Itens vendidos automaticamente {overview['items_sold']}  "
            f"ouro obtido com vendas {overview['total_gold_from_sales']}"
        )
        for row in game.stats.sales_by_item(character.id):
            print(f"  Venda de {row['name']}: {row['quantity']} unidade(s), {row['total_gold']} ouro")
    print("\nRanking:")
    for row in game.stats.leaderboard():
        print(
            f"  {row['name']}: {row['wins']}V {row['losses']}D "
            f"{row['battles_fought']} batalhas"
        )
    print("\nDesempenho contra os inimigos:")
    for row in game.stats.enemy_threats():
        print(
            f"  {row['name']}: taxa de vitória {row['player_win_rate_pct']}% "
            f"({row['times_fought']} batalhas)"
        )
    print("\nProgresso das missões:")
    for row in game.stats.quest_funnel():
        print(
            f"  {row['name']}: {row['completion_rate_pct']}% "
            f"({row['times_completed']}/{row['times_accepted']} concluídas)"
        )
    print("\nValor do inventário:")
    value_rows = game.stats.inventory_value(character.id)
    if not value_rows:
        print("  (vazio)")
    total = 0
    for row in value_rows:
        total += row["total_value"]
        print(
            f"  {SLOT_NAMES.get(row['slot'], row['slot'])} {row['name']} x{row['quantity']} = "
            f"{row['total_value']} ouro"
        )
    print(f"  Total: {total} ouro")


def _choose_skill(character: Character) -> Skill | None:
    if not character.skills:
        print("Você ainda não aprendeu nenhuma habilidade.")
        return None
    labels = [
        f"{skill.name} ({skill.mp_cost} MP, {skill.damage_percent}% dano)"
        for skill in character.skills
    ]
    picked = _pick(labels, "habilidade")
    if picked is None:
        return None
    return character.skills[labels.index(picked)]


def _show_turn(character: Character, enemy: Enemy, turn: int) -> None:
    stats = character.effective_stats()
    print(
        f"\n-- Turno {turn} --  "
        f"Você {stats.hp}/{stats.max_hp} HP  "
        f"{stats.mp}/{stats.max_mp} MP  |  "
        f"{enemy.name} {enemy.stats.hp}/{enemy.stats.max_hp} HP"
    )


def _enemy_turn(game: GameService, character: Character, enemy: Enemy, log: BattleLog) -> bool:
    taken, line = game.combat.enemy_attack(enemy, character)
    log.damage_taken += taken
    print(line)
    return character.is_alive


def _player_action(
    game: GameService, character: Character, enemy: Enemy, log: BattleLog
) -> tuple[str | None, int, bool]:
    action = _prompt("[A]tacar  [H]abilidade  [F]ugir: ").lower()
    if action == "f":
        log.lines.append("Você fugiu.")
        return "flee", 0, True
    if action == "h":
        skill = _choose_skill(character)
        if skill is None:
            return None, 0, False
        damage, line = game.combat.player_skill_attack(character, enemy, skill)
        print(line)
        return (None, damage, False) if damage == 0 else (None, damage, True)
    if action == "a":
        damage, line = game.combat.player_basic_attack(character, enemy)
        print(line)
        return None, damage, True
    print("Escolha A, H ou F.")
    return None, 0, False


def _select_enemy(game: GameService) -> Enemy | None:
    enemies = game.catalog.list_enemies()
    labels = [
        f"{enemy.name} (nível {enemy.level}, HP {enemy.stats.max_hp}, "
        f"+{enemy.exp_reward} EXP / +{enemy.gold_reward} ouro)"
        for enemy in enemies
    ]
    picked = _pick(labels, "inimigo")
    return enemies[labels.index(picked)].clone() if picked is not None else None


def _finish_fight(game: GameService, character: Character, enemy: Enemy, log: BattleLog) -> None:
    loot_roll = log.outcome == "win" and game.combat.rng.random() < 0.45
    for note in game.resolve_battle(character, enemy, log, loot_roll=loot_roll):
        print(note)
    _pause()


def _fight(game: GameService, character: Character) -> None:
    enemy = _select_enemy(game)
    if enemy is None:
        return
    log = BattleLog(outcome="flee", turns=0, damage_dealt=0, damage_taken=0, lines=[])
    print(f"\nUm {enemy.name} apareceu!")

    while character.is_alive and enemy.is_alive:
        log.turns += 1
        _show_turn(character, enemy, log.turns)
        player_first = game.combat.player_goes_first(character, enemy)
        if not player_first and not _enemy_turn(game, character, enemy, log):
            log.outcome = "loss"
            break
        outcome, damage, valid = _player_action(game, character, enemy, log)
        if not valid:
            log.turns -= 1
            continue
        if outcome == "flee":
            log.outcome = outcome
            break
        log.damage_dealt += damage
        if not enemy.is_alive:
            log.outcome = "win"
            break
        if player_first and not _enemy_turn(game, character, enemy, log):
            log.outcome = "loss"
            break

    _finish_fight(game, character, enemy, log)


def _town_loop(game: GameService, character: Character) -> None:
    while True:
        _sheet(character)
        options = [
            "Lutar",
            "Inventário",
            "Loja",
            "Missões",
            "Habilidades",
            "Histórico",
            "Estatísticas",
            "Descansar na estalagem (50 ouro)",
            "Salvar e sair",
        ]
        choice = _pick(options, "opção")
        if choice == options[0]:
            _fight(game, character)
        elif choice == options[1]:
            _inventory(game, character)
        elif choice == options[2]:
            _shop(game, character)
        elif choice == options[3]:
            _quests(game, character)
        elif choice == options[4]:
            _skills(character)
            _pause()
        elif choice == options[5]:
            _history(game, character)
            _pause()
        elif choice == options[6]:
            _stats(game, character)
            _pause()
        elif choice == options[7]:
            print(game.rest(character))
            _pause()
        elif choice == options[8]:
            game.save(character)
            print("Salvo. Até logo.")
            return


def _create_character(game: GameService) -> Character | None:
    name = _prompt("Nome do personagem: ")
    if not name:
        return None
    classes = game.catalog.list_classes()
    labels = [
        f"{cls.name} — {cls.description} "
        f"(HP {cls.base_hp}, ATK {cls.base_attack}, DEF {cls.base_defense}, SPD {cls.base_speed})"
        for cls in classes
    ]
    picked = _pick(labels, "classe")
    if picked is None:
        return None
    chosen = classes[labels.index(picked)]
    try:
        return game.characters.create(name, chosen)
    except psycopg.errors.UniqueViolation:
        game.conn.rollback()
        print("Esse nome já está sendo usado.")
        return None


def _load_character(game: GameService) -> Character | None:
    names = game.characters.list_names()
    if not names:
        print("Nenhum personagem salvo.")
        return None
    picked = _pick(names, "personagem")
    if picked is None:
        return None
    return game.characters.load_by_name(picked)


def _delete_character(game: GameService) -> None:
    names = game.characters.list_names()
    if not names:
        print("Nenhum personagem salvo.")
        return
    picked = _pick(names, "personagem para excluir")
    if picked is None:
        return
    confirmation = _prompt(f'Digite "DELETAR" para apagar {picked}: ')
    if confirmation != "DELETAR":
        print("Exclusão cancelada.")
        return
    if game.characters.delete_by_name(picked):
        game.conn.commit()
        print(f"Personagem {picked} deletado.")
    else:
        print("Personagem não encontrado.")


def main() -> int:
    print("postgres-rpg — um RPG de texto por turnos")
    try:
        with get_connection() as conn:
            initialize_schema(conn)
            game = create_game_service(conn)
            while True:
                options = [
                    "Criar personagem",
                    "Carregar personagem",
                    "Excluir personagem",
                    "Sair",
                ]
                choice = _pick(options, "opção")
                if choice == options[0]:
                    character = _create_character(game)
                    if character:
                        conn.commit()
                        _town_loop(game, character)
                elif choice == options[1]:
                    character = _load_character(game)
                    if character:
                        _town_loop(game, character)
                elif choice == options[2]:
                    _delete_character(game)
                    _pause()
                elif choice == options[3]:
                    return 0
    except psycopg.OperationalError as exc:
        print("Não foi possível conectar ao banco de dados.")
        print("Inicie o banco com: docker compose up -d")
        print("Depois copie .env.example para .env, se necessário.")
        print(f"Detalhes: {exc}")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nAté logo.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
