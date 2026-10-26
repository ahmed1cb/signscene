import { z } from 'zod';

export const registerSchema = z.object({
  full_name: z.string().trim().min(2).max(100),
  com_id: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^[A-Z][A-Z0-9]{1,10}-\d{4}$/, 'com_id must be like NAME-1234'),
  password: z.string().min(6).max(128),
});

export const loginSchema = z.object({
  com_id: z.string().trim().toUpperCase(),
  password: z.string().min(1),
});
