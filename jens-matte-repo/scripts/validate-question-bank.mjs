import fs from "node:fs";

const bank = JSON.parse(fs.readFileSync(new URL("../data/questions.json", import.meta.url), "utf8"));
const questions = bank.questions;
const errors = [];
const ids = new Set();
const promptFingerprints = new Set();
const topicCounts = new Map();
const gradeCounts = new Map();
const levelCounts = new Map();
const typeCounts = new Map();
const visualCounts = new Map();
const targetTopics = new Map([
  ["Tall og regnearter", 70],
  ["Brøk", 75],
  ["Desimaltall", 50],
  ["Prosent", 55],
  ["Algebra og mønster", 50],
  ["Geometri", 45],
  ["Måling", 35],
  ["Statistikk og sannsynlighet", 35],
  ["Økonomi", 30],
  ["Problemløsing", 55],
]);
const supportedVisuals = new Set([
  "numberLine", "fractionBar", "fractionCompare", "percentGrid", "priceTag", "progressBar",
  "pattern", "functionTable", "rectangle", "triangle", "circle", "angles", "coordinateGrid",
  "compositeL", "ruler", "clockPair", "prism", "mapScale", "dataDots", "barChart",
  "probabilityBag", "dice", "receipt", "budget", "offers", "recipe", "tiledRectangle",
  "combinationGrid", "fractionTank",
]);
const optionIds = ["A", "B", "C", "D"];

if (!bank.version || !bank.curriculum || !bank.schemaVersion) errors.push("Bank metadata is incomplete");
if (!Array.isArray(questions)) errors.push("questions must be an array");
if (questions.length !== 500) errors.push(`Expected 500 questions, got ${questions.length}`);

for (const q of questions) {
  if (ids.has(q.id)) errors.push(`Duplicate id: ${q.id}`);
  ids.add(q.id);
  const fingerprint = `${q.prompt}|${q.options?.map((o) => o.text).join("|")}`.toLocaleLowerCase("nb-NO");
  if (promptFingerprints.has(fingerprint)) errors.push(`${q.id}: duplicate prompt/options`);
  promptFingerprints.add(fingerprint);

  topicCounts.set(q.topic, (topicCounts.get(q.topic) ?? 0) + 1);
  gradeCounts.set(q.grade, (gradeCounts.get(q.grade) ?? 0) + 1);
  levelCounts.set(q.level, (levelCounts.get(q.level) ?? 0) + 1);
  typeCounts.set(q.type, (typeCounts.get(q.type) ?? 0) + 1);

  if (!Number.isInteger(q.level) || q.level < 1 || q.level > 10) errors.push(`${q.id}: bad level`);
  if (![5, 6, 7].includes(q.grade)) errors.push(`${q.id}: bad grade`);
  if (!["quick", "standard", "challenge"].includes(q.type)) errors.push(`${q.id}: bad type`);
  if (!q.prompt?.trim() || !q.hint?.trim() || !q.skill?.trim()) errors.push(`${q.id}: missing text/skill`);
  if (!Number.isInteger(q.xp) || q.xp <= 0) errors.push(`${q.id}: bad XP`);
  if (!Array.isArray(q.options) || q.options.length !== 4) errors.push(`${q.id}: needs four options`);
  if (q.options?.map((o) => o.id).join("") !== optionIds.join("")) errors.push(`${q.id}: option ids must be A-D`);
  const optionTexts = new Set(q.options?.map((o) => o.text));
  if (optionTexts.size !== 4) errors.push(`${q.id}: duplicate option text`);
  if (q.options?.filter((o) => o.id === q.correctOption).length !== 1) errors.push(`${q.id}: bad correct option`);
  if (!q.explanation?.summary?.trim() || !q.explanation?.takeaway?.trim()) errors.push(`${q.id}: missing summary/takeaway`);
  if (!Array.isArray(q.explanation?.steps) || q.explanation.steps.length < 2) errors.push(`${q.id}: needs at least two worked steps`);
  for (const option of q.options ?? []) {
    if (!option.text?.trim()) errors.push(`${q.id}/${option.id}: empty option`);
    if (option.id !== q.correctOption && !option.feedback?.trim()) errors.push(`${q.id}/${option.id}: missing targeted feedback`);
  }
  if (q.visual) {
    visualCounts.set(q.visual.type, (visualCounts.get(q.visual.type) ?? 0) + 1);
    if (!supportedVisuals.has(q.visual.type)) errors.push(`${q.id}: unsupported visual ${q.visual.type}`);
  }
}

for (const [topic, expected] of targetTopics) {
  if ((topicCounts.get(topic) ?? 0) !== expected) {
    errors.push(`${topic}: expected ${expected}, got ${topicCounts.get(topic) ?? 0}`);
  }
}
if ([...gradeCounts.values()].reduce((a, b) => a + b, 0) !== 500) errors.push("grade counts do not sum to 500");
if ([...levelCounts.keys()].some((level) => level < 1 || level > 10)) errors.push("bad level distribution");
if ([...typeCounts.values()].reduce((a, b) => a + b, 0) !== 500) errors.push("type counts do not sum to 500");
if ([...visualCounts.values()].reduce((a, b) => a + b, 0) < 150) errors.push("too few visual questions");

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(
  `Question bank OK: ${questions.length} questions, ${topicCounts.size} topics, ` +
  `${[...visualCounts.values()].reduce((a, b) => a + b, 0)} visual tasks.`,
);
