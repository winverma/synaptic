-- ======================================================================
-- bars_1m: 1-minute OHLCV bars (large time-series; recommend partitioning)
-- ======================================================================
CREATE TABLE bars_1m (
    bar_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    symbol          TEXT        NOT NULL,
    ts              TIMESTAMPTZ NOT NULL,          -- bar start timestamp (UTC)
    open            NUMERIC(18,8) NOT NULL,
    high            NUMERIC(18,8) NOT NULL,
    low             NUMERIC(18,8) NOT NULL,
    close           NUMERIC(18,8) NOT NULL,
    volume          NUMERIC(28,12) NOT NULL,
    vwap            NUMERIC(18,8),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (symbol, ts)                                -- prevent duplicate bars
);
-- Partitioning suggestion:
-- ALTER TABLE bars_1m PARTITION BY RANGE (ts);
-- CREATE TABLE bars_1m_2025_11 PARTITION OF bars_1m FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
-- Repeat per month to improve pruning and retention management.
CREATE INDEX ix_bars_1m_symbol_ts ON bars_1m (symbol, ts);
CREATE INDEX ix_bars_1m_ts ON bars_1m (ts);

-- ============================================================
-- orders: live/ historical orders placed by strategies
-- ============================================================
CREATE TABLE orders (
    order_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    strategy_id     BIGINT       NOT NULL,
    symbol          TEXT         NOT NULL,
    side            TEXT         NOT NULL CHECK (side IN ('BUY','SELL')),
    order_type      TEXT         NOT NULL CHECK (order_type IN ('LIMIT','MARKET','STOP','STOP_LIMIT')),
    status          TEXT         NOT NULL CHECK (status IN ('NEW','PARTIAL','FILLED','CANCELLED','REJECTED')),
    qty             NUMERIC(28,12) NOT NULL,
    price           NUMERIC(18,8),                 -- optional for market orders (NULL)
    time_in_force   TEXT CHECK (time_in_force IN ('GTC','IOC','FOK','DAY')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    parent_order_id BIGINT,                        -- for OCO / bracket structures
    notes           TEXT,
    CONSTRAINT fk_orders_parent FOREIGN KEY (parent_order_id) REFERENCES orders(order_id) ON DELETE SET NULL
);
CREATE INDEX ix_orders_strategy_symbol_status ON orders (strategy_id, symbol, status);
CREATE INDEX ix_orders_symbol_created_at ON orders (symbol, created_at);
CREATE INDEX ix_orders_strategy_created_at ON orders (strategy_id, created_at);

-- ============================================================
-- trades: executions/fills (can be high volume; index heavily)
-- ============================================================
CREATE TABLE trades (
    trade_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        BIGINT       NOT NULL,
    strategy_id     BIGINT       NOT NULL,
    symbol          TEXT         NOT NULL,
    ts              TIMESTAMPTZ  NOT NULL,          -- execution timestamp (UTC)
    side            TEXT         NOT NULL CHECK (side IN ('BUY','SELL')),
    qty             NUMERIC(28,12) NOT NULL,
    price           NUMERIC(18,8)  NOT NULL,
    fee             NUMERIC(18,8)  DEFAULT 0.0,
    liquidity       TEXT CHECK (liquidity IN ('MAKER','TAKER')),
    venue           TEXT,
    created_at      TIMESTAMPTZ   DEFAULT NOW(),
    CONSTRAINT fk_trades_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);
-- Consider partitioning if volume is extreme:
-- ALTER TABLE trades PARTITION BY RANGE (ts);
-- CREATE TABLE trades_2025_11 PARTITION OF trades FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE INDEX ix_trades_symbol_ts ON trades (symbol, ts);
CREATE INDEX ix_trades_strategy_ts ON trades (strategy_id, ts);
CREATE INDEX ix_trades_order_id ON trades (order_id);

-- ============================================================
-- positions: current net position per (strategy, symbol)
-- ============================================================
CREATE TABLE positions (
    position_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    strategy_id     BIGINT       NOT NULL,
    symbol          TEXT         NOT NULL,
    qty             NUMERIC(28,12) NOT NULL DEFAULT 0.0,
    avg_price       NUMERIC(18,8),
    realized_pnl    NUMERIC(18,8) NOT NULL DEFAULT 0.0,
    unrealized_pnl  NUMERIC(18,8) NOT NULL DEFAULT 0.0,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_positions_strategy_symbol UNIQUE (strategy_id, symbol)
);
CREATE INDEX ix_positions_strategy_symbol ON positions (strategy_id, symbol);

-- ============================================================
-- pnl_daily: aggregated daily PnL per (strategy, symbol)
-- ============================================================
CREATE TABLE pnl_daily (
    strategy_id     BIGINT       NOT NULL,
    symbol          TEXT         NOT NULL,
    trade_date      DATE         NOT NULL,
    realized_pnl    NUMERIC(18,8) NOT NULL DEFAULT 0.0,
    unrealized_pnl  NUMERIC(18,8) NOT NULL DEFAULT 0.0,
    fees            NUMERIC(18,8) NOT NULL DEFAULT 0.0,
    volume          NUMERIC(28,12) NOT NULL DEFAULT 0.0,
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (strategy_id, symbol, trade_date)
);
-- Partitioning suggestion (range by trade_date):
-- ALTER TABLE pnl_daily PARTITION BY RANGE (trade_date);
-- CREATE TABLE pnl_daily_2025_11 PARTITION OF pnl_daily FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE INDEX ix_pnl_daily_symbol_date ON pnl_daily (symbol, trade_date);
CREATE INDEX ix_pnl_daily_strategy_date ON pnl_daily (strategy_id, trade_date);

-- ============================================================
-- Suggested foreign key relationships (optional based on broader schema):
-- (Not enforced here beyond trades->orders; consider separate strategy table)
-- ============================================================
-- Potential future table:
-- CREATE TABLE strategies (
--     strategy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
--     name        TEXT NOT NULL UNIQUE
-- );
-- Then add FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id) to orders/trades/positions/pnl_daily.

-- End of schema