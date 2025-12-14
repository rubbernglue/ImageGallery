-- Add reload flag column to images table
ALTER TABLE images ADD COLUMN IF NOT EXISTS needs_reload BOOLEAN DEFAULT FALSE;

-- Create index for quick lookup
CREATE INDEX IF NOT EXISTS idx_images_needs_reload ON images (needs_reload) WHERE needs_reload = TRUE;

-- Add comment
COMMENT ON COLUMN images.needs_reload IS 'Flag to mark images that should be reprocessed from source';
