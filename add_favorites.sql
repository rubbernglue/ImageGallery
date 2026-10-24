-- Per-user favorite images
CREATE TABLE IF NOT EXISTS favorites (
    username VARCHAR(100) NOT NULL,                                -- Username from config_auth.USERS
    image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, image_id)
);

COMMENT ON TABLE favorites IS 'Images favorited by each logged-in user';
