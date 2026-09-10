-- Full Schema for Moments PostgreSQL Database
-- Idempotent DDL

-- 1. rsa_keys
CREATE TABLE IF NOT EXISTS rsa_keys (
    id SERIAL PRIMARY KEY,
    public_key_pem TEXT NOT NULL,
    private_key_pem TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- 2. system_status
CREATE TABLE IF NOT EXISTS system_status (
    id SERIAL PRIMARY KEY,
    initialized BOOLEAN NOT NULL DEFAULT FALSE,
    admin_user_id INTEGER NULL,
    llm_base_url VARCHAR(500) NOT NULL DEFAULT 'https://api.openai.com/v1',
    llm_api_key VARCHAR(500) NOT NULL DEFAULT '',
    llm_model VARCHAR(100) NOT NULL DEFAULT 'gpt-4o-mini',
    llm_timeout INTEGER NOT NULL DEFAULT 30,
    llm_max_tokens INTEGER NOT NULL DEFAULT 300,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- 3. users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(100) NOT NULL,
    signature VARCHAR(500) NULL,
    avatar_path VARCHAR(500) NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CONSTRAINT ck_users_role CHECK (role IN ('admin', 'user', 'bot')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CONSTRAINT ck_users_status CHECK (status IN ('active', 'deactivated', 'disabled')),
    can_invite BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP WITHOUT TIME ZONE NULL,
    last_login_at TIMESTAMP WITHOUT TIME ZONE NULL,
    token_version INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_status ON users (status);

-- 4. file_metadata
CREATE TABLE IF NOT EXISTS file_metadata (
    id SERIAL PRIMARY KEY,
    storage_path VARCHAR(500) NOT NULL UNIQUE,
    original_name VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    size INTEGER NOT NULL,
    mime VARCHAR(100) NOT NULL,
    format VARCHAR(20) NOT NULL,
    kind VARCHAR(20) NOT NULL CONSTRAINT ck_file_metadata_kind CHECK (kind IN ('image', 'video', 'avatar', 'thumb', 'large')),
    owner_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- 5. friendships
CREATE TABLE IF NOT EXISTS friendships (
    id SERIAL PRIMARY KEY,
    user_a_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_b_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CONSTRAINT ck_friendships_status CHECK (status IN ('pending', 'accepted')),
    requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMP WITHOUT TIME ZONE NULL,
    CONSTRAINT ck_friendships_user_order CHECK (user_a_id < user_b_id),
    CONSTRAINT uq_friendships_users UNIQUE (user_a_id, user_b_id)
);

-- 6. invite_codes
CREATE TABLE IF NOT EXISTS invite_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CONSTRAINT ck_invite_codes_status CHECK (status IN ('active', 'used', 'expired', 'revoked')),
    expires_at TIMESTAMP WITHOUT TIME ZONE NULL,
    used_by_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_invite_codes_creator_id ON invite_codes (creator_id);
CREATE INDEX IF NOT EXISTS ix_invite_codes_status ON invite_codes (status);

-- 7. likes
CREATE TABLE IF NOT EXISTS likes (
    id SERIAL PRIMARY KEY,
    target_type VARCHAR(20) NOT NULL CONSTRAINT ck_likes_target_type CHECK (target_type IN ('post', 'comment')),
    target_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_likes_target_user UNIQUE (target_type, target_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_likes_target ON likes (target_type, target_id);

-- 8. posts
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    visibility VARCHAR(20) NOT NULL DEFAULT 'public' CONSTRAINT ck_posts_visibility CHECK (visibility IN ('public', 'friends')),
    deleted_at TIMESTAMP WITHOUT TIME ZONE NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_posts_created_at ON posts (created_at);
CREATE INDEX IF NOT EXISTS ix_posts_deleted_at ON posts (deleted_at);
CREATE INDEX IF NOT EXISTS ix_posts_user_id ON posts (user_id);
CREATE INDEX IF NOT EXISTS ix_posts_feed_cursor ON posts (created_at, id);

-- 9. comments
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_comment_id INTEGER NULL REFERENCES comments(id) ON DELETE CASCADE,
    reply_to_user_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
    content TEXT NULL,
    image_path VARCHAR(500) NULL,
    image_thumb_path VARCHAR(500) NULL,
    image_large_path VARCHAR(500) NULL,
    deleted_at TIMESTAMP WITHOUT TIME ZONE NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_comments_created_at ON comments (created_at);
CREATE INDEX IF NOT EXISTS ix_comments_post_id ON comments (post_id);

-- 10. post_media
CREATE TABLE IF NOT EXISTS post_media (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NULL REFERENCES posts(id) ON DELETE CASCADE,
    owner_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
    file_path VARCHAR(500) NOT NULL,
    thumb_path VARCHAR(500) NULL,
    large_path VARCHAR(500) NULL,
    filename VARCHAR(255) NOT NULL,
    size INTEGER NOT NULL,
    mime VARCHAR(100) NOT NULL,
    format VARCHAR(20) NOT NULL,
    kind VARCHAR(20) NOT NULL CONSTRAINT ck_post_media_kind CHECK (kind IN ('image', 'video')),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_post_media_post_id ON post_media (post_id);
CREATE INDEX IF NOT EXISTS ix_post_media_owner_id ON post_media (owner_id);

-- 11. bots
CREATE TABLE IF NOT EXISTS bots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    persona TEXT NOT NULL,
    poll_interval_n INTEGER NOT NULL DEFAULT 600 CONSTRAINT ck_bots_poll_n CHECK (poll_interval_n > 0),
    poll_interval_x INTEGER NOT NULL DEFAULT 60 CONSTRAINT ck_bots_poll_x CHECK (poll_interval_x >= 0),
    lookback_days INTEGER NOT NULL DEFAULT 3 CONSTRAINT ck_bots_lookback CHECK (lookback_days > 0),
    comments_per_hour INTEGER NOT NULL DEFAULT 10 CONSTRAINT ck_bots_cph CHECK (comments_per_hour > 0),
    max_consecutive_failures INTEGER NOT NULL DEFAULT 5,
    llm_model VARCHAR(100) NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    auto_paused BOOLEAN NOT NULL DEFAULT FALSE,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_run_at TIMESTAMP WITHOUT TIME ZONE NULL,
    next_run_at TIMESTAMP WITHOUT TIME ZONE NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_bots_enabled ON bots (enabled);

-- 12. bot_reply_logs
CREATE TABLE IF NOT EXISTS bot_reply_logs (
    id SERIAL PRIMARY KEY,
    bot_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    kind VARCHAR(20) NOT NULL,
    target_comment_id INTEGER NULL,
    reply_comment_id INTEGER NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_bot_reply_target UNIQUE (bot_user_id, post_id, kind, target_comment_id)
);

CREATE INDEX IF NOT EXISTS ix_bot_reply_logs_bot ON bot_reply_logs (bot_user_id);

-- 13. alembic_version
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
