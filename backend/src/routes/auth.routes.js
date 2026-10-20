import { Router } from 'express';
import { getPool } from '../config/db.js';
import { hashPassword, comparePassword } from '../auth/password.js';
import { registerSchema, loginSchema } from '../auth/validators.js';
import {signToken} from '../auth/jwt.js'
import rateLimit from 'express-rate-limit';
import { requireAuth } from '../middleware/auth.js';

const router = Router();

const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
});

router.post('/register', authLimiter, async (req, res) => {
  const { error, value } = registerSchema.validate(req.body);
  if (error) {
    return res.status(400).json({ success: false, error: error.message });
  }

  const { full_name, com_id, password, preferred } = value;
  const pool = getPool();
  const conn = await pool.getConnection();

  try {
    const [existing] = await conn.execute('SELECT id FROM users WHERE com_id = ?', [com_id]);
    if (existing.length) {
      return res.status(409).json({ success: false, error: 'com_id already exists' });
    }

    const password_hash = await hashPassword(password);
    const prefStr = Array.isArray(preferred) ? preferred.join(',') : String(preferred);

    const [result] = await conn.execute(
      'INSERT INTO users (full_name, com_id, password_hash, preferred_content) VALUES (?, ?, ?, ?)',
      [full_name, com_id, password_hash, prefStr]
    );

    const userId = result.insertId;
    res.status(201).json({
      success: true,
      user: {
        id: userId,
        full_name,
        com_id,
        preferred: preferred || prefStr.split(','),
      },
    });
  } catch (err) {
    console.error('register error:', err);
    res.status(500).json({ success: false, error: 'server error' });
  } finally {
    conn.release();
  }
});

router.post('/login', authLimiter, async (req, res) => {
  const { error, value } = loginSchema.validate(req.body);
  if (error) {
    return res.status(400).json({ success: false, error: error.message });
  }

  const { com_id, password } = value;
  const pool = getPool();
  try {
    const [rows] = await pool.execute(
      'SELECT id, full_name, com_id, password_hash, preferred_content FROM users WHERE com_id = ?',
      [com_id]
    );

    if (rows.length === 0) {
      return res.status(401).json({ success: false, error: 'invalid credentials' });
    }

    const user = rows[0];
    const ok = await comparePassword(password, user.password_hash);
    if (!ok) {
      return res.status(401).json({ success: false, error: 'invalid credentials' });
    }

    const token = signToken({ id: user.id, com_id: user.com_id, full_name: user.full_name });
    res.json({
      success: true,
      token,
      user: {
        id: user.id,
        full_name: user.full_name,
        com_id: user.com_id,
        preferred: user.preferred_content ? user.preferred_content.split(',') : ['text'],
      },
    });
  } catch (err) {
    console.error('login error:', err);
    res.status(500).json({ success: false, error: 'server error' });
  }
});


router.get('/me', requireAuth, async (req, res) => {
  try {
    const [rows] = await getPool().execute(
      'SELECT id, full_name, com_id, preferred_content FROM users WHERE id = ?',
      [req.user.id]
    );
    if (!rows.length) return res.status(401).json({ success: false, error: 'invalid token' });
    const u = rows[0];
    res.json({ success: true, user: { id: u.id, full_name: u.full_name, com_id: u.com_id, preferred: u.preferred_content ? u.preferred_content.split(',') : ['text'] } });
  } catch (err) {
    res.status(500).json({ success: false, error: 'server error' });
  }
});

export default router;
