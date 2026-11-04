import assert from 'node:assert/strict';

import { analyzeSentence } from '../src/scene/language.js';
import { resolveScene } from '../src/scene/generator.js';

function step(steps, term) {
  const matches = steps.filter((item) => item.term === term);
  assert.ok(matches.length, `missing step for "${term}"`);
  return matches[matches.length - 1];
}

function expectAny(actual, expected, label) {
  assert.ok(
    expected.has(actual),
    `${label}: expected one of ${[...expected].join(', ')}, got ${actual}`
  );
}

const analysis = analyzeSentence('She is drinking milk');
assert.deepEqual(
  analysis.map(({ term, lemma, pos }) => ({ term, lemma, pos })),
  [
    { term: 'she', lemma: 'she', pos: 'noun' },
    { term: 'drinking', lemma: 'drink', pos: 'verb' },
    { term: 'milk', lemma: 'milk', pos: 'noun' },
  ]
);

const water = await resolveScene('I want water');
expectAny(
  step(water, 'water').pictogram_id,
  new Set([2248, 6889, 32464]),
  'water noun'
);

const watering = await resolveScene('I water the plants');
expectAny(
  step(watering, 'water').pictogram_id,
  new Set([2816, 22082, 24354, 24355, 34173]),
  'water verb'
);
assert.equal(step(watering, 'plants').pictogram_id, 3143);

const drinking = await resolveScene('She is drinking milk');
expectAny(
  step(drinking, 'drinking').pictogram_id,
  new Set([2276, 6061, 29716, 37528]),
  'drink verb'
);
assert.equal(step(drinking, 'milk').pictogram_id, 2445);

const playing = await resolveScene('The boy is playing with a red ball');
assert.equal(step(playing, 'playing').lemma, 'play');
assert.ok(step(playing, 'playing').pictogram_id != null);
assert.equal(step(playing, 'red').pictogram_id, 2808);
expectAny(
  step(playing, 'ball').pictogram_id,
  new Set([2269, 3241]),
  'ball noun'
);

const light = await resolveScene('The light is on');
assert.equal(step(light, 'light').pictogram_id, 8619);

const flyingBat = await resolveScene('A bat is flying');
assert.equal(step(flyingBat, 'bat').pictogram_id, 2903);
assert.equal(step(flyingBat, 'flying').pictogram_id, 6246);

const hitBat = await resolveScene('I hit the ball with a bat');
assert.equal(step(hitBat, 'bat').pictogram_id, 8501);

const hotFood = await resolveScene('The hot food is ready');
assert.equal(step(hotFood, 'hot').pictogram_id, 4583);

expectAny(
  step(await resolveScene('one'), 'one').pictogram_id,
  new Set([7291, 35677]),
  'number one hand'
);
expectAny(
  step(await resolveScene('five'), 'five').pictogram_id,
  new Set([6979, 35631]),
  'number five hand'
);
assert.equal(step(await resolveScene('17'), '17').pictogram_id, 29272);
assert.equal(step(await resolveScene('24'), '24').pictogram_id, 29286);

console.log('scene regression checks passed');
