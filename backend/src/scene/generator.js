import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import sharp from 'sharp';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SEARCH_URL = 'https://api.arasaac.org/v1/pictograms/{lang}/bestsearch/{term}';
const IMAGE_URL = 'https://static.arasaac.org/pictograms/{pid}/{pid}_500.png';

const LANG =
  process.env.ARASAAC_LANG || process.env.SIGNSCENE_ARASAAC_LANG || 'en';
const MAX_PICTOS = 6;
const REQUEST_TIMEOUT_MS = 10_000;
const MAX_SCENE_CHARS = 3_000_000;
const CACHE_DIR = process.env.ARASAAC_CACHE_DIR
  ? path.resolve(process.env.ARASAAC_CACHE_DIR)
  : path.resolve(__dirname, '../../data/arasaac');

const STOPWORDS = new Set([
  'a',
  'an',
  'the',
  'is',
  'are',
  'am',
  'be',
  'to',
  'of',
  'and',
  'or',
  'it',
  'this',
  'that',
  'in',
  'on',
  'at',
  'for',
  'with',
]);

const idCache = new Map();

export class SceneGenerationError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'SceneGenerationError';
    this.status = status;
  }
}

function words(sentence) {
  const seen = new Set();
  const out = [];
  const matches = String(sentence).toLowerCase().match(/[\p{L}]+/gu) || [];
  for (const word of matches) {
    if (STOPWORDS.has(word) || seen.has(word)) continue;
    seen.add(word);
    out.push(word);
  }
  return out;
}

async function httpGet(url) {
  let response;
  try {
    response = await fetch(url, {
      headers: { 'User-Agent': 'signscene/1.0' },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    throw new SceneGenerationError(502, `ARASAAC request failed: ${error.message}`);
  }

  if (!response.ok) {
    const error = new SceneGenerationError(
      502,
      `ARASAAC request failed with status ${response.status}`
    );
    error.upstreamStatus = response.status;
    throw error;
  }

  return Buffer.from(await response.arrayBuffer());
}

async function searchId(term) {
  if (idCache.has(term)) return idCache.get(term);

  const url = SEARCH_URL.replace('{lang}', encodeURIComponent(LANG)).replace(
    '{term}',
    encodeURIComponent(term)
  );

  let pid = null;
  try {
    const data = JSON.parse((await httpGet(url)).toString('utf8'));
    if (Array.isArray(data) && data.length && data[0]._id != null) {
      const value = Number(data[0]._id);
      pid = Number.isFinite(value) ? value : null;
    }
  } catch (error) {
    if (error.upstreamStatus !== 404) throw error;
  }

  idCache.set(term, pid);
  return pid;
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

async function compose(images) {
  const count = images.length;
  const cols = Math.min(count, 3);
  const rows = Math.ceil(count / cols);
  const tile = count === 1 ? 512 : 256;
  const width = cols * tile;
  const height = rows * tile;

  const composites = [];
  for (let index = 0; index < count; index += 1) {
    const input = await sharp(images[index])
      .resize(tile, tile, {
        fit: 'contain',
        background: { r: 255, g: 255, b: 255, alpha: 1 },
      })
      .png()
      .toBuffer();
    composites.push({
      input,
      left: (index % cols) * tile,
      top: Math.floor(index / cols) * tile,
    });
  }

  const buffer = await sharp({
    create: {
      width,
      height,
      channels: 3,
      background: { r: 255, g: 255, b: 255 },
    },
  })
    .composite(composites)
    .jpeg({ quality: 88 })
    .toBuffer();

  return { buffer, width, height };
}

export async function generateScene(sentence) {
  const terms = words(sentence);
  if (!terms.length) {
    throw new SceneGenerationError(422, 'sentence has no usable words');
  }

  const images = [];
  for (const term of terms) {
    const pid = await searchId(term);
    if (pid == null) continue;

    const image = await fetchImage(pid);
    if (image) images.push(image);
    if (images.length >= MAX_PICTOS) break;
  }

  if (!images.length) {
    throw new SceneGenerationError(422, 'no pictograms found for this sentence');
  }

  const { buffer, width, height } = await compose(images);
  const scene = `data:image/jpeg;base64,${buffer.toString('base64')}`;

  if (scene.length > MAX_SCENE_CHARS) {
    throw new SceneGenerationError(413, 'generated scene is too large');
  }

  return {
    scene,
    width,
    height,
    pictograms: images.length,
  };
}
