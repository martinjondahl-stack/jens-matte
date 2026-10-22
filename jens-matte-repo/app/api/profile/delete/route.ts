import { bearerToken, secretHash } from "@/lib/auth";
import { databaseConfigured, pool } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function DELETE(request: Request): Promise<Response> {
  if (!databaseConfigured()) {
    return Response.json({ error: "Databasen er ikke koblet til ennå." }, { status: 503 });
  }
  const token = bearerToken(request);
  if (!token) return Response.json({ error: "Mangler spilløkt." }, { status: 401 });

  const result = await pool().query(
    `DELETE FROM players
      WHERE id = (SELECT player_id FROM player_sessions WHERE session_hash = $1)`,
    [secretHash(token)],
  );
  if (result.rowCount !== 1) {
    return Response.json({ error: "Spilløkten er utløpt eller profilen er allerede slettet." }, { status: 404 });
  }
  return Response.json({ ok: true });
}
