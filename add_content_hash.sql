-- Pixel fingerprint of each image's 600px version, used by update_all.py to recognise
-- renamed images (it also adds this column automatically on its first run)
ALTER TABLE images ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
CREATE INDEX IF NOT EXISTS idx_images_content_hash ON images (content_hash);

COMMENT ON COLUMN images.content_hash IS 'SHA-256 of decoded pixels of the 600px version (ignores EXIF and file name)';
