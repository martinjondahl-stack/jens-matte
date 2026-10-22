CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS players (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  name_key TEXT NOT NULL,
  code_hash TEXT NOT NULL,
  xp INTEGER NOT NULL DEFAULT 0,
  overall_level INTEGER NOT NULL DEFAULT 3 CHECK (overall_level BETWEEN 1 AND 10),
  recent_question_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS players_name_key_idx ON players(name_key);
CREATE INDEX IF NOT EXISTS players_updated_at_idx ON players(updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS players_name_code_unique_idx ON players(name_key, code_hash);

CREATE TABLE IF NOT EXISTS player_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  session_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS player_sessions_player_idx ON player_sessions(player_id);
CREATE INDEX IF NOT EXISTS player_sessions_last_used_idx ON player_sessions(last_used_at DESC);

CREATE TABLE IF NOT EXISTS skill_progress (
  player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  topic TEXT NOT NULL,
  skill TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  correct_count INTEGER NOT NULL DEFAULT 0,
  mastery DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (mastery >= 0 AND mastery <= 1),
  level INTEGER NOT NULL DEFAULT 3 CHECK (level BETWEEN 1 AND 10),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (player_id, topic, skill)
);

CREATE TABLE IF NOT EXISTS rounds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  correct_count INTEGER NOT NULL,
  total_count INTEGER NOT NULL,
  xp_earned INTEGER NOT NULL,
  best_streak INTEGER NOT NULL DEFAULT 0,
  completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rounds_player_completed_idx ON rounds(player_id, completed_at DESC);

CREATE TABLE IF NOT EXISTS attempts (
  id BIGSERIAL PRIMARY KEY,
  round_id UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
  player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL,
  topic TEXT NOT NULL,
  skill TEXT NOT NULL,
  selected_option TEXT NOT NULL,
  correct BOOLEAN NOT NULL,
  used_hint BOOLEAN NOT NULL DEFAULT FALSE,
  response_ms INTEGER NOT NULL DEFAULT 0,
  xp_earned INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS attempts_player_created_idx ON attempts(player_id, created_at DESC);
CREATE INDEX IF NOT EXISTS attempts_question_idx ON attempts(question_id);
