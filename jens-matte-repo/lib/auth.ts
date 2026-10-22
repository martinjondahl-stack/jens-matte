import { createHash, randomBytes } from "node:crypto";

const ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";

export function generatePlayerCode(): string {
  const bytes = randomBytes(8);
  let raw = "";
  for (let i = 0; i < 8; i += 1) {
    raw += ALPHABET[bytes[i] % ALPHABET.length];
  }
  return `${raw.slice(0, 4)}-${raw.slice(4)}`;
}

export function normalizeCode(code: string): string {
  return code.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

export function generateSessionToken(): string {
  return randomBytes(32).toString("base64url");
}

export function secretHash(secret: string): string {
  const pepper = process.env.PROFILE_CODE_PEPPER || "jens-matte-local-development-pepper";
  return createHash("sha256").update(`${pepper}:${secret}`).digest("hex");
}

export function nameKey(name: string): string {
  return name.trim().toLocaleLowerCase("nb-NO").replace(/\s+/g, " ");
}

export function bearerToken(request: Request): string | null {
  const auth = request.headers.get("authorization");
  if (!auth?.startsWith("Bearer ")) return null;
  return auth.slice(7).trim() || null;
}
