-- 2) "Last Known Position per Symbol" View (latest row per (symbol, strategy_id))
CREATE OR REPLACE VIEW last_known_position_per_symbol AS
SELECT
  symbol,
  strategy_id,
  quantity,
  ts
FROM (
  SELECT
    p.*,
    ROW_NUMBER() OVER (PARTITION BY p.symbol, p.strategy_id ORDER BY p.ts DESC) AS rn
  FROM positions p
) x
WHERE rn = 1;