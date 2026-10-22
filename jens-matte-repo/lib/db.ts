import { Pool, type PoolClient } from "pg";
import type { PlayerProfile, SkillProgress } from "@/lib/types";

const globalForDb = globalThis as unknown as { jensMattePool?: Pool };

export function databaseConfigured(): boolean {
  return Boolean(process.env.DATABASE_URL);
}

export function pool(): Pool {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is not configured");
  }
  if (!globalForDb.jensMattePool) {
    globalForDb.jensMattePool = new Pool({
      connectionString: process.env.DATABASE_URL,
      max: 8,
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 8_000,
      ssl: process.env.PGSSLMODE === "require" ? { rejectUnauthorized: false } : undefined,
    });
  }
  return globalForDb.jensMattePool;
}

export async function withTransaction<T>(fn: (client: PoolClient) => Promise<T>): Promise<T> {
  const client = await pool().connect();
  try {
    await client.query("BEGIN");
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function loadProfileBySessionHash(
  sessionHash: string,
  client: PoolClient | Pool = pool(),
): Promise<PlayerProfile | null> {
  const playerResult = await client.query(
    `SELECT p.id, p.name, p.xp, p.overall_level, p.recent_question_ids
       FROM player_sessions s
       JOIN players p ON p.id = s.player_id
      WHERE s.session_hash = $1
      LIMIT 1`,
    [sessionHash],
  );
  if (playerResult.rowCount === 0) return null;
  const row = playerResult.rows[0] as {
    id: string;
    name: string;
    xp: number;
    overall_level: number;
    recent_question_ids: string[] | null;
  };

  const skillResult = await client.query(
    `SELECT topic, skill, attempts, correct_count, mastery, level
       FROM skill_progress
      WHERE player_id = $1`,
    [row.id],
  );
  const skillProgress: Record<string, SkillProgress> = {};
  for (const skillRow of skillResult.rows as Array<{
    topic: string;
    skill: string;
    attempts: number;
    correct_count: number;
    mastery: number;
    level: number;
  }>) {
    skillProgress[`${skillRow.topic}::${skillRow.skill}`] = {
      topic: skillRow.topic,
      skill: skillRow.skill,
      attempts: Number(skillRow.attempts),
      correct: Number(skillRow.correct_count),
      mastery: Number(skillRow.mastery),
      level: Number(skillRow.level),
    };
  }

  return {
    id: row.id,
    name: row.name,
    xp: Number(row.xp),
    overallLevel: Number(row.overall_level),
    skillProgress,
    recentQuestionIds: Array.isArray(row.recent_question_ids) ? row.recent_question_ids : [],
    mode: "synced",
  };
}
