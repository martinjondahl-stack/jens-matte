import { databaseConfigured, pool } from "@/lib/db";
import { questions } from "@/lib/questions";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  let database = "not-configured";
  if (databaseConfigured()) {
    try {
      await pool().query("SELECT 1");
      database = "ok";
    } catch {
      database = "error";
    }
  }
  return Response.json({
    ok: database !== "error",
    app: "JENS MATTE 5.–7.",
    questions: questions.length,
    database,
    timestamp: new Date().toISOString(),
  });
}
