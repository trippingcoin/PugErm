import { REGION_ALIASES } from "/static/js/constants.js";

export function scoreClass(score) {
  if (score >= 70) return "score-high";
  if (score >= 50) return "score-mid";
  return "score-low";
}

export function riskClass(risk) {
  return `risk-${risk || "low"}`;
}

export function scoreToColor(score) {
  const x = Math.max(0, Math.min(100, Number(score) || 0));
  if (x >= 75) return "#10B981";
  if (x >= 60) return "#34D399";
  if (x >= 45) return "#F59E0B";
  return "#EF4444";
}

export function normalizeRegionName(name) {
  const normalized = String(name || "")
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/қ/g, "к")
    .replace(/ғ/g, "г")
    .replace(/ү/g, "у")
    .replace(/ұ/g, "у")
    .replace(/\s+/g, " ")
    .trim();
  return REGION_ALIASES[normalized] || normalized;
}

export function regionNameFromRecord(record) {
  const attrs = record?.attributes || {};
  return attrs["Область"] || attrs["область"] || "";
}

export function buildNarrativeText(record, lang = "ru") {
  const pos = (record.explanation?.positive || []).slice(0, 3).join(", ");
  const neg = (record.explanation?.negative || []).slice(0, 2).join(", ");
  if (lang === "kz") {
    const level = record.score >= 70 ? "жоғары" : (record.score >= 50 ? "орташа" : "төмен");
    return `Сіздің ұпайыңыз ${record.score.toFixed(1)}/100 — ${level} деңгей.\nКүшті жақтары: ${pos || "анықталмады"}.\nЖетілдіру бағыттары: ${neg || "жоқ"}.`;
  }
  const level = record.score >= 70 ? "высокий" : (record.score >= 50 ? "средний" : "низкий");
  return `Ваш скор: ${record.score.toFixed(1)}/100 — ${level} приоритет.\nСильные стороны: ${pos || "не определены"}.\nОбласти улучшения: ${neg || "отсутствуют"}.`;
}
