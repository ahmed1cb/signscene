import { z } from 'zod';

const comId = z
  .string()
  .trim()
  .toUpperCase()
  .regex(/^[A-Z][A-Z0-9]{1,10}-\d{4}$/, 'com_id must be like NAME-1234');

export const authSchema = z.object({
  type: z.literal('auth'),
  token: z.string().min(10),
});

export const callStartSchema = z.object({
  type: z.literal('call.start'),
  to: comId,
});

const callAction = (type) =>
  z.object({
    type: z.literal(type),
    call_id: z.string().uuid(),
  });

export const callAcceptSchema = callAction('call.accept');
export const callRejectSchema = callAction('call.reject');
export const callEndSchema = callAction('call.end');

export const contentSendSchema = z.object({
  type: z.literal('content.send'),
  call_id: z.string().uuid(),
  kind: z.enum(['text', 'scene']),
  content: z.string().min(1).max(3_000_000),
});

export const pingSchema = z.object({
  type: z.literal('ping'),
});

export const clientMessageSchema = z.discriminatedUnion('type', [
  authSchema,
  callStartSchema,
  callAcceptSchema,
  callRejectSchema,
  callEndSchema,
  contentSendSchema,
  pingSchema,
]);

export function parseClientMessage(raw) {
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return { error: 'invalid json' };
  }

  const parsed = clientMessageSchema.safeParse(data);
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message || 'invalid payload' };
  }
  if (
    parsed.data.type === 'content.send' &&
    parsed.data.kind === 'text' &&
    parsed.data.content.length > 4000
  ) {
    return { error: 'text content is too long' };
  }
  return { data: parsed.data };
}
