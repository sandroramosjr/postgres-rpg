INSERT INTO character_classes (name, description, base_hp, base_mp, base_attack, base_defense, base_speed)
VALUES
    ('Guerreiro', 'Combatente da linha de frente com muito HP e ataque.', 40, 8, 10, 8, 6),
    ('Mago', 'Canhão de vidro que depende de habilidades e MP.', 24, 22, 7, 4, 7),
    ('Ladino', 'Atacante veloz que troca resistência por velocidade.', 28, 12, 9, 5, 11);

INSERT INTO equipment (name, slot, attack_bonus, defense_bonus, speed_bonus, hp_bonus, price, min_level)
VALUES
    ('Espada Enferrujada', 'weapon', 3, 0, 0, 0, 15, 1),
    ('Lâmina de Ferro', 'weapon', 7, 0, 0, 0, 60, 3),
    ('Cajado das Faíscas', 'weapon', 5, 0, 1, 0, 55, 2),
    ('Colete de Couro', 'armor', 0, 3, 0, 4, 20, 1),
    ('Cota de Malha', 'armor', 0, 7, -1, 8, 80, 4),
    ('Capa Veloz', 'accessory', 0, 1, 4, 0, 45, 2),
    ('Amuleto da Sorte', 'accessory', 2, 1, 1, 2, 70, 3);

INSERT INTO skills (name, description, damage_percent, mp_cost, required_level, class_id)
VALUES
    ('Golpe Poderoso', 'Um golpe corpo a corpo devastador.', 160, 4, 1, 1),
    ('Turbilhão', 'Gire e ataque com força extra.', 210, 8, 4, 1),
    ('Raio de Fogo', 'Uma explosão concentrada de chamas.', 240, 4, 1, 2),
    ('Explosão Arcana', 'Libere sua mana acumulada como dano.', 320, 10, 4, 2),
    ('Golpe pelas Costas', 'Ataque quando o inimigo estiver vulnerável.', 170, 4, 1, 3),
    ('Rajada', 'Uma sequência rápida de cortes.', 220, 9, 4, 3);

INSERT INTO enemies (name, level, hp, attack, defense, speed, exp_reward, gold_reward, loot_equipment_id)
VALUES
    ('Slime', 1, 18, 5, 2, 4, 12, 8, 1),
    ('Lobo da Floresta', 2, 26, 8, 3, 9, 20, 14, 4),
    ('Bandido', 3, 34, 11, 5, 8, 32, 22, 2),
    ('Morcego da Caverna', 4, 28, 10, 4, 12, 28, 18, 6),
    ('Ogro', 6, 70, 16, 10, 5, 70, 45, 5);

INSERT INTO quests (name, description, target_enemy_id, required_kills, exp_reward, gold_reward, min_level)
VALUES
    ('Problema dos Slimes', 'Derrote três Slimes perto do poço da vila.', 1, 3, 40, 30, 1),
    ('Peles de Lobo', 'Reduza a matilha de Lobos da Floresta.', 2, 2, 60, 45, 1),
    ('Segurança na Estrada', 'Derrote os Bandidos que ameaçam a estrada comercial.', 3, 2, 90, 80, 3),
    ('Contrato do Ogro', 'Derrube o Ogro que vive nas colinas.', 5, 1, 150, 120, 5);
