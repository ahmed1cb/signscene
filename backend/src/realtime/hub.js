import { randomUUID } from 'node:crypto';

import { WebSocket } from 'ws';

import { verifyToken } from '../auth/jwt.js';
import { parseClientMessage } from './protocol.js';

const CLOSE_UNAUTHORIZED = 4003;
const CLOSE_REPLACED = 4001;
const RATE_WINDOW_MS = 10_000;
const RATE_MAX_MESSAGES = 100;

function publicUser(user) {
  return {
    id: user.id,
    com_id: user.com_id,
    full_name: user.full_name,
  };
}

export class RealtimeHub {
  constructor({
    wss,
    repo,
    ringTimeoutMs = 45_000,
    authTimeoutMs = 5_000,
    heartbeatMs = 30_000,
    logger = console,
  }) {
    this._wss = wss;
    this._repo = repo;
    this._ringTimeoutMs = ringTimeoutMs;
    this._authTimeoutMs = authTimeoutMs;
    this._logger = logger;

    this._sessions = new Map();
    this._users = new Map();
    this._calls = new Map();
    this._activeCalls = new Map();

    this._wss.on('connection', (socket) => this._onConnection(socket));
    this._heartbeat = setInterval(
      () => this._checkHeartbeats(),
      heartbeatMs
    );
    this._heartbeat.unref?.();
  }

  close() {
    clearInterval(this._heartbeat);
    for (const call of this._calls.values()) {
      if (call.ringTimer) clearTimeout(call.ringTimer);
    }
    for (const session of this._sessions.values()) {
      if (session.authTimer) clearTimeout(session.authTimer);
    }
    this._calls.clear();
    this._activeCalls.clear();
    for (const socket of this._wss.clients) {
      try {
        socket.close(1001, 'server shutdown');
      } catch {
        socket.terminate();
      }
    }
  }

  _onConnection(socket) {
    const session = {
      socket,
      user: null,
      callId: null,
      isAlive: true,
      authTimer: null,
      rateCount: 0,
      rateResetAt: 0,
    };
    this._sessions.set(socket, session);

    session.authTimer = setTimeout(() => {
      if (!session.user) {
        socket.close(CLOSE_UNAUTHORIZED, 'authentication timeout');
      }
    }, this._authTimeoutMs);
    session.authTimer.unref?.();

    socket.on('pong', () => {
      session.isAlive = true;
    });
    socket.on('error', (error) => {
      this._logger.warn?.(`websocket error: ${error.message}`);
    });
    socket.on('close', () => {
      this._handleClose(session).catch((error) => {
        this._logger.error?.('websocket close error:', error);
      });
    });
    socket.on('message', (raw) => {
      this._handleRawMessage(session, raw).catch((error) => {
        this._logger.error?.('websocket message error:', error);
        this._sendError(socket, 'server_error', 'Server error');
      });
    });
  }

  async _handleRawMessage(session, raw) {
    const parsed = parseClientMessage(raw.toString());
    if (parsed.error) {
      this._sendError(session.socket, 'invalid_payload', parsed.error);
      return;
    }

    const message = parsed.data;

    if (!session.user) {
      if (message.type !== 'auth') {
        this._sendError(
          session.socket,
          'unauthorized',
          'Authenticate before sending messages'
        );
        session.socket.close(CLOSE_UNAUTHORIZED, 'not authenticated');
        return;
      }
      await this._handleAuth(session, message);
      return;
    }

    if (message.type === 'auth') {
      this._sendError(
        session.socket,
        'already_authenticated',
        'This connection is already authenticated'
      );
      return;
    }

    if (this._rateLimited(session)) {
      this._sendError(
        session.socket,
        'rate_limited',
        'Too many messages, slow down'
      );
      return;
    }

    switch (message.type) {
      case 'call.start':
        await this._handleCallStart(session, message);
        break;
      case 'call.accept':
        await this._handleCallAccept(session, message);
        break;
      case 'call.reject':
        await this._handleCallReject(session, message);
        break;
      case 'call.end':
        await this._handleCallEnd(session, message);
        break;
      case 'content.send':
        await this._handleContent(session, message);
        break;
      case 'ping':
        this._send(session.socket, { type: 'pong' });
        break;
      default:
        this._sendError(
          session.socket,
          'invalid_payload',
          'Unknown message type'
        );
    }
  }

  async _handleAuth(session, message) {
    let decoded;
    try {
      decoded = verifyToken(message.token);
    } catch {
      this._sendError(session.socket, 'unauthorized', 'Invalid or expired token');
      session.socket.close(CLOSE_UNAUTHORIZED, 'invalid token');
      return;
    }

    let user;
    try {
      user = await this._repo.findUserById(decoded.id);
    } catch (error) {
      this._logger.error?.('auth user lookup failed:', error);
      this._sendError(session.socket, 'server_error', 'Could not load user');
      session.socket.close(CLOSE_UNAUTHORIZED, 'auth failed');
      return;
    }

    if (!user) {
      this._sendError(session.socket, 'unauthorized', 'User no longer exists');
      session.socket.close(CLOSE_UNAUTHORIZED, 'unknown user');
      return;
    }

    if (session.socket.readyState !== WebSocket.OPEN) return;

    await this._replaceExistingSession(user.id, session.socket);

    clearTimeout(session.authTimer);
    session.authTimer = null;
    session.user = user;
    session.rateResetAt = Date.now() + RATE_WINDOW_MS;
    this._users.set(user.id, session.socket);

    this._send(session.socket, {
      type: 'ready',
      user: publicUser(user),
    });
  }

  async _replaceExistingSession(userId, newSocket) {
    const existingSocket = this._users.get(userId);
    if (!existingSocket || existingSocket === newSocket) return;

    const existingSession = this._sessions.get(existingSocket);
    if (existingSession?.callId) {
      const call = this._calls.get(existingSession.callId);
      if (call) {
        await this._finishCall(
          call,
          'ended',
          'session_replaced',
          'call.ended'
        );
      }
    }

    this._send(existingSocket, {
      type: 'error',
      code: 'session_replaced',
      message: 'This account connected from another device',
    });
    try {
      existingSocket.close(CLOSE_REPLACED, 'session replaced');
    } catch {
      existingSocket.terminate();
    }
  }

  async _handleCallStart(session, message) {
    const caller = session.user;
    if (this._activeCalls.has(caller.id)) {
      this._sendError(session.socket, 'user_busy', 'You are already in a call');
      return;
    }

    if (message.to === caller.com_id) {
      this._sendError(
        session.socket,
        'cannot_call_self',
        'You cannot call yourself'
      );
      return;
    }

    let target;
    try {
      target = await this._repo.findUserByComId(message.to);
    } catch (error) {
      this._logger.error?.('call target lookup failed:', error);
      this._sendError(session.socket, 'server_error', 'Could not find user');
      return;
    }

    if (!target) {
      this._sendError(
        session.socket,
        'target_not_found',
        'No user found with that com_id'
      );
      return;
    }

    if (!this._isOnline(target.id)) {
      this._sendError(session.socket, 'user_offline', 'That user is offline');
      return;
    }

    if (this._activeCalls.has(target.id)) {
      this._sendError(session.socket, 'user_busy', 'That user is busy');
      return;
    }

    const call = {
      id: randomUUID(),
      callerId: caller.id,
      calleeId: target.id,
      caller: publicUser(caller),
      callee: publicUser(target),
      state: 'ringing',
      ringTimer: null,
    };

    try {
      await this._repo.createCall({
        id: call.id,
        callerId: call.callerId,
        calleeId: call.calleeId,
      });
    } catch (error) {
      this._logger.error?.('create call failed:', error);
      this._sendError(session.socket, 'server_error', 'Could not start call');
      return;
    }

    call.ringTimer = setTimeout(() => {
      this._timeoutCall(call.id).catch((error) => {
        this._logger.error?.('call timeout error:', error);
      });
    }, this._ringTimeoutMs);
    call.ringTimer.unref?.();

    this._calls.set(call.id, call);
    this._activeCalls.set(call.callerId, call.id);
    this._activeCalls.set(call.calleeId, call.id);
    session.callId = call.id;

    const calleeSession = this._sessions.get(this._users.get(call.calleeId));
    if (calleeSession) calleeSession.callId = call.id;

    const expiresIn = Math.ceil(this._ringTimeoutMs / 1000);
    this._send(session.socket, {
      type: 'call.ringing',
      call_id: call.id,
      to: call.callee.com_id,
      expires_in: expiresIn,
    });
    this._sendToUser(call.calleeId, {
      type: 'call.incoming',
      call_id: call.id,
      from: call.caller,
      expires_in: expiresIn,
    });
  }

  async _handleCallAccept(session, message) {
    const call = this._calls.get(message.call_id);
    if (!call) {
      this._sendError(session.socket, 'call_not_found', 'Call is no longer available');
      return;
    }
    if (session.user.id !== call.calleeId) {
      this._sendError(session.socket, 'forbidden', 'Only the callee can accept');
      return;
    }
    if (call.state !== 'ringing') {
      this._sendError(session.socket, 'call_not_active', 'Call is not ringing');
      return;
    }

    let updated;
    try {
      updated = await this._repo.markCallActive(call.id);
    } catch (error) {
      this._logger.error?.('accept call failed:', error);
      this._sendError(session.socket, 'server_error', 'Could not accept call');
      return;
    }

    if (!updated) {
      this._sendError(session.socket, 'call_not_active', 'Call is no longer ringing');
      return;
    }

    call.state = 'active';
    if (call.ringTimer) {
      clearTimeout(call.ringTimer);
      call.ringTimer = null;
    }

    this._sendToUser(call.callerId, {
      type: 'call.accepted',
      call_id: call.id,
      peer: call.callee,
    });
    this._sendToUser(call.calleeId, {
      type: 'call.accepted',
      call_id: call.id,
      peer: call.caller,
    });
  }

  async _handleCallReject(session, message) {
    const call = this._calls.get(message.call_id);
    if (!call) {
      this._sendError(session.socket, 'call_not_found', 'Call is no longer available');
      return;
    }
    if (session.user.id !== call.calleeId) {
      this._sendError(session.socket, 'forbidden', 'Only the callee can reject');
      return;
    }
    if (call.state !== 'ringing') {
      this._sendError(session.socket, 'call_not_active', 'Call is not ringing');
      return;
    }

    await this._finishCall(call, 'rejected', 'rejected', 'call.rejected');
  }

  async _handleCallEnd(session, message) {
    const call = this._calls.get(message.call_id);
    if (!call) {
      this._sendError(session.socket, 'call_not_found', 'Call is no longer available');
      return;
    }
    if (
      session.user.id !== call.callerId &&
      session.user.id !== call.calleeId
    ) {
      this._sendError(session.socket, 'forbidden', 'You are not in this call');
      return;
    }

    await this._finishCall(call, 'ended', 'ended', 'call.ended');
  }

  async _handleContent(session, message) {
    const call = this._calls.get(message.call_id);
    if (!call) {
      this._sendError(session.socket, 'call_not_found', 'Call is no longer available');
      return;
    }
    if (call.state !== 'active') {
      this._sendError(session.socket, 'call_not_active', 'Call is not active');
      return;
    }

    const sender = session.user;
    if (sender.id !== call.callerId && sender.id !== call.calleeId) {
      this._sendError(session.socket, 'forbidden', 'You are not in this call');
      return;
    }

    const peerId =
      sender.id === call.callerId ? call.calleeId : call.callerId;
    if (!this._isOnline(peerId)) {
      await this._finishCall(
        call,
        'ended',
        'peer_disconnected',
        'call.ended'
      );
      return;
    }

    let stored;
    try {
      stored = await this._repo.insertMessage({
        callId: call.id,
        senderId: sender.id,
        kind: message.kind,
        content: message.content,
      });
    } catch (error) {
      this._logger.error?.('store message failed:', error);
      this._sendError(session.socket, 'server_error', 'Could not send message');
      return;
    }

    this._sendToUser(peerId, {
      type: 'content',
      call_id: call.id,
      message_id: stored?.id ?? null,
      sender: publicUser(sender),
      kind: message.kind,
      content: message.content,
      created_at: stored?.created_at ?? new Date().toISOString(),
    });
  }

  async _timeoutCall(callId) {
    const call = this._calls.get(callId);
    if (!call || call.state !== 'ringing') return;
    await this._finishCall(call, 'missed', 'timeout', 'call.ended');
  }

  async _finishCall(call, state, reason, eventType) {
    if (call.done) return;
    call.done = true;

    if (call.ringTimer) {
      clearTimeout(call.ringTimer);
      call.ringTimer = null;
    }

    this._calls.delete(call.id);
    if (this._activeCalls.get(call.callerId) === call.id) {
      this._activeCalls.delete(call.callerId);
    }
    if (this._activeCalls.get(call.calleeId) === call.id) {
      this._activeCalls.delete(call.calleeId);
    }

    const callerSession = this._sessions.get(this._users.get(call.callerId));
    if (callerSession?.callId === call.id) callerSession.callId = null;
    const calleeSession = this._sessions.get(this._users.get(call.calleeId));
    if (calleeSession?.callId === call.id) calleeSession.callId = null;

    try {
      await this._repo.markCallEnded(call.id, state, reason);
    } catch (error) {
      this._logger.error?.('end call persistence failed:', error);
    }

    const payload = {
      type: eventType,
      call_id: call.id,
      reason,
    };
    this._sendToUser(call.callerId, payload);
    this._sendToUser(call.calleeId, payload);
  }

  async _handleClose(session) {
    if (session.authTimer) {
      clearTimeout(session.authTimer);
      session.authTimer = null;
    }
    this._sessions.delete(session.socket);

    if (!session.user) return;

    if (this._users.get(session.user.id) === session.socket) {
      this._users.delete(session.user.id);
    }

    if (session.callId) {
      const call = this._calls.get(session.callId);
      if (call) {
        await this._finishCall(
          call,
          'ended',
          'peer_disconnected',
          'call.ended'
        );
      }
      session.callId = null;
    }
  }

  _checkHeartbeats() {
    for (const socket of this._wss.clients) {
      const session = this._sessions.get(socket);
      if (!session) continue;
      if (!session.isAlive) {
        socket.terminate();
        continue;
      }
      session.isAlive = false;
      try {
        socket.ping();
      } catch {
        socket.terminate();
      }
    }
  }

  _rateLimited(session) {
    const now = Date.now();
    if (now >= session.rateResetAt) {
      session.rateCount = 0;
      session.rateResetAt = now + RATE_WINDOW_MS;
    }
    session.rateCount += 1;
    return session.rateCount > RATE_MAX_MESSAGES;
  }

  _isOnline(userId) {
    const socket = this._users.get(userId);
    return socket && socket.readyState === WebSocket.OPEN ? socket : null;
  }

  _send(socket, payload) {
    if (socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify(payload));
  }

  _sendToUser(userId, payload) {
    const socket = this._isOnline(userId);
    if (socket) this._send(socket, payload);
  }

  _sendError(socket, code, message) {
    this._send(socket, {
      type: 'error',
      code,
      message,
    });
  }
}
