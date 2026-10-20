import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import rateLimit from 'express-rate-limit';
import authRoutes from './routes/auth.routes.js';
import { pingDb } from './config/db.js';

dotenv.config();

const app = express();
app.set('trust proxy', 1);

app.use(helmet());
app.use(
  cors({
    origin: (process.env.CORS_ORIGIN || '*').split(',').map((s) => s.trim()),
    credentials: true,
  })
);
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 60,
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(globalLimiter);
// made this to check if the servers works

app.get('/healthz', (req, res) => res.json({ ok: true }));

// made this to check if the database is connected
app.get('/db/health', async (req, res) => {
  try {
    await pingDb();
    res.json({ db: 'ok' });
  } catch (e) {
    res.status(500).json({ db: 'fail', error: e.message });
  }
});

app.use('/auth', authRoutes);

app.use((req, res) => res.status(404).json({ error: 'not found' }));

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'server error' });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  console.log(`SignScene backend listening on :${PORT}`);
});
