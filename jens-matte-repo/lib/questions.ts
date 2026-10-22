import bankJson from "@/data/questions.json";
import type { Question, QuestionBank } from "@/lib/types";

export const questionBank = bankJson as QuestionBank;
export const questions: Question[] = questionBank.questions;
export const questionById = new Map(questions.map((question) => [question.id, question]));
export const topics = [...new Set(questions.map((question) => question.topic))];
