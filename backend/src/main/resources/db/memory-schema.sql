-- Memory-owned tables only. User/Moment foreign keys are added after their schema exists.
CREATE TABLE IF NOT EXISTS reon_memory (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    engine_memory_id VARCHAR(64) NOT NULL,
    period_month VARCHAR(7) NOT NULL,
    pattern_type VARCHAR(16) NOT NULL,
    title VARCHAR(512) NOT NULL,
    description TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    moment_count INT NOT NULL,
    contexts_json TEXT NOT NULL,
    tracks_json TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    active BOOLEAN NOT NULL,
    history_revision BIGINT NOT NULL,
    read_at DATETIME(6),
    version BIGINT NOT NULL,
    CONSTRAINT uk_memory_engine UNIQUE (engine_memory_id),
    INDEX idx_memory_owner_active (user_id, active, end_date)
);
CREATE TABLE IF NOT EXISTS reon_memory_moment (
    memory_id BIGINT NOT NULL,
    sort_index INT NOT NULL,
    moment_id BIGINT NOT NULL,
    recorded_at DATETIME(6) NOT NULL,
    song_title VARCHAR(255) NOT NULL,
    artist VARCHAR(255),
    memo VARCHAR(2000),
    PRIMARY KEY (memory_id, sort_index),
    CONSTRAINT fk_memory_moment FOREIGN KEY (memory_id) REFERENCES reon_memory(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS memory_history_revision (
    user_id BIGINT PRIMARY KEY,
    revision BIGINT NOT NULL,
    pending_months VARCHAR(2048) NOT NULL
);
