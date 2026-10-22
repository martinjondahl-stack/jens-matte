export type QuestionType = "quick" | "standard" | "challenge";

export type VisualSpec = {
  type: string;
  [key: string]: unknown;
};

export type AnswerOption = {
  id: "A" | "B" | "C" | "D";
  text: string;
  feedback: string;
};

export type Question = {
  id: string;
  grade: 5 | 6 | 7;
  level: number;
  topic: string;
  skill: string;
  type: QuestionType;
  prompt: string;
  hint: string;
  options: AnswerOption[];
  correctOption: AnswerOption["id"];
  explanation: {
    summary: string;
    steps: string[];
    takeaway: string;
  };
  xp: number;
  visual: VisualSpec | null;
  tags: string[];
};

export type QuestionBank = {
  version: string;
  title: string;
  curriculum: string;
  generatedAt: string;
  description: string;
  schemaVersion: number;
  questions: Question[];
};

export type SkillProgress = {
  topic: string;
  skill: string;
  attempts: number;
  correct: number;
  mastery: number;
  level: number;
};

export type PlayerProfile = {
  id: string;
  name: string;
  xp: number;
  overallLevel: number;
  skillProgress: Record<string, SkillProgress>;
  recentQuestionIds: string[];
  mode: "local" | "synced";
  token?: string;
  playerCode?: string;
};

export type Attempt = {
  questionId: string;
  selectedOption: AnswerOption["id"];
  usedHint: boolean;
  responseMs: number;
};

export type ScoredAttempt = Attempt & {
  correct: boolean;
  xpEarned: number;
  topic: string;
  skill: string;
  level: number;
};

export type RoundSummary = {
  correct: number;
  total: number;
  xpEarned: number;
  bestStreak: number;
  scoredAttempts: ScoredAttempt[];
  focusSkills: SkillProgress[];
};
