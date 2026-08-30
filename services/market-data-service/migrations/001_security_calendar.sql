CREATE TABLE IF NOT EXISTS securities (
  security_id TEXT PRIMARY KEY,
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  version BIGINT NOT NULL DEFAULT 1,
  UNIQUE (exchange, symbol)
);
CREATE TABLE IF NOT EXISTS trading_calendar (
  market TEXT NOT NULL,
  trading_day DATE NOT NULL,
  is_trading_day BOOLEAN NOT NULL,
  PRIMARY KEY (market, trading_day)
);
CREATE TABLE IF NOT EXISTS outbox_events (
  event_id UUID PRIMARY KEY,
  subject TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  published_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS inbox_events (
  event_id UUID NOT NULL,
  consumer_name TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (event_id, consumer_name)
);
