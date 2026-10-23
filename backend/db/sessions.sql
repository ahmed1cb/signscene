USE signscene;

CREATE TABLE IF NOT EXISTS calls (
  id           CHAR(36) PRIMARY KEY,
  caller_id    BIGINT UNSIGNED NOT NULL,
  callee_id    BIGINT UNSIGNED NOT NULL,
  state        ENUM('ringing','active','ended','rejected','missed')
               NOT NULL DEFAULT 'ringing',
  started_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  answered_at  DATETIME(3) NULL,
  ended_at     DATETIME(3) NULL,
  end_reason   VARCHAR(40) NULL,
  CONSTRAINT fk_calls_caller
    FOREIGN KEY (caller_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_calls_callee
    FOREIGN KEY (callee_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_calls_state (state),
  INDEX idx_calls_caller (caller_id),
  INDEX idx_calls_callee (callee_id)
);

CREATE TABLE IF NOT EXISTS call_messages (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  call_id     CHAR(36) NOT NULL,
  sender_id   BIGINT UNSIGNED NOT NULL,
  kind        ENUM('text','scene') NOT NULL,
  payload     MEDIUMTEXT NOT NULL,
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  CONSTRAINT fk_messages_call
    FOREIGN KEY (call_id) REFERENCES calls(id) ON DELETE CASCADE,
  CONSTRAINT fk_messages_sender
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_messages_call (call_id, id),
  INDEX idx_messages_sender (sender_id)
);
