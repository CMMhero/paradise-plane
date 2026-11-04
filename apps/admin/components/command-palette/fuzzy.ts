/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: fuzzy scoring for the God Mode command palette
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Every word of the query has to land somewhere in the entry (title, keywords,
 * description, breadcrumb), so "email delay" finds the batch delay row even
 * though the two words sit in different fields. Each word is scored by how
 * well it lands, best first: whole word, start of a word, inside a word, one
 * typo away from a word, scattered letters. The field it lands in scales that.
 */

export type TFuzzyField = { text: string; weight: number };

/** Below this a scattered-letter match is noise ("ae" hits nearly everything). */
const MIN_SUBSEQUENCE_SCORE = 0.12;
/** Typos are only forgiven in words long enough that one edit is still a clear intent. */
const TYPO_MIN_LENGTH = 4;

const SCORE = {
  wholeWord: 1,
  wordStart: 0.85,
  inside: 0.6,
  typo: 0.45,
  subsequenceMax: 0.35,
  /** Added when the whole query appears as is in the first field (the title). */
  phraseBonus: 0.25,
} as const;

export const normalize = (text: string): string =>
  text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    // Setting keys (EMAIL_BATCH_DELAY_MINUTES) read as words.
    .replace(/[_\-./]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const isWordChar = (ch: string | undefined): boolean => ch !== undefined && /[\p{L}\p{N}]/u.test(ch);

/** Damerau-Levenshtein (optimal string alignment) distance, stopping early above `limit`. */
function editDistance(a: string, b: string, limit: number): number {
  if (Math.abs(a.length - b.length) > limit) return limit + 1;
  const rows: number[][] = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array<number>(b.length).fill(0)]);
  for (let j = 0; j <= b.length; j++) rows[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    let rowMin = Infinity;
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      let best = Math.min(rows[i - 1][j] + 1, rows[i][j - 1] + 1, rows[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1])
        best = Math.min(best, rows[i - 2][j - 2] + 1);
      rows[i][j] = best;
      rowMin = Math.min(rowMin, best);
    }
    if (rowMin > limit) return limit + 1;
  }
  return rows[a.length][b.length];
}

/** Letters of `token` in order inside `text`; tighter spans score higher. */
function subsequenceScore(token: string, text: string): number {
  let best = 0;
  // Try every start position of the first letter, keep the tightest span.
  for (let start = text.indexOf(token[0]); start !== -1; start = text.indexOf(token[0], start + 1)) {
    let pos = start;
    let ok = true;
    for (let k = 1; k < token.length; k++) {
      pos = text.indexOf(token[k], pos + 1);
      if (pos === -1) {
        ok = false;
        break;
      }
    }
    if (!ok) break;
    const span = pos - start + 1;
    const startsWord = !isWordChar(text[start - 1]);
    const score = SCORE.subsequenceMax * (token.length / span) * (startsWord ? 1 : 0.8);
    best = Math.max(best, score);
  }
  return best >= MIN_SUBSEQUENCE_SCORE ? best : 0;
}

/** How well one normalized query word lands in one normalized text, 0..1. */
export function tokenScore(token: string, text: string): number {
  if (!token || !text) return 0;

  let best = 0;
  for (let idx = text.indexOf(token); idx !== -1; idx = text.indexOf(token, idx + 1)) {
    const startsWord = !isWordChar(text[idx - 1]);
    const endsWord = !isWordChar(text[idx + token.length]);
    const score = startsWord ? (endsWord ? SCORE.wholeWord : SCORE.wordStart) : SCORE.inside;
    best = Math.max(best, score);
    if (best === SCORE.wholeWord) return best;
  }
  if (best > 0) return best;

  if (token.length >= TYPO_MIN_LENGTH) {
    for (const word of text.split(" ")) {
      // Compare against the word and against its prefix, so a typo in a partly typed word still counts.
      const prefix = word.slice(0, token.length);
      if (editDistance(token, word, 1) <= 1 || (word.length > token.length && editDistance(token, prefix, 1) <= 1)) {
        return SCORE.typo;
      }
    }
  }

  return subsequenceScore(token, text);
}

/**
 * Score of a query against weighted fields, 0 when any query word is missing.
 * The first field is treated as the title for the phrase bonus.
 */
export function fuzzyScore(query: string, fields: TFuzzyField[]): number {
  const q = normalize(query);
  if (!q) return 0;
  const tokens = q.split(" ");
  const normalized = fields.map((f) => ({ text: normalize(f.text), weight: f.weight }));

  let total = 0;
  for (const token of tokens) {
    let best = 0;
    for (const field of normalized) best = Math.max(best, tokenScore(token, field.text) * field.weight);
    if (best === 0) return 0;
    total += best;
  }

  const title = normalized[0]?.text ?? "";
  const bonus =
    tokens.length > 1 && title.includes(q) ? SCORE.phraseBonus : title.startsWith(q) ? SCORE.phraseBonus / 2 : 0;
  return total / tokens.length + bonus;
}
