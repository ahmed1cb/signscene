PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS sessions (
  id          TEXT PRIMARY KEY,
  caller_id   INTEGER NOT NULL,
  callee_id   INTEGER NOT NULL,
  state       TEXT NOT NULL DEFAULT 'ringing'
              CHECK(state IN ('ringing','accepted','active','ended','rejected','missed')),
  started_at  TEXT NOT NULL,
  answered_at TEXT NULL,
  ended_at    TEXT NULL,
  last_ping   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_state ON sessions(state);
CREATE INDEX IF NOT EXISTS idx_sessions_callee ON sessions(callee_id);

CREATE TABLE IF NOT EXISTS peers (
  user_id     INTEGER PRIMARY KEY,
  socket_id   TEXT NULL,
  status      TEXT NOT NULL DEFAULT 'offline'
              CHECK(status IN ('online','offline')),
  last_seen   TEXT NOT NULL
);
