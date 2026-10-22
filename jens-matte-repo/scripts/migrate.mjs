import fs from "node:fs/promises";
import path from "node:path";
import pg from "pg";

const { Pool } = pg;
const url = process.env.DATABASE_URL;
if (!url) {
  console.log("[migrate] DATABASE_URL is not set; running in local-only mode.");
  process.exit(0);
}

const pool = new Pool({
  connectionString: url,
  max: 1,
  ssl: process.env.PGSSLMODE === "require" ? { rejectUnauthorized: false } : undefined,
});

try {
  const migrationsDir = path.join(process.cwd(), "migrations");
  const files = (await fs.readdir(migrationsDir)).filter((file) => file.endsWith(".sql")).sort();
  for (const file of files) {
    const sql = await fs.readFile(path.join(migrationsDir, file), "utf8");
    console.log(`[migrate] Applying ${file}`);
    await pool.query(sql);
  }
  console.log("[migrate] Database is ready.");
} finally {
  await pool.end();
}
