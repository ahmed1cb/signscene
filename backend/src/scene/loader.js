import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DATA_PATH = path.resolve(__dirname, '../../data/scene_prompts.json');

let cached = null;
let cachedMtime = 0;

export function getConfig() {
  try {
    const stat = fs.statSync(DATA_PATH);
    if (!cached || stat.mtimeMs !== cachedMtime) {
      const raw = fs.readFileSync(DATA_PATH, 'utf8');
      cached = JSON.parse(raw);
      cachedMtime = stat.mtimeMs;
    }
    return cached;
  } catch (err) {
    if (cached) return cached;
    throw err;
  }
}

export function reloadConfig() {
  cached = null;
  cachedMtime = 0;
  return getConfig();
}
