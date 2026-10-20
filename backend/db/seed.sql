-- Seed data for signscene_users (MySQL)
-- All demo users have password: 123456 (bcrypt hash shared below)

USE signscene;

INSERT INTO users (full_name, com_id, password_hash, preferred_content) VALUES
  ('Alice Hassan',  'ALICE-4821', '$2y$10$174E9Lj90D9TZqabnct3hOmdopcqLKDfBNrNNw8zJEtdwziyi9aYe', 'text,audio,scene'),
  ('John Smith',    'JOHN-7290',  '$2y$10$174E9Lj90D9TZqabnct3hOmdopcqLKDfBNrNNw8zJEtdwziyi9aYe', 'text,audio'),
  ('Sara Ahmed',    'SARA-1155',  '$2y$10$174E9Lj90D9TZqabnct3hOmdopcqLKDfBNrNNw8zJEtdwziyi9aYe', 'text,scene'),
  ('Omar Khaled',   'OMAR-9034',  '$2y$10$174E9Lj90D9TZqabnct3hOmdopcqLKDfBNrNNw8zJEtdwziyi9aYe', 'text');

INSERT INTO signs (term, category, description, image_path) VALUES
  ('hello',     'greetings',  'Open palm facing out, small side-to-side wave.',                 'assets/scenes/hello.png'),
  ('yes',       'basic',      'Fist nodding up and down at the wrist.',                          'assets/scenes/yes.png'),
  ('no',        'basic',      'Index and middle finger tap the thumb, twice.',                   'assets/scenes/no.png'),
  ('help',      'emergency',  'Fist resting on flat palm, lift both hands together.',            'assets/scenes/help.png'),
  ('thanks',    'greetings',  'Flat palm from chin moves outward and down.',                     'assets/scenes/thanks.png'),
  ('please',    'basic',      'Flat palm circles on the chest.',                                 'assets/scenes/please.png'),
  ('water',     'daily',      'Tapping a closed hand twice against the chin.',                   'assets/scenes/water.png'),
  ('emergency', 'emergency',  'Open hand taps chest repeatedly, urgent expression.',             'assets/scenes/emergency.png'),
  ('family',    'daily',      'Both hands make a circle, thumbs joined, then separate outward.', 'assets/scenes/family.png'),
  ('love',      'feelings',   'Cross both fists over the chest.',                                'assets/scenes/love.png');
