-- Seed data for CWB (MySQL)
-- All demo users have password: 123456

USE cwb;

INSERT INTO users (full_name, com_id, password_hash) VALUES
  ('Alice Hassan',  'ALICE-4821', '$2b$10$7WymsNmPAe0z9PW7Q24Qq.cmihMxR6cdnLn9Xt80q18kJOs2HYBHC'),
  ('John Smith',    'JOHN-7290',  '$2b$10$7WymsNmPAe0z9PW7Q24Qq.cmihMxR6cdnLn9Xt80q18kJOs2HYBHC'),
  ('Sara Ahmed',    'SARA-1155',  '$2b$10$7WymsNmPAe0z9PW7Q24Qq.cmihMxR6cdnLn9Xt80q18kJOs2HYBHC'),
  ('Omar Khaled',   'OMAR-9034',  '$2b$10$7WymsNmPAe0z9PW7Q24Qq.cmihMxR6cdnLn9Xt80q18kJOs2HYBHC')
ON DUPLICATE KEY UPDATE
  full_name = VALUES(full_name),
  password_hash = VALUES(password_hash);
