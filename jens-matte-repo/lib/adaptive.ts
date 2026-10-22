import { skillKey } from "@/lib/progress";
import type { PlayerProfile, Question } from "@/lib/types";

export type RoundOptions = {
  topic?: string;
  size?: number;
  seed?: number;
};

export function selectAdaptiveRound(
  allQuestions: Question[],
  profile: PlayerProfile,
  options: RoundOptions = {},
): Question[] {
  const size = options.size ?? 10;
  const pool = allQuestions.filter((q) => !options.topic || q.topic === options.topic);
  const random = mulberry32(options.seed ?? Date.now());
  const selected: Question[] = [];
  const recent = new Set(profile.recentQuestionIds.slice(0, 40));

  // Guarantee variety: one visual and one challenge when possible.
  const visual = weightedPick(pool.filter((q) => q.visual), profile, recent, selected, random);
  if (visual) selected.push(visual);
  const challenge = weightedPick(
    pool.filter((q) => q.type === "challenge"),
    profile,
    recent,
    selected,
    random,
  );
  if (challenge && !selected.some((q) => q.id === challenge.id)) selected.push(challenge);

  while (selected.length < size) {
    const next = weightedPick(pool, profile, recent, selected, random);
    if (!next) break;
    selected.push(next);
  }

  // In the unlikely event a tight filter did not provide enough unique tasks.
  if (selected.length < size) {
    for (const question of shuffle(pool, random)) {
      if (!selected.some((q) => q.id === question.id)) selected.push(question);
      if (selected.length === size) break;
    }
  }

  return selected.slice(0, size);
}

function weightedPick(
  pool: Question[],
  profile: PlayerProfile,
  recent: Set<string>,
  selected: Question[],
  random: () => number,
): Question | undefined {
  const selectedIds = new Set(selected.map((q) => q.id));
  const topicCounts = new Map<string, number>();
  selected.forEach((q) => topicCounts.set(q.topic, (topicCounts.get(q.topic) ?? 0) + 1));
  const challengeCount = selected.filter((q) => q.type === "challenge").length;

  const candidates = pool
    .filter((q) => !selectedIds.has(q.id))
    .map((question) => {
      const progress = profile.skillProgress[skillKey(question.topic, question.skill)];
      const targetLevel = progress?.level ?? profile.overallLevel ?? 3;
      const mastery = progress?.mastery ?? 0.5;
      const levelDistance = Math.abs(question.level - targetLevel);
      let weight = Math.exp(-0.55 * levelDistance);
      weight *= 0.8 + (1 - mastery) * 1.6;
      weight *= recent.has(question.id) ? 0.08 : 1;
      weight *= 1 / (1 + (topicCounts.get(question.topic) ?? 0) * 0.7);
      if (question.type === "challenge" && challengeCount >= 2) weight *= 0.18;
      if (question.type === "quick") weight *= 1.08;
      weight *= 0.85 + random() * 0.3;
      return { question, weight };
    })
    .filter((item) => item.weight > 0);

  const total = candidates.reduce((sum, item) => sum + item.weight, 0);
  if (total <= 0 || candidates.length === 0) return undefined;
  let threshold = random() * total;
  for (const item of candidates) {
    threshold -= item.weight;
    if (threshold <= 0) return item.question;
  }
  return candidates[candidates.length - 1]?.question;
}

function shuffle<T>(items: T[], random: () => number): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function mulberry32(seed: number): () => number {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
