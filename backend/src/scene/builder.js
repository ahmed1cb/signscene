function normalize(sentence) {
  if (typeof sentence !== 'string') return '';
  return sentence.trim().replace(/\s+/g, ' ');
}

export function processSentence(sentence, config) {
  const s = normalize(sentence);
  if (!s) {
    return {
      prompt: 'A simple black line drawing, minimal sketch, bold clean outlines, isolated on a pure white background, no color, no shading, no scenery, no text.',
      negative_prompt: config?.negative_prompt || '',
      defaults: config?.defaults || {},
    };
  }

  const key = s.toLowerCase();
  const mappings = config?.mappings || {};

  if (mappings[key]) {
    return {
      prompt: mappings[key],
      negative_prompt: config?.negative_prompt || '',
      defaults: config?.defaults || {},
    };
  }

  for (const [mapKey, mapValue] of Object.entries(mappings)) {
    if (typeof mapKey !== 'string') continue;
    const aliases = mapKey
      .split(/[,;|\n]/)
      .map((a) => a.trim().toLowerCase())
      .filter(Boolean);
    if (aliases.includes(key)) {
      return {
        prompt: mapValue,
        negative_prompt: config?.negative_prompt || '',
        defaults: config?.defaults || {},
      };
    }
  }

  const template = config?.template || 'A simple black line drawing of "{sentence}", minimal sketch, bold clean outlines, isolated on a pure white background, no color, no shading, no scenery, no text.';
  const prompt = template.replace('{sentence}', s);
  return {
    prompt,
    negative_prompt: config?.negative_prompt || '',
    defaults: config?.defaults || {},
  };
}

export function buildForClient(sentence, config) {
  return processSentence(sentence, config);
}
