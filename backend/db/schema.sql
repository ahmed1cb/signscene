CREATE DATABASE IF NOT EXISTS signscene
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE signscene_users;

CREATE TABLE IF NOT EXISTS users (
  id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  full_name        VARCHAR(100) NOT NULL,
  com_id           VARCHAR(16) NOT NULL UNIQUE,
  password_hash    CHAR(60) NOT NULL,
  preferred_content SET('text','audio','scene') NOT NULL DEFAULT 'text,audio,scene',
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS signs (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  term        VARCHAR(60) NOT NULL,
  category    VARCHAR(40) NOT NULL,
  description TEXT NULL,
  image_path  VARCHAR(255) NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_term (term, category)
);
