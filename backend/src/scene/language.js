import nlp from 'compromise';

export const MAX_TERMS = 6;

const STOPWORDS = new Set([
  'a',
  'an',
  'the',
  'is',
  'are',
  'am',
  'was',
  'were',
  'be',
  'been',
  'being',
  'to',
  'of',
  'and',
  'or',
  'in',
  'on',
  'at',
  'for',
  'with',
  'from',
  'by',
  'as',
  'but',
  'so',
  'do',
  'does',
  'did',
  'have',
  'has',
  'had',
  'will',
  'would',
  'can',
  'could',
  'should',
  'may',
  'might',
  'must',
  'please',
]);

const CONTRACTIONS = new Map([
  ["don't", 'not'],
  ['dont', 'not'],
  ["doesn't", 'not'],
  ['doesnt', 'not'],
  ["didn't", 'not'],
  ['didnt', 'not'],
  ["won't", 'not'],
  ['wont', 'not'],
  ["can't", 'not'],
  ['cant', 'not'],
  ['cannot', 'not'],
  ["isn't", 'not'],
  ['isnt', 'not'],
  ["aren't", 'not'],
  ['arent', 'not'],
  ["wasn't", 'not'],
  ['wasnt', 'not'],
  ["weren't", 'not'],
  ['werent', 'not'],
  ["haven't", 'not'],
  ['havent', 'not'],
  ["hasn't", 'not'],
  ['hasnt', 'not'],
  ["hadn't", 'not'],
  ['hadnt', 'not'],
  ["shouldn't", 'not'],
  ['shouldnt', 'not'],
  ["wouldn't", 'not'],
  ['wouldnt', 'not'],
  ["couldn't", 'not'],
  ['couldnt', 'not'],
  ["mustn't", 'not'],
  ['mustnt', 'not'],
]);

const NUMBER_WORDS = new Map([
  ['zero', 0],
  ['one', 1],
  ['two', 2],
  ['three', 3],
  ['four', 4],
  ['five', 5],
  ['six', 6],
  ['seven', 7],
  ['eight', 8],
  ['nine', 9],
  ['ten', 10],
  ['eleven', 11],
  ['twelve', 12],
  ['thirteen', 13],
  ['fourteen', 14],
  ['fifteen', 15],
  ['sixteen', 16],
  ['seventeen', 17],
  ['eighteen', 18],
  ['nineteen', 19],
  ['twenty', 20],
  ['thirty', 30],
  ['forty', 40],
  ['fifty', 50],
  ['sixty', 60],
  ['seventy', 70],
  ['eighty', 80],
  ['ninety', 90],
  ['hundred', 100],
  ['thousand', 1000],
]);

const WORD_RE =
  /[\p{L}\p{M}]+(?:'[\p{L}\p{M}]+)*|\d+(?:[.,]\d+)?/gu;

function normalizeToken(value) {
  return String(value)
    .replace(/[\u2018\u2019\u201B`\u00B4]/g, "'")
    .toLowerCase();
}

export function normalizeKeyword(value) {
  return normalizeToken(value)
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function extractTerms(sentence) {
  const normalized = normalizeToken(sentence);
  const matches = normalized.match(WORD_RE) || [];

  const terms = [];
  for (const match of matches) {
    let word = match;
    if (word.endsWith("'s") && word.length > 2) {
      word = word.slice(0, -2);
    }
    for (const suffix of ["'re", "'ve", "'ll", "'d", "'m"]) {
      if (word.endsWith(suffix)) {
        word = word.slice(0, -suffix.length);
        break;
      }
    }
    word = CONTRACTIONS.get(word) || word;

    for (const part of word.split(/\s+/)) {
      if (!part || STOPWORDS.has(part)) continue;
      if (terms[terms.length - 1] === part) continue;
      terms.push(part);
      if (terms.length >= MAX_TERMS) return terms;
    }
  }
  return terms;
}

function documentTokens(sentence) {
  const document = nlp(sentence);
  const sentences = document.json({
    terms: { text: true, normal: true, tags: true },
  });
  const tokens = [];
  for (const item of sentences) {
    for (const token of item.terms || []) {
      if (token.text && token.text.trim()) tokens.push(token);
    }
  }
  return tokens;
}

function tokenKey(text) {
  return normalizeToken(text)
    .replace(/'s$/, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function tagsFor(term, tokenTags) {
  const key = tokenKey(term);
  if (tokenTags.has(key)) return tokenTags.get(key);

  const isolated = nlp(term).json({
    terms: { text: true, normal: true, tags: true },
  });
  return isolated[0]?.terms?.[0]?.tags || [];
}

function posFromTags(tags) {
  if (tags.includes('Value') || tags.includes('Cardinal')) return 'number';
  if (tags.includes('Verb')) return 'verb';
  if (tags.includes('Adjective')) return 'adjective';
  if (tags.includes('Noun')) return 'noun';
  if (tags.includes('Date') || tags.includes('Adverb')) return 'adverb';
  if (tags.includes('Negative')) return 'adverb';
  return 'other';
}

function lemmaFor(term, pos) {
  if (!term) return term;

  if (pos === 'verb') {
    return (
      nlp(term).tag('Verb').verbs().toInfinitive().text().trim() || term
    );
  }

  if (pos === 'noun') {
    return (
      nlp(term).tag('Noun').nouns().toSingular().text().trim() || term
    );
  }

  if (pos === 'adjective') {
    const forms = nlp(term).tag('Adjective').adjectives().conjugate();
    return forms?.[0]?.Adjective || term;
  }

  return term;
}

export function numericValue(term) {
  const normalized = normalizeKeyword(term);
  if (/^\d+$/.test(normalized)) return Number(normalized);
  return NUMBER_WORDS.get(normalized) ?? null;
}

export function analyzeSentence(sentence) {
  const terms = extractTerms(sentence);
  if (!terms.length) return [];

  const tokenTags = new Map();
  for (const token of documentTokens(normalizeToken(sentence))) {
    const key = tokenKey(token.text);
    if (key && !tokenTags.has(key)) tokenTags.set(key, token.tags || []);
  }

  return terms.map((term) => {
    const tags = tagsFor(term, tokenTags);
    const pos = posFromTags(tags);
    const number = numericValue(term);
    const lemma =
      number != null ? String(number) : lemmaFor(term, pos) || term;

    return {
      term,
      lemma,
      pos,
      number,
    };
  });
}
