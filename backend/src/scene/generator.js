import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import sharp from 'sharp';

import { analyzeSentence, normalizeKeyword } from './language.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SEARCH_URL = 'https://api.arasaac.org/v1/pictograms/{lang}/search/{term}';
const BESTSEARCH_URL =
  'https://api.arasaac.org/v1/pictograms/{lang}/bestsearch/{term}';
const IMAGE_URL = 'https://static.arasaac.org/pictograms/{pid}/{pid}_500.png';

const LANG =
  process.env.ARASAAC_LANG || process.env.CWB_ARASAAC_LANG || 'en';
const REQUEST_TIMEOUT_MS = 20_000;
const MAX_SCENE_CHARS = 3_000_000;
const CACHE_DIR = process.env.ARASAAC_CACHE_DIR
  ? path.resolve(process.env.ARASAAC_CACHE_DIR)
  : path.resolve(__dirname, '../../data/arasaac');
const LEXICON_PATH = path.resolve(__dirname, '../../data/scene_lexicon.json');

const CANVAS_WIDTH = 1200;
const CANVAS_MARGIN = 56;
const HEADER_HEIGHT = 150;
const BOTTOM_PADDING = 52;
const ROW_GAP = 64;
const COLUMN_GAP = 36;
const CARD_RADIUS = 24;
const ACCENT = '#2563EB';
const INK = '#0F172A';
const MUTED = '#64748B';
const BORDER = '#DDE4EE';
const CANVAS_BG = '#F3F6FB';
const CARD_BG = '#FFFFFF';
const FONT_STACK = "'Noto Sans','DejaVu Sans',sans-serif";

const candidateCache = new Map();
let lexiconPromise = null;

export class SceneGenerationError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'SceneGenerationError';
    this.status = status;
  }
}

async function loadLexicon() {
  if (!lexiconPromise) {
    lexiconPromise = fs
      .readFile(LEXICON_PATH, 'utf8')
      .then((raw) => JSON.parse(raw))
      .catch((error) => {
        if (error.code !== 'ENOENT') {
          console.warn('scene lexicon could not be loaded:', error.message);
        }
        return {};
      });
  }
  return lexiconPromise;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function httpGet(url, attempt = 1) {
  let response;
  try {
    response = await fetch(url, {
      headers: { 'User-Agent': 'cwb/1.0' },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    if (attempt < 3) {
      await delay(attempt * 500);
      return httpGet(url, attempt + 1);
    }
    throw new SceneGenerationError(502, `ARASAAC request failed: ${error.message}`);
  }

  if (!response.ok) {
    if ([429, 500, 502, 503, 504].includes(response.status) && attempt < 3) {
      await delay(attempt * 500);
      return httpGet(url, attempt + 1);
    }

    const error = new SceneGenerationError(
      502,
      `ARASAAC request failed with status ${response.status}`
    );
    error.upstreamStatus = response.status;
    throw error;
  }

  return Buffer.from(await response.arrayBuffer());
}

function keywordUrl(base, term) {
  return base.replace('{lang}', encodeURIComponent(LANG)).replace(
    '{term}',
    encodeURIComponent(term)
  );
}

async function fetchCandidatesFrom(url) {
  let data;
  try {
    data = JSON.parse((await httpGet(url)).toString('utf8'));
  } catch (error) {
    if (error.upstreamStatus === 404) return [];
    throw error;
  }
  return Array.isArray(data) ? data : [];
}

async function candidatesFor(concept) {
  const query =
    concept.number != null ? String(concept.number) : concept.lemma || concept.term;
  if (candidateCache.has(query)) return candidateCache.get(query);

  let data = await fetchCandidatesFrom(keywordUrl(SEARCH_URL, query));
  if (!data.length) {
    data = await fetchCandidatesFrom(keywordUrl(BESTSEARCH_URL, query));
  }

  const candidates = data
    .slice(0, 120)
    .filter((item) => Number.isFinite(Number(item?._id)))
    .map((item, index) => ({
      ...item,
      _id: Number(item._id),
      _rank: index,
    }));

  candidateCache.set(query, candidates);
  return candidates;
}

function keywordTypeMatches(type, pos) {
  if (pos === 'noun') return type === 2;
  if (pos === 'verb') return type === 3;
  if (pos === 'adjective') return type === 4;
  if (pos === 'adverb') return type === 6;
  if (pos === 'other') return true;
  return false;
}

function hasTimeTag(candidate) {
  const tags = (candidate.tags || []).map(normalizeKeyword);
  const categories = (candidate.categories || []).map(normalizeKeyword);
  return (
    tags.includes('time') ||
    tags.includes('unit of time') ||
    tags.includes('day hours') ||
    categories.includes('day hours')
  );
}

function contextMatches(candidate, context) {
  const text = normalizeKeyword(
    [
      ...(candidate.keywords || []).map((item) => item.keyword),
      ...(candidate.keywords || []).map((item) => item.meaning || ''),
      ...(candidate.tags || []),
      ...(candidate.categories || []),
    ].join(' ')
  );

  let matches = 0;
  for (const token of context) {
    if (!token || token.length < 3 || matches >= 5) continue;
    const pattern = new RegExp(`\\b${token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`);
    if (pattern.test(text)) matches += 1;
  }
  return matches;
}

function scoreCandidate(candidate, concept, context) {
  const keywords = candidate.keywords || [];
  const searchTerms = new Set(
    [
      normalizeKeyword(concept.term),
      normalizeKeyword(concept.lemma),
      concept.number != null ? String(concept.number) : '',
    ].filter(Boolean)
  );

  let score = 0;
  const exact = keywords.filter((item) =>
    searchTerms.has(normalizeKeyword(item.keyword))
  );

  if (exact.length) {
    score += 120;
    if (concept.pos !== 'number' && exact.some((item) => keywordTypeMatches(item.type, concept.pos))) {
      score += 80;
    }
  } else {
    const partial = keywords.some((item) =>
      normalizeKeyword(item.keyword).includes(normalizeKeyword(concept.lemma))
    );
    if (partial) score += 20;
  }

  score += contextMatches(candidate, context) * 12;

  if (concept.number != null) {
    if (hasTimeTag(candidate)) score -= 120;
    if (concept.number >= 0 && concept.number <= 10 && candidate.skin) {
      score += 35;
    }
  }

  return score;
}

function displayLabel(term) {
  return term.replace(/^\p{L}/u, (char) => char.toUpperCase());
}

async function lookupConcept(concept, context) {
  const lexicon = await loadLexicon();
  const override =
    lexicon?.[concept.term] ||
    lexicon?.[concept.lemma] ||
    (concept.number != null ? lexicon?.[String(concept.number)] : null);

  if (override && override.id != null) {
    const id = Number(override.id);
    return {
      id: Number.isFinite(id) ? id : null,
      label: override.label ? String(override.label) : displayLabel(concept.term),
    };
  }

  const candidates = await candidatesFor(concept);
  if (!candidates.length) {
    return {
      id: null,
      label: displayLabel(concept.term),
    };
  }

  const localContext = context.filter((term) => term !== concept.lemma);
  const ranked = [...candidates].sort((left, right) => {
    const scoreDelta =
      scoreCandidate(right, concept, localContext) -
      scoreCandidate(left, concept, localContext);
    if (scoreDelta) return scoreDelta;
    if (left._rank !== right._rank) return left._rank - right._rank;
    return left._id - right._id;
  });

  return {
    id: ranked[0]._id,
    label: displayLabel(concept.term),
  };
}

async function fetchImage(pid) {
  await fs.mkdir(CACHE_DIR, { recursive: true });
  const file = path.join(CACHE_DIR, `${pid}.png`);

  try {
    const cached = await fs.readFile(file);
    if (cached.length) return cached;
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }

  let raw;
  try {
    raw = await httpGet(IMAGE_URL.replaceAll('{pid}', String(pid)));
  } catch (error) {
    if (error.upstreamStatus === 404) return null;
    throw error;
  }

  await fs.writeFile(file, raw);
  return raw;
}

async function resolveSteps(sentence) {
  const concepts = analyzeSentence(sentence);
  if (!concepts.length) {
    throw new SceneGenerationError(422, 'sentence has no usable words');
  }

  const context = concepts.map((concept) => concept.lemma);
  const steps = [];
  for (const concept of concepts) {
    const meta = await lookupConcept(concept, context);
    steps.push({
      term: concept.term,
      lemma: concept.lemma,
      label: meta.label || concept.term,
      pictogramId: meta.id ?? null,
    });
  }
  return steps;
}

async function buildSteps(sentence) {
  const steps = await resolveSteps(sentence);
  for (const step of steps) {
    step.image =
      step.pictogramId == null ? null : await fetchImage(step.pictogramId);
  }
  return steps;
}

function escapeXml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    switch (char) {
      case '&':
        return '&amp;';
      case '<':
        return '&lt;';
      case '>':
        return '&gt;';
      case '"':
        return '&quot;';
      default:
        return '&apos;';
    }
  });
}

function estimateMaxChars(width, fontSize) {
  return Math.max(8, Math.floor(width / (fontSize * 0.56)));
}

function wrapText(text, maxChars, maxLines) {
  const words = String(text).trim().split(/\s+/).filter(Boolean);
  if (!words.length) return [''];

  const lines = [];
  let line = '';
  let index = 0;

  while (index < words.length && lines.length < maxLines) {
    const word = words[index];
    if (!line && word.length > maxChars) {
      lines.push(`${word.slice(0, Math.max(1, maxChars - 1))}\u2026`);
      index += 1;
      continue;
    }

    const candidate = line ? `${line} ${word}` : word;
    if (candidate.length <= maxChars || !line) {
      line = candidate;
      index += 1;
      continue;
    }

    lines.push(line);
    line = '';
  }

  if (line && lines.length < maxLines) lines.push(line);

  if (index < words.length) {
    let last = lines[lines.length - 1] || '';
    last = last.replace(/[\s,.;:!?]+$/u, '');
    if (last.length > maxChars - 1) {
      last = last.slice(0, Math.max(0, maxChars - 1));
    }
    lines[lines.length - 1] = `${last}\u2026`;
  }

  return lines.length ? lines : [''];
}

function textMarkup(lines, { x, y, size, lineHeight, fill, weight, anchor }) {
  return lines
    .map(
      (line, index) =>
        `<text x="${x}" y="${y + index * lineHeight}" text-anchor="${anchor}" font-family="${FONT_STACK}" font-size="${size}" font-weight="${weight}" fill="${fill}">${escapeXml(
          line
        )}</text>`
    )
    .join('');
}

function cardLayout(count) {
  const cols = count === 1 ? 1 : count === 2 ? 2 : 3;
  const rows = Math.ceil(count / cols);

  let cardWidth;
  let cardHeight;
  let pictogramSize;
  if (cols === 1) {
    cardWidth = 520;
    cardHeight = 480;
    pictogramSize = 330;
  } else if (cols === 2) {
    cardWidth = 512;
    cardHeight = 420;
    pictogramSize = 280;
  } else {
    cardWidth = 344;
    cardHeight = 372;
    pictogramSize = 230;
  }

  const top = HEADER_HEIGHT + 10;
  const height =
    top + rows * cardHeight + (rows - 1) * ROW_GAP + BOTTOM_PADDING;

  return {
    cols,
    rows,
    cardWidth,
    cardHeight,
    pictogramSize,
    top,
    width: CANVAS_WIDTH,
    height,
  };
}

function cardPosition(index, count, layout) {
  const row = Math.floor(index / layout.cols);
  const column = index % layout.cols;
  const countInRow = Math.min(layout.cols, count - row * layout.cols);
  const rowWidth =
    countInRow * layout.cardWidth + (countInRow - 1) * COLUMN_GAP;
  const rowStartX = (layout.width - rowWidth) / 2;
  const x = rowStartX + column * (layout.cardWidth + COLUMN_GAP);
  const y = layout.top + row * (layout.cardHeight + ROW_GAP);
  return { x, y, row, countInRow };
}

function arrowHead(x, y, direction) {
  if (direction === 'down') {
    return `<polygon points="${x},${y} ${x - 6},${y - 11} ${x + 6},${y - 11}" fill="${ACCENT}"/>`;
  }
  return `<polygon points="${x},${y} ${x - 11},${y - 6} ${x - 11},${y + 6}" fill="${ACCENT}"/>`;
}

function placeholderMarkup(x, y, size) {
  return `<g opacity="0.35">
    <rect x="${x}" y="${y}" width="${size}" height="${size}" rx="18" fill="none" stroke="${MUTED}" stroke-width="3" stroke-dasharray="10 8"/>
    <circle cx="${x + size * 0.32}" cy="${y + size * 0.30}" r="${size * 0.07}" fill="${MUTED}"/>
    <path d="M ${x + size * 0.16} ${y + size * 0.72} L ${x + size * 0.38} ${y + size * 0.46} L ${x + size * 0.56} ${y + size * 0.62} L ${x + size * 0.68} ${y + size * 0.52} L ${x + size * 0.84} ${y + size * 0.72} Z" fill="${MUTED}"/>
  </g>`;
}

function buildSvg(steps, sentence) {
  const layout = cardLayout(steps.length);
  const margin = CANVAS_MARGIN;
  const headerMaxChars = estimateMaxChars(layout.width - 2 * margin - 32, 34);
  const headerLines = wrapText(sentence, headerMaxChars, 2);
  const headerHeight = headerLines.length * 44;

  const parts = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${layout.width}" height="${layout.height}" viewBox="0 0 ${layout.width} ${layout.height}">`,
    `<rect width="${layout.width}" height="${layout.height}" fill="${CANVAS_BG}"/>`,
    `<circle cx="${layout.width - 80}" cy="40" r="170" fill="${ACCENT}" opacity="0.04"/>`,
    `<circle cx="60" cy="${layout.height - 40}" r="130" fill="${ACCENT}" opacity="0.035"/>`,
    `<rect x="${margin}" y="38" width="6" height="${headerHeight}" rx="3" fill="${ACCENT}"/>`,
    textMarkup(headerLines, {
      x: margin + 24,
      y: 66,
      size: 34,
      lineHeight: 44,
      fill: INK,
      weight: 700,
      anchor: 'start',
    }),
  ];

  const positions = steps.map((_, index) =>
    cardPosition(index, steps.length, layout)
  );

  const labelSize = layout.cols === 1 ? 28 : layout.cols === 2 ? 26 : 23;
  const labelLineHeight = labelSize + 5;

  for (let index = 0; index < steps.length; index += 1) {
    const step = steps[index];
    const position = positions[index];
    const cardX = position.x;
    const cardY = position.y;
    const cardW = layout.cardWidth;
    const cardH = layout.cardHeight;

    const labelMaxChars = estimateMaxChars(cardW - 34, labelSize);
    const labelLines = wrapText(step.label, labelMaxChars, 2);
    const labelBlockHeight = labelLines.length * labelLineHeight;
    const labelBlockTop = cardY + cardH - 20 - labelBlockHeight;
    const pictureTop = cardY + 38;
    const pictureBottom = labelBlockTop - 12;
    const available = Math.max(110, pictureBottom - pictureTop);
    const pictureSize = Math.max(
      110,
      Math.min(layout.pictogramSize, cardW - 40, available)
    );
    const pictureX = cardX + (cardW - pictureSize) / 2;
    const pictureY = pictureTop + (available - pictureSize) / 2;

    parts.push(
      `<rect x="${cardX + 2}" y="${cardY + 8}" width="${cardW}" height="${cardH}" rx="${CARD_RADIUS}" fill="${INK}" opacity="0.055"/>`,
      `<rect x="${cardX}" y="${cardY}" width="${cardW}" height="${cardH}" rx="${CARD_RADIUS}" fill="${CARD_BG}" stroke="${BORDER}" stroke-width="2"/>`
    );

    if (step.image) {
      const data = `data:image/png;base64,${step.image.toString('base64')}`;
      parts.push(
        `<image href="${data}" x="${pictureX}" y="${pictureY}" width="${pictureSize}" height="${pictureSize}" preserveAspectRatio="xMidYMid meet"/>`
      );
    } else {
      parts.push(placeholderMarkup(pictureX, pictureY, pictureSize));
    }

    const badgeX = cardX + 26;
    const badgeY = cardY + 26;
    parts.push(
      `<circle cx="${badgeX}" cy="${badgeY}" r="21" fill="${ACCENT}"/>`,
      `<text x="${badgeX}" y="${badgeY + 7}" text-anchor="middle" font-family="${FONT_STACK}" font-size="20" font-weight="700" fill="#FFFFFF">${
        index + 1
      }</text>`,
      textMarkup(labelLines, {
        x: cardX + cardW / 2,
        y: labelBlockTop + labelSize,
        size: labelSize,
        lineHeight: labelLineHeight,
        fill: INK,
        weight: 600,
        anchor: 'middle',
      })
    );
  }

  for (let index = 0; index + 1 < steps.length; index += 1) {
    const current = positions[index];
    const next = positions[index + 1];
    if (current.row !== next.row) continue;

    const y = current.y + layout.cardHeight * 0.45;
    const fromX = current.x + layout.cardWidth + 6;
    const toX = next.x - 6;

    parts.push(
      `<line x1="${fromX}" y1="${y}" x2="${toX}" y2="${y}" stroke="${ACCENT}" stroke-width="3" stroke-linecap="round" opacity="0.75"/>`,
      arrowHead(toX, y, 'right')
    );
  }

  for (let row = 0; row + 1 < layout.rows; row += 1) {
    const lastIndex = Math.min(
      steps.length - 1,
      row * layout.cols +
        Math.min(layout.cols, steps.length - row * layout.cols) -
        1
    );
    const nextIndex = (row + 1) * layout.cols;
    const last = positions[lastIndex];
    const next = positions[nextIndex];
    if (!last || !next) continue;

    const startX = last.x + layout.cardWidth / 2;
    const startY = last.y + layout.cardHeight + 8;
    const endX = next.x + layout.cardWidth / 2;
    const endY = next.y - 8;
    const midY = (startY + endY) / 2;

    parts.push(
      `<path d="M ${startX} ${startY} L ${startX} ${midY} L ${endX} ${midY} L ${endX} ${endY}" fill="none" stroke="${ACCENT}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.55"/>`,
      arrowHead(endX, endY, 'down')
    );
  }

  parts.push('</svg>');
  return { svg: parts.join(''), layout };
}

async function compose(steps, sentence) {
  const { svg, layout } = buildSvg(steps, sentence);
  const buffer = await sharp(Buffer.from(svg))
    .jpeg({ quality: 88, chromaSubsampling: '4:4:4' })
    .toBuffer();

  return {
    buffer,
    width: layout.width,
    height: layout.height,
  };
}

export async function resolveScene(sentence) {
  const steps = await resolveSteps(sentence);
  return steps.map((step, index) => ({
    order: index + 1,
    term: step.term,
    lemma: step.lemma,
    label: step.label,
    pictogram_id: step.pictogramId,
    has_image: step.pictogramId != null,
  }));
}

export async function generateScene(sentence) {
  const steps = await buildSteps(sentence);
  const { buffer, width, height } = await compose(steps, sentence);
  const scene = `data:image/jpeg;base64,${buffer.toString('base64')}`;

  if (scene.length > MAX_SCENE_CHARS) {
    throw new SceneGenerationError(413, 'generated scene is too large');
  }

  return {
    scene,
    width,
    height,
    pictograms: steps.filter((step) => step.image).length,
    steps: steps.map((step, index) => ({
      order: index + 1,
      term: step.term,
      label: step.label,
      pictogram_id: step.pictogramId,
      has_image: Boolean(step.image),
    })),
  };
}
