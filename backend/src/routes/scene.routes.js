import { Router } from 'express';
import { getConfig, reloadConfig } from '../scene/loader.js';
import { processSentence } from '../scene/builder.js';

const router = Router();

router.get('/config', (req, res) => {
  try {
    const config = getConfig();
    res.json({ success: true, config });
  } catch (err) {
    console.error('scene config error:', err);
    res.status(500).json({ success: false, error: 'server error' });
  }
});

router.post('/process', (req, res) => {
  try {
    const { sentence } = req.body || {};
    if (typeof sentence !== 'string' || !sentence.trim()) {
      return res.status(400).json({ success: false, error: 'sentence required' });
    }
    const config = getConfig();
    const result = processSentence(sentence, config);
    res.json({ success: true, ...result });
  } catch (err) {
    console.error('scene process error:', err);
    res.status(500).json({ success: false, error: 'server error' });
  }

});

router.post('/reload', (req, res) => {
  try {
    const config = reloadConfig();
    res.json({ success: true, config });
  } catch (err) {
    console.error('scene reload error:', err);
    res.status(500).json({ success: false, error: 'server error' });
  }
});

export default router;
