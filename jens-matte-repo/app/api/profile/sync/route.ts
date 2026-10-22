import { bearerToken, secretHash } from "@/lib/auth";
import { databaseConfigured, loadProfileBySessionHash } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  if (!databaseConfigured()) {
    return Response.json({ error: "Databasen er ikke koblet til ennå." }, { status: 503 });
  }
  const token = bearerToken(request);
  if (!token) return Response.json({ error: "Mangler spilløkt." }, { status: 401 });
  const profile = await loadProfileBySessionHash(secretHash(token));
  if (!profile) return Response.json({ error: "Spilløkten er utløpt." }, { status: 401 });
  return Response.json({ profile: { ...profile, token } });
}
