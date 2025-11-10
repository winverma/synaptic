-- 1) Daily PnL Rollup and Max Drawdown (for strategy_id = 1)
WITH pnl AS (
  SELECT
    date,
    net_pnl,
    SUM(net_pnl) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_pnl
  FROM pnl_daily
  WHERE strategy_id = 1
),
peaks AS (
  SELECT
    date,
    cum_pnl,
    MAX(cum_pnl) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_peak
  FROM pnl
)
SELECT
  date,
  cum_pnl,
  (running_peak - cum_pnl) AS drawdown,
  MAX(running_peak - cum_pnl) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS max_drawdown_to_date
FROM peaks
ORDER BY date;