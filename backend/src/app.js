import http from 'node:http';

import cors from 'cors';
import dotenv from 'dotenv';
import express from 'express';
import rateLimit from 'express-rate-limit';
import helmet from 'helmet';
import { WebSocketServer } from 'ws';

import authRoutes from './routes/auth.routes.js';
import sceneRoutes from './routes/scene.routes.js';
import { pingDb } from './config/db.js';
import { RealtimeHub } from './realtime/hub.js';
import * as realtimeRepository from './realtime/repository.js';

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
app.use('/scene', sceneRoutes);

app.use((req, res) => res.status(404).json({ error: 'not found' }));

// Public Errors Handler
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'server error' });
});

const PORT = process.env.PORT || 8080;
const server = http.createServer(app);
const wss = new WebSocketServer({
  server,
  path: process.env.WS_PATH || '/ws',
  maxPayload: parseInt(process.env.WS_MAX_PAYLOAD_BYTES || '3145728', 10),
});

const hub = new RealtimeHub({
  wss,
  repo: realtimeRepository,
  ringTimeoutMs: parseInt(process.env.CALL_RING_TIMEOUT_MS || '45000', 10),
});

server.listen(PORT, () => {
  console.log(`SignScene backend listening on :${PORT}`);
});

function shutdown() {
  hub.close();
  wss.close();
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 3000).unref();
}

process.once('SIGINT', shutdown);
process.once('SIGTERM', shutdown);
