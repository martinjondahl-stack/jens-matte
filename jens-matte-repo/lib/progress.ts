import type {
  Attempt,
  PlayerProfile,
  Question,
  RoundSummary,
  ScoredAttempt,
  SkillProgress,
} from "@/lib/types";

export const DEFAULT_LEVEL = 3;

export function createLocalProfile(name: string): PlayerProfile {
  return {
    id: `local-${cryptoRandomId()}`,
    name: cleanName(name),
    xp: 0,
    overallLevel: DEFAULT_LEVEL,
    skillProgress: {},
    recentQuestionIds: [],
    mode: "local",
  };
}

export function cleanName(name: string): string {
  return name.trim().replace(/\s+/g, " ").slice(0, 24) || "Spiller";
}

function cryptoRandomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function skillKey(topic: string, skill: string): string {
  return `${topic}::${skill}`;
}

export function xpLevel(xp: number): number {
  // A gentle curve: level 2 at 300 XP, level 10 around 24k XP.
  return Math.max(1, Math.min(50, Math.floor(Math.sqrt(Math.max(0, xp) / 300)) + 1));
}

export function scoreAttempts(
  profile: PlayerProfile,
  attempts: Attempt[],
  questionMap: Map<string, Question>,
): { profile: PlayerProfile; summary: RoundSummary } {
  const next: PlayerProfile = {
    ...profile,
    skillProgress: { ...profile.skillProgress },
    recentQuestionIds: [...profile.recentQuestionIds],
  };

  let streak = 0;
  let bestStreak = 0;
  let xpEarned = 0;
  let correctCount = 0;
  const scoredAttempts: ScoredAttempt[] = [];

  for (const attempt of attempts) {
    const question = questionMap.get(attempt.questionId);
    if (!question) continue;

    const correct = attempt.selectedOption === question.correctOption;
    if (correct) {
      streak += 1;
      bestStreak = Math.max(bestStreak, streak);
      correctCount += 1;
    } else {
      streak = 0;
    }

    const streakBonus = correct ? Math.min(20, Math.max(0, streak - 1) * 2) : 0;
    const hintMultiplier = attempt.usedHint ? 0.7 : 1;
    const attemptXp = correct
      ? Math.max(1, Math.round((question.xp + streakBonus) * hintMultiplier))
      : 0;

    xpEarned += attemptXp;
    scoredAttempts.push({
      ...attempt,
      correct,
      xpEarned: attemptXp,
      topic: question.topic,
      skill: question.skill,
      level: question.level,
    });

    const key = skillKey(question.topic, question.skill);
    const current = next.skillProgress[key] ?? {
      topic: question.topic,
      skill: question.skill,
      attempts: 0,
      correct: 0,
      mastery: 0.5,
      level: Math.max(1, Math.min(10, profile.overallLevel)),
    };

    const attemptsCount = current.attempts + 1;
    const correctTotal = current.correct + (correct ? 1 : 0);
    const recencyWeight = question.type === "challenge" ? 0.24 : 0.18;
    const updatedMastery = clamp(
      current.mastery * (1 - recencyWeight) + (correct ? 1 : 0) * recencyWeight,
      0.05,
      0.98,
    );

    let updatedLevel = current.level;
    if (attemptsCount >= 4 && updatedMastery >= 0.8 && question.level >= updatedLevel - 1) {
      updatedLevel = Math.min(10, updatedLevel + 1);
    } else if (attemptsCount >= 4 && updatedMastery < 0.42) {
      updatedLevel = Math.max(1, updatedLevel - 1);
    }

    next.skillProgress[key] = {
      ...current,
      attempts: attemptsCount,
      correct: correctTotal,
      mastery: Number(updatedMastery.toFixed(4)),
      level: updatedLevel,
    };
  }

  next.xp += xpEarned;
  next.overallLevel = Math.max(1, Math.min(10, Math.round(averageSkillLevel(next))));
  if (Object.keys(next.skillProgress).length === 0) {
    next.overallLevel = Math.min(10, xpLevel(next.xp));
  }
  next.recentQuestionIds = [
    ...attempts.map((attempt) => attempt.questionId),
    ...next.recentQuestionIds,
  ].slice(0, 60);

  const focusSkills = Object.values(next.skillProgress)
    .sort((a, b) => a.mastery - b.mastery || b.attempts - a.attempts)
    .slice(0, 3);

  return {
    profile: next,
    summary: {
      correct: correctCount,
      total: attempts.length,
      xpEarned,
      bestStreak,
      scoredAttempts,
      focusSkills,
    },
  };
}

function averageSkillLevel(profile: PlayerProfile): number {
  const values = Object.values(profile.skillProgress);
  if (values.length === 0) return profile.overallLevel || DEFAULT_LEVEL;
  const weighted = values.reduce((sum, item) => sum + item.level * Math.min(8, item.attempts + 1), 0);
  const weights = values.reduce((sum, item) => sum + Math.min(8, item.attempts + 1), 0);
  return weighted / Math.max(1, weights);
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
