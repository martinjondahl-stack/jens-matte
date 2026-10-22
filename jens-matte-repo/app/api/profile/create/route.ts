import { generatePlayerCode, generateSessionToken, nameKey, normalizeCode, secretHash } from "@/lib/auth";
import { databaseConfigured, loadProfileBySessionHash, withTransaction } from "@/lib/db";
import { cleanName } from "@/lib/progress";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<Response> {
  if (!databaseConfigured()) {
    return Response.json({ error: "Databasen er ikke koblet til ennå." }, { status: 503 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Ugyldig forespørsel." }, { status: 400 });
  }
  const rawName = typeof body === "object" && body && "name" in body ? String(body.name) : "";
  const name = cleanName(rawName);
  if (name.length < 2) {
    return Response.json({ error: "Navnet må ha minst to tegn." }, { status: 400 });
  }

  // A collision is extremely unlikely, but retry a few times so name + code stays unique.
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const playerCode = generatePlayerCode();
    const sessionToken = generateSessionToken();
    const sessionHash = secretHash(sessionToken);
    const codeHash = secretHash(normalizeCode(playerCode));

    try {
      const profile = await withTransaction(async (client) => {
        const playerResult = await client.query<{ id: string }>(
          `INSERT INTO players (name, name_key, code_hash)
           VALUES ($1, $2, $3)
           RETURNING id`,
          [name, nameKey(name), codeHash],
        );
        const playerId = playerResult.rows[0]?.id;
        if (!playerId) throw new Error("Player insert failed");
        await client.query(
          `INSERT INTO player_sessions (player_id, session_hash) VALUES ($1, $2)`,
          [playerId, sessionHash],
        );
        return loadProfileBySessionHash(sessionHash, client);
      });
      if (!profile) throw new Error("Profile load failed");
      return Response.json({
        profile: { ...profile, token: sessionToken, playerCode },
        playerCode,
      });
    } catch (error) {
      const maybePg = error as { code?: string };
      if (maybePg.code === "23505") continue;
      console.error("profile create failed", error);
      return Response.json({ error: "Kunne ikke opprette spilleren." }, { status: 500 });
    }
  }

  return Response.json({ error: "Kunne ikke lage en unik spillkode. Prøv igjen." }, { status: 503 });
}
