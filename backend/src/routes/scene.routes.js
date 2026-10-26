import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { z } from 'zod';

import { requireAuth } from '../middleware/auth.js';
import { generateScene, SceneGenerationError } from '../scene/generator.js';

const router = Router();

const generateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
});

const generateSchema = z.object({
  sentence: z.string().trim().min(1).max(500),
});

router.post('/generate', requireAuth, generateLimiter, async (req, res) => {
  const parsed = generateSchema.safeParse(req.body || {});
  if (!parsed.success) {
    return res.status(400).json({
      success: false,
      error: parsed.error.issues[0]?.message || 'invalid request',
    });
  }

  try {
    const result = await generateScene(parsed.data.sentence);
    res.json({ success: true, sentence: parsed.data.sentence, ...result });
  } catch (err) {
    const known = err instanceof SceneGenerationError;
    if (!known) console.error('scene generate error:', err);
    res.status(known ? err.status : 502).json({
      success: false,
      error: known ? err.message : 'could not generate scene',
    });
  }
});

export default router;
