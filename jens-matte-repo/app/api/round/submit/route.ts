import { bearerToken, secretHash } from "@/lib/auth";
import { databaseConfigured, loadProfileBySessionHash, withTransaction } from "@/lib/db";
import { questionById } from "@/lib/questions";
import { scoreAttempts } from "@/lib/progress";
import type { Attempt } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const OPTION_IDS = new Set(["A", "B", "C", "D"]);

export async function POST(request: Request): Promise<Response> {
  if (!databaseConfigured()) {
    return Response.json({ error: "Databasen er ikke koblet til ennå." }, { status: 503 });
  }
  const token = bearerToken(request);
  if (!token) return Response.json({ error: "Mangler spilløkt." }, { status: 401 });

  let body: { attempts?: unknown };
  try {
    body = (await request.json()) as { attempts?: unknown };
  } catch {
    return Response.json({ error: "Ugyldig forespørsel." }, { status: 400 });
  }
  if (!Array.isArray(body.attempts) || body.attempts.length < 1 || body.attempts.length > 20) {
    return Response.json({ error: "En runde må ha mellom 1 og 20 svar." }, { status: 400 });
  }

  const attempts: Attempt[] = [];
  for (const raw of body.attempts) {
    if (!raw || typeof raw !== "object") return Response.json({ error: "Ugyldig svarformat." }, { status: 400 });
    const item = raw as Record<string, unknown>;
    const questionId = String(item.questionId ?? "");
    const selectedOption = String(item.selectedOption ?? "");
    if (!questionById.has(questionId) || !OPTION_IDS.has(selectedOption)) {
      return Response.json({ error: "Runden inneholder et ukjent spørsmål eller svar." }, { status: 400 });
    }
    attempts.push({
      questionId,
      selectedOption: selectedOption as Attempt["selectedOption"],
      usedHint: Boolean(item.usedHint),
      responseMs: Math.max(0, Math.min(30 * 60 * 1000, Number(item.responseMs) || 0)),
    });
  }

  try {
    const result = await withTransaction(async (client) => {
      const sessionHash = secretHash(token);
      // Serialize updates for the same player so simultaneous iPhone/Mac rounds do not overwrite each other.
      await client.query(
        `SELECT p.id
           FROM player_sessions s
           JOIN players p ON p.id = s.player_id
          WHERE s.session_hash = $1
          FOR UPDATE OF p`,
        [sessionHash],
      );
      const current = await loadProfileBySessionHash(sessionHash, client);
      if (!current) throw new SessionError();
      const scored = scoreAttempts(current, attempts, questionById);

      const roundInsert = await client.query<{ id: string }>(
        `INSERT INTO rounds (player_id, correct_count, total_count, xp_earned, best_streak)
         VALUES ($1, $2, $3, $4, $5)
         RETURNING id`,
        [current.id, scored.summary.correct, scored.summary.total, scored.summary.xpEarned, scored.summary.bestStreak],
      );
      const roundId = roundInsert.rows[0].id;

      for (const attempt of scored.summary.scoredAttempts) {
        await client.query(
          `INSERT INTO attempts
            (round_id, player_id, question_id, topic, skill, selected_option, correct, used_hint, response_ms, xp_earned)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
          [roundId, current.id, attempt.questionId, attempt.topic, attempt.skill, attempt.selectedOption,
            attempt.correct, attempt.usedHint, attempt.responseMs, attempt.xpEarned],
        );
      }

      await client.query(
        `UPDATE players
            SET xp = $1, overall_level = $2, recent_question_ids = $3::jsonb, updated_at = NOW()
          WHERE id = $4`,
        [scored.profile.xp, scored.profile.overallLevel, JSON.stringify(scored.profile.recentQuestionIds), current.id],
      );

      for (const progress of Object.values(scored.profile.skillProgress)) {
        await client.query(
          `INSERT INTO skill_progress
            (player_id, topic, skill, attempts, correct_count, mastery, level, updated_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,NOW())
           ON CONFLICT (player_id, topic, skill)
           DO UPDATE SET attempts = EXCLUDED.attempts,
                         correct_count = EXCLUDED.correct_count,
                         mastery = EXCLUDED.mastery,
                         level = EXCLUDED.level,
                         updated_at = NOW()`,
          [current.id, progress.topic, progress.skill, progress.attempts, progress.correct, progress.mastery, progress.level],
        );
      }

      return { profile: { ...scored.profile, token, mode: "synced" as const }, summary: scored.summary };
    });
    return Response.json(result);
  } catch (error) {
    if (error instanceof SessionError) {
      return Response.json({ error: "Spilløkten er utløpt. Logg inn med spillkoden igjen." }, { status: 401 });
    }
    console.error("round submit failed", error);
    return Response.json({ error: "Kunne ikke lagre runden akkurat nå." }, { status: 500 });
  }
}

class SessionError extends Error {}
