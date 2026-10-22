import { generateSessionToken, nameKey, normalizeCode, secretHash } from "@/lib/auth";
import { databaseConfigured, loadProfileBySessionHash, withTransaction } from "@/lib/db";
import { cleanName } from "@/lib/progress";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<Response> {
  if (!databaseConfigured()) {
    return Response.json({ error: "Databasen er ikke koblet til ennå." }, { status: 503 });
  }

  let body: { name?: unknown; code?: unknown };
  try {
    body = (await request.json()) as { name?: unknown; code?: unknown };
  } catch {
    return Response.json({ error: "Ugyldig forespørsel." }, { status: 400 });
  }
  const name = cleanName(String(body.name ?? ""));
  const code = normalizeCode(String(body.code ?? ""));
  if (name.length < 2 || code.length !== 8) {
    return Response.json({ error: "Skriv inn navn og den åttesifrede spillkoden." }, { status: 400 });
  }

  const sessionToken = generateSessionToken();
  const sessionHash = secretHash(sessionToken);
  const codeHash = secretHash(code);

  const profile = await withTransaction(async (client) => {
    const lookup = await client.query<{ id: string }>(
      `SELECT id FROM players WHERE name_key = $1 AND code_hash = $2 ORDER BY created_at DESC LIMIT 1`,
      [nameKey(name), codeHash],
    );
    if (lookup.rowCount !== 1) return null;
    await client.query(
      `INSERT INTO player_sessions (player_id, session_hash) VALUES ($1, $2)`,
      [lookup.rows[0].id, sessionHash],
    );
    return loadProfileBySessionHash(sessionHash, client);
  });

  if (!profile) {
    return Response.json({ error: "Fant ingen spiller med dette navnet og denne koden." }, { status: 404 });
  }
  return Response.json({ profile: { ...profile, token: sessionToken } });
}
