-- postgres-rpg schema: normalized catalog + per-character state + battle history.

CREATE TABLE character_classes (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    base_hp     INTEGER NOT NULL CHECK (base_hp > 0),
    base_mp     INTEGER NOT NULL CHECK (base_mp >= 0),
    base_attack INTEGER NOT NULL CHECK (base_attack >= 0),
    base_defense INTEGER NOT NULL CHECK (base_defense >= 0),
    base_speed  INTEGER NOT NULL CHECK (base_speed >= 0)
);

CREATE TABLE characters (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    class_id    INTEGER NOT NULL REFERENCES character_classes (id),
    level       INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    exp         INTEGER NOT NULL DEFAULT 0 CHECK (exp >= 0),
    gold        INTEGER NOT NULL DEFAULT 0 CHECK (gold >= 0),
    hp          INTEGER NOT NULL,
    max_hp      INTEGER NOT NULL,
    mp          INTEGER NOT NULL,
    max_mp      INTEGER NOT NULL,
    attack      INTEGER NOT NULL,
    defense     INTEGER NOT NULL,
    speed       INTEGER NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE equipment (
    id            SERIAL PRIMARY KEY,
    name          TEXT UNIQUE NOT NULL,
    slot          TEXT NOT NULL CHECK (slot IN ('weapon', 'armor', 'accessory')),
    attack_bonus  INTEGER NOT NULL DEFAULT 0,
    defense_bonus INTEGER NOT NULL DEFAULT 0,
    speed_bonus   INTEGER NOT NULL DEFAULT 0,
    hp_bonus      INTEGER NOT NULL DEFAULT 0,
    price         INTEGER NOT NULL DEFAULT 0 CHECK (price >= 0),
    min_level     INTEGER NOT NULL DEFAULT 1 CHECK (min_level >= 1)
);

CREATE TABLE inventory (
    character_id INTEGER NOT NULL REFERENCES characters (id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipment (id),
    quantity     INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    PRIMARY KEY (character_id, equipment_id)
);

CREATE TABLE equipped_items (
    character_id INTEGER NOT NULL REFERENCES characters (id) ON DELETE CASCADE,
    slot         TEXT NOT NULL CHECK (slot IN ('weapon', 'armor', 'accessory')),
    equipment_id INTEGER NOT NULL REFERENCES equipment (id),
    PRIMARY KEY (character_id, slot)
);

CREATE TABLE item_sales (
    id           SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters (id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipment (id),
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    unit_price   INTEGER NOT NULL CHECK (unit_price >= 0),
    sold_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE skills (
    id              SERIAL PRIMARY KEY,
    name            TEXT UNIQUE NOT NULL,
    description     TEXT NOT NULL,
    damage_percent  INTEGER NOT NULL CHECK (damage_percent > 0),
    mp_cost         INTEGER NOT NULL CHECK (mp_cost >= 0),
    required_level  INTEGER NOT NULL DEFAULT 1 CHECK (required_level >= 1),
    class_id        INTEGER REFERENCES character_classes (id)
);

CREATE TABLE character_skills (
    character_id INTEGER NOT NULL REFERENCES characters (id) ON DELETE CASCADE,
    skill_id     INTEGER NOT NULL REFERENCES skills (id),
    PRIMARY KEY (character_id, skill_id)
);

CREATE TABLE enemies (
    id                SERIAL PRIMARY KEY,
    name              TEXT UNIQUE NOT NULL,
    level             INTEGER NOT NULL CHECK (level >= 1),
    hp                INTEGER NOT NULL CHECK (hp > 0),
    attack            INTEGER NOT NULL CHECK (attack >= 0),
    defense           INTEGER NOT NULL CHECK (defense >= 0),
    speed             INTEGER NOT NULL CHECK (speed >= 0),
    exp_reward        INTEGER NOT NULL CHECK (exp_reward >= 0),
    gold_reward       INTEGER NOT NULL CHECK (gold_reward >= 0),
    loot_equipment_id INTEGER REFERENCES equipment (id)
);

CREATE TABLE quests (
    id             SERIAL PRIMARY KEY,
    name           TEXT UNIQUE NOT NULL,
    description    TEXT NOT NULL,
    target_enemy_id INTEGER NOT NULL REFERENCES enemies (id),
    required_kills INTEGER NOT NULL CHECK (required_kills > 0),
    exp_reward     INTEGER NOT NULL CHECK (exp_reward >= 0),
    gold_reward    INTEGER NOT NULL CHECK (gold_reward >= 0),
    min_level      INTEGER NOT NULL DEFAULT 1 CHECK (min_level >= 1)
);

CREATE TABLE character_quests (
    id           SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters (id) ON DELETE CASCADE,
    quest_id     INTEGER NOT NULL REFERENCES quests (id),
    status       TEXT NOT NULL CHECK (status IN ('active', 'completed')),
    kills        INTEGER NOT NULL DEFAULT 0 CHECK (kills >= 0),
    started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE battles (
    id            SERIAL PRIMARY KEY,
    character_id  INTEGER NOT NULL REFERENCES characters (id) ON DELETE CASCADE,
    enemy_id      INTEGER NOT NULL REFERENCES enemies (id),
    outcome       TEXT NOT NULL CHECK (outcome IN ('win', 'loss', 'flee')),
    turns         INTEGER NOT NULL CHECK (turns >= 1),
    damage_dealt  INTEGER NOT NULL DEFAULT 0 CHECK (damage_dealt >= 0),
    damage_taken  INTEGER NOT NULL DEFAULT 0 CHECK (damage_taken >= 0),
    exp_gained    INTEGER NOT NULL DEFAULT 0 CHECK (exp_gained >= 0),
    gold_gained   INTEGER NOT NULL DEFAULT 0 CHECK (gold_gained >= 0),
    fought_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_battles_character_fought_at ON battles (character_id, fought_at DESC);
CREATE INDEX idx_battles_outcome ON battles (outcome);
CREATE INDEX idx_character_quests_status ON character_quests (status);
CREATE INDEX idx_item_sales_character_sold_at ON item_sales (character_id, sold_at DESC);

CREATE OR REPLACE VIEW character_battle_stats AS
SELECT
    c.id AS character_id,
    c.name,
    COUNT(b.id) AS battles_fought,
    COUNT(*) FILTER (WHERE b.outcome = 'win') AS wins,
    COUNT(*) FILTER (WHERE b.outcome = 'loss') AS losses,
    COUNT(*) FILTER (WHERE b.outcome = 'flee') AS flees,
    COALESCE(SUM(b.damage_dealt), 0) AS total_damage_dealt,
    COALESCE(SUM(b.damage_taken), 0) AS total_damage_taken,
    COALESCE(ROUND(AVG(b.turns)::numeric, 1), 0) AS avg_turns,
    COALESCE(SUM(b.exp_gained), 0) AS total_exp_from_battles,
    COALESCE(SUM(b.gold_gained), 0) AS total_gold_from_battles
FROM characters c
LEFT JOIN battles b ON b.character_id = c.id
GROUP BY c.id, c.name;

CREATE OR REPLACE VIEW enemy_threat_stats AS
SELECT
    e.id AS enemy_id,
    e.name,
    COUNT(b.id) AS times_fought,
    COUNT(*) FILTER (WHERE b.outcome = 'win') AS player_wins,
    COUNT(*) FILTER (WHERE b.outcome = 'loss') AS player_losses,
    CASE
        WHEN COUNT(*) FILTER (WHERE b.outcome IN ('win', 'loss')) = 0 THEN 0
        ELSE ROUND(
            100.0 * COUNT(*) FILTER (WHERE b.outcome = 'win')
            / COUNT(*) FILTER (WHERE b.outcome IN ('win', 'loss')),
            1
        )
    END AS player_win_rate_pct
FROM enemies e
LEFT JOIN battles b ON b.enemy_id = e.id
GROUP BY e.id, e.name;

CREATE OR REPLACE VIEW quest_completion_stats AS
SELECT
    q.id AS quest_id,
    q.name,
    COUNT(cq.character_id) AS times_accepted,
    COUNT(*) FILTER (WHERE cq.status = 'completed') AS times_completed,
    CASE
        WHEN COUNT(cq.character_id) = 0 THEN 0
        ELSE ROUND(
            100.0 * COUNT(*) FILTER (WHERE cq.status = 'completed') / COUNT(cq.character_id),
            1
        )
    END AS completion_rate_pct
FROM quests q
LEFT JOIN character_quests cq ON cq.quest_id = q.id
GROUP BY q.id, q.name;
