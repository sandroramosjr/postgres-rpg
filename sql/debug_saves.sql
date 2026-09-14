BEGIN;

DELETE FROM characters
WHERE name IN ('WAR', 'ROG', 'MAG');

INSERT INTO characters (
    name, class_id, level, exp, gold,
    hp, max_hp, mp, max_mp, attack, defense, speed
)
SELECT
    debug.name,
    cc.id,
    10,
    0,
    9999,
    cc.base_hp + 54,
    cc.base_hp + 54,
    cc.base_mp + 27,
    cc.base_mp + 27,
    cc.base_attack + 18,
    cc.base_defense + 18,
    cc.base_speed + 9
FROM (
    VALUES
        ('WAR', 'Guerreiro'),
        ('ROG', 'Ladino'),
        ('MAG', 'Mago')
) AS debug(name, class_name)
JOIN character_classes cc ON cc.name = debug.class_name;

INSERT INTO inventory (character_id, equipment_id, quantity)
SELECT c.id, e.id, 1
FROM characters c
CROSS JOIN equipment e
WHERE c.name IN ('WAR', 'ROG', 'MAG');

INSERT INTO equipped_items (character_id, slot, equipment_id)
SELECT c.id, selected.slot, selected.id
FROM characters c
CROSS JOIN LATERAL (
    SELECT DISTINCT ON (e.slot) e.id, e.slot
    FROM equipment e
    ORDER BY e.slot, e.price DESC, e.id
) AS selected
WHERE c.name IN ('WAR', 'ROG', 'MAG');

INSERT INTO character_skills (character_id, skill_id)
SELECT c.id, s.id
FROM characters c
JOIN character_classes cc ON cc.id = c.class_id
JOIN skills s ON s.class_id = cc.id
WHERE c.name IN ('WAR', 'ROG', 'MAG')
  AND s.required_level <= c.level;

COMMIT;