-- Showcase queries. The CLI runs equivalents of these at runtime.

-- Per-character battle record
SELECT name, battles_fought, wins, losses, flees,
       total_damage_dealt, avg_turns
FROM character_battle_stats
ORDER BY wins DESC, battles_fought DESC;

-- Enemies ranked by how often players lose
SELECT name, times_fought, player_wins, player_losses, player_win_rate_pct
FROM enemy_threat_stats
ORDER BY player_win_rate_pct DESC, times_fought DESC;

-- Quest funnel
SELECT name, times_accepted, times_completed, completion_rate_pct
FROM quest_completion_stats
ORDER BY completion_rate_pct DESC, name;

-- Gold and EXP sources for one character (parameter :character_id)
SELECT
    c.name,
    c.gold AS current_gold,
    c.exp AS current_exp,
    COALESCE(SUM(b.gold_gained), 0) AS gold_from_battles,
    COALESCE(SUM(b.exp_gained), 0) AS exp_from_battles
FROM characters c
LEFT JOIN battles b ON b.character_id = c.id
WHERE c.id = :character_id
GROUP BY c.id;

-- Inventory value
SELECT e.slot, e.name, i.quantity, e.price, i.quantity * e.price AS total_value
FROM inventory i
JOIN equipment e ON e.id = i.equipment_id
WHERE i.character_id = :character_id
ORDER BY e.slot, e.name;
