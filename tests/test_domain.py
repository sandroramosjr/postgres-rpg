from rpg.combat import CombatEngine
from rpg.models.character import Character, CharacterClass
from rpg.models.enemy import Enemy
from rpg.models.equipment import Equipment, Inventory
from rpg.models.quest import Quest
from rpg.models.skill import Skill
from rpg.models.stats import Stats


def _warrior() -> CharacterClass:
    return CharacterClass(1, "Warrior", "tank", 40, 8, 10, 8, 6)


def _hero() -> Character:
    stats = Stats(hp=40, max_hp=40, mp=8, max_mp=8, attack=10, defense=8, speed=6)
    return Character(name="Hero", character_class=_warrior(), stats=stats, gold=50)


def _slime() -> Enemy:
    stats = Stats(hp=18, max_hp=18, mp=0, max_mp=0, attack=5, defense=2, speed=4)
    return Enemy(
        enemy_id=1,
        name="Slime",
        level=1,
        stats=stats,
        exp_reward=12,
        gold_reward=8,
    )


def test_effective_stats_include_equipment():
    hero = _hero()
    sword = Equipment(1, "Rusty Sword", "weapon", 3, 0, 0, 0, 15, 1)
    hero.inventory.add(sword)
    hero.equip(1)
    assert hero.effective_stats().attack == 13
    assert hero.stats.attack == 10


def test_inventory_remove_one_item():
    inventory = Inventory()
    sword = Equipment(1, "Rusty Sword", "weapon", 3, 0, 0, 0, 15, 1)
    inventory.add(sword, 2)

    assert inventory.remove(1) == sword
    assert inventory.quantity(1) == 1


def test_gain_exp_levels_up_and_grants_gold():
    hero = _hero()
    starting_gold = hero.gold
    levels = hero.gain_exp(100)
    assert levels == [2]
    assert hero.level == 2
    assert hero.gold == starting_gold + 25
    assert hero.stats.max_hp > 40


def test_quest_completes_after_required_kills():
    hero = _hero()
    quest = Quest(1, "Slime Problem", "kill slimes", 1, "Slime", 2, 40, 30, 1)
    starting_gold = hero.gold
    hero.accept_quest(quest)
    first = hero.record_enemy_kill(1)
    assert first == []
    done = hero.record_enemy_kill(1)
    assert len(done) == 1
    assert done[0].is_complete
    assert hero.exp == 40
    assert hero.gold == starting_gold + 30


def test_completed_quest_can_be_accepted_again():
    hero = _hero()
    quest = Quest(1, "Slime Problem", "kill slimes", 1, "Slime", 1, 40, 30, 1)

    first = hero.accept_quest(quest)
    assert first is not None
    hero.record_enemy_kill(1)

    repeated = hero.accept_quest(quest)
    assert repeated is not None
    assert repeated.completed_before


def test_combat_damage_is_at_least_one():
    engine = CombatEngine()
    hero = _hero()
    slime = _slime()
    dmg, _ = engine.player_basic_attack(hero, slime)
    assert dmg >= 1
    assert slime.stats.hp == slime.stats.max_hp - dmg


def test_skill_spends_mp():
    engine = CombatEngine()
    hero = _hero()
    skill = Skill(1, "Power Strike", "heavy", 160, 4, 1, 1)
    hero.learn_skill(skill)
    slime = _slime()
    _, line = engine.player_skill_attack(hero, slime, skill)
    assert hero.stats.mp == 4
    assert "Power Strike" in line


def test_mage_fire_skill_has_strong_damage():
    mage = CharacterClass(2, "Mage", "caster", 24, 22, 7, 4, 7)
    hero = Character(
        name="Mage",
        character_class=mage,
        stats=Stats(hp=24, max_hp=24, mp=22, max_mp=22, attack=7, defense=4, speed=7),
    )
    skill = Skill(2, "Fire Bolt", "fire", 240, 4, 1, 2)
    hero.learn_skill(skill)
    slime = _slime()

    damage, _ = CombatEngine().player_skill_attack(hero, slime, skill)

    assert damage >= 9
    assert hero.stats.mp == 18


def test_speed_controls_initiative():
    engine = CombatEngine()
    hero = _hero()
    slime = _slime()
    assert engine.player_goes_first(hero, slime)

    fast_enemy = _slime()
    fast_enemy.stats.speed = hero.stats.speed + 1
    assert not engine.player_goes_first(hero, fast_enemy)


def test_equipment_hp_bonus_is_used_for_damage_and_death():
    hero = _hero()
    vest = Equipment(2, "Leather Vest", "armor", 0, 3, 0, 4, 20, 1)
    hero.inventory.add(vest)
    hero.equip(2)

    hero.take_damage(hero.stats.max_hp)

    assert hero.is_alive
    assert hero.effective_stats().hp == 4
    hero.take_damage(4)
    assert not hero.is_alive
