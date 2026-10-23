import { getPool } from '../config/db.js';

const USER_FIELDS = 'id, full_name, com_id';

export async function findUserByComId(comId) {
  const [rows] = await getPool().execute(
    `SELECT ${USER_FIELDS} FROM users WHERE com_id = ?`,
    [comId]
  );
  return rows[0] || null;
}

export async function findUserById(userId) {
  const [rows] = await getPool().execute(
    `SELECT ${USER_FIELDS} FROM users WHERE id = ?`,
    [userId]
  );
  return rows[0] || null;
}

export async function createCall({ id, callerId, calleeId }) {
  await getPool().execute(
    `INSERT INTO calls (id, caller_id, callee_id, state, started_at)
     VALUES (?, ?, ?, 'ringing', NOW(3))`,
    [id, callerId, calleeId]
  );
}

export async function markCallActive(callId) {
  const [result] = await getPool().execute(
    `UPDATE calls
     SET state = 'active', answered_at = NOW(3)
     WHERE id = ? AND state = 'ringing'`,
    [callId]
  );
  return result.affectedRows > 0;
}

export async function markCallEnded(callId, state, reason) {
  await getPool().execute(
    `UPDATE calls
     SET state = ?, ended_at = NOW(3), end_reason = ?
     WHERE id = ? AND state IN ('ringing', 'active')`,
    [state, reason, callId]
  );
}

export async function insertMessage({ callId, senderId, kind, content }) {
  const pool = getPool();
  const [result] = await pool.execute(
    `INSERT INTO call_messages (call_id, sender_id, kind, payload)
     VALUES (?, ?, ?, ?)`,
    [callId, senderId, kind, content]
  );
  const [rows] = await pool.execute(
    `SELECT id, created_at FROM call_messages WHERE id = ?`,
    [result.insertId]
  );
  return rows[0];
}
