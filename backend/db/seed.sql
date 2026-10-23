-- Seed data for signscene (MySQL)
-- All demo users have password: 123456 (bcrypt hash shared below)

USE signscene;

INSERT INTO users (full_name, com_id, password_hash) VALUES
  ('Alice Hassan',  'ALICE-4821', '$2y$10$174E9Lj90D9TZqabnct3hOmdopcqLKDfBNrNNw8zJEtdwziyi9aYe'),
  ('John Smith',    'JOHN-7290',  '$2y$10$174E9Lj90D9TZqabnct3hOmdopcqLKDfBNrNNw8zJEtdwziyi9aYe'),
  ('Sara Ahmed',    'SARA-1155',  '$2y$10$174E9Lj90D9TZqabnct3hOmdopcqLKDfBNrNNw8zJEtdwziyi9aYe'),
  ('Omar Khaled',   'OMAR-9034',  '$2y$10$174E9Lj90D9TZqabnct3hOmdopcqLKDfBNrNNw8zJEtdwziyi9aYe');
