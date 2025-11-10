-- 3) 30-Day Rolling Sharpe (for strategy_id = 1), annualized with sqrt(252)
WITH w AS (
  SELECT
    date,
    net_pnl,
    AVG(net_pnl)      OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS mean_30,
    STDDEV_SAMP(net_pnl) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS std_30,
    COUNT(net_pnl)    OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS n_30
  FROM pnl_daily
  WHERE strategy_id = 1
)
SELECT
  date,
  mean_30,
  std_30,
  CASE
    WHEN n_30 >= 30 AND std_30 > 0
      THEN (mean_30 / std_30) * sqrt(252.0)
    ELSE NULL
  END AS rolling_sharpe_30
FROM w
ORDER BY date;