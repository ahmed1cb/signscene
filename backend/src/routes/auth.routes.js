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
  const parsed = registerSchema.safeParse(req.body || {});
  if (!parsed.success) {
    return res.status(400).json({
      success: false,
      error: parsed.error.issues[0]?.message || 'invalid request',
    });
  }

  const { full_name, com_id, password } = parsed.data;
  const pool = getPool();
  let conn;

  try {
    conn = await pool.getConnection();
    const [existing] = await conn.execute('SELECT id FROM users WHERE com_id = ?', [com_id]);
    if (existing.length) {
      return res.status(409).json({ success: false, error: 'com_id already exists' });
    }

    const password_hash = await hashPassword(password);

    const [result] = await conn.execute(
      'INSERT INTO users (full_name, com_id, password_hash) VALUES (?, ?, ?)',
      [full_name, com_id, password_hash]
    );

    const userId = result.insertId;
    res.status(201).json({
      success: true,
      user: {
        id: userId,
        full_name,
        com_id,
      },
    });
  } catch (err) {
    console.error('register error:', err);
    res.status(500).json({ success: false, error: 'server error' });
  } finally {
    if (conn) conn.release();
  }
});

router.post('/login', authLimiter, async (req, res) => {
  const parsed = loginSchema.safeParse(req.body || {});
  if (!parsed.success) {
    return res.status(400).json({
      success: false,
      error: parsed.error.issues[0]?.message || 'invalid request',
    });
  }

  const { com_id, password } = parsed.data;
  const pool = getPool();
  try {
    const [rows] = await pool.execute(
      'SELECT id, full_name, com_id, password_hash FROM users WHERE com_id = ?',
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
      'SELECT id, full_name, com_id FROM users WHERE id = ?',
      [req.user.id]
    );
    if (!rows.length) return res.status(401).json({ success: false, error: 'invalid token' });
    const u = rows[0];
    res.json({ success: true, user: { id: u.id, full_name: u.full_name, com_id: u.com_id } });
  } catch (err) {
    res.status(500).json({ success: false, error: 'server error' });
  }
});

export default router;
