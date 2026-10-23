import Joi from 'joi';

export const registerSchema = Joi.object({
  full_name: Joi.string().trim().min(2).max(100).required(),
  com_id: Joi.string()
    .trim()
    .uppercase()
    .pattern(/^[A-Z][A-Z0-9]{1,10}-\d{4}$/)
    .required()
    .messages({
      'string.pattern.base': 'com_id must be like NAME-1234',
    }),
  password: Joi.string().min(6).max(128).required(),
});

export const loginSchema = Joi.object({
  com_id: Joi.string().trim().uppercase().required(),
  password: Joi.string().min(1).required(),
});
