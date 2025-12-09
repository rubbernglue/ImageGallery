-- Add EXIF columns to existing images table
-- Run this to add EXIF support to your existing database

ALTER TABLE images ADD COLUMN IF NOT EXISTS exif_data JSONB;
ALTER TABLE images ADD COLUMN IF NOT EXISTS camera_make VARCHAR(100);
ALTER TABLE images ADD COLUMN IF NOT EXISTS camera_model VARCHAR(100);
ALTER TABLE images ADD COLUMN IF NOT EXISTS lens_model VARCHAR(100);
ALTER TABLE images ADD COLUMN IF NOT EXISTS focal_length VARCHAR(20);
ALTER TABLE images ADD COLUMN IF NOT EXISTS aperture VARCHAR(10);
ALTER TABLE images ADD COLUMN IF NOT EXISTS shutter_speed VARCHAR(20);
ALTER TABLE images ADD COLUMN IF NOT EXISTS iso VARCHAR(10);
ALTER TABLE images ADD COLUMN IF NOT EXISTS date_taken TIMESTAMP;

-- Create indexes for common EXIF searches
CREATE INDEX IF NOT EXISTS idx_images_camera_make ON images (camera_make);
CREATE INDEX IF NOT EXISTS idx_images_camera_model ON images (camera_model);
CREATE INDEX IF NOT EXISTS idx_images_date_taken ON images (date_taken);
CREATE INDEX IF NOT EXISTS idx_images_exif_data ON images USING gin (exif_data);

-- Add comment
COMMENT ON COLUMN images.exif_data IS 'Full EXIF data as JSON for advanced queries';
COMMENT ON COLUMN images.camera_make IS 'Camera manufacturer (e.g., Canon, Nikon)';
COMMENT ON COLUMN images.camera_model IS 'Camera model (e.g., Canon EOS 5D)';
COMMENT ON COLUMN images.lens_model IS 'Lens model/description';
COMMENT ON COLUMN images.focal_length IS 'Focal length (e.g., 50mm, 24-70mm)';
COMMENT ON COLUMN images.aperture IS 'Aperture value (e.g., f/2.8, f/8)';
COMMENT ON COLUMN images.shutter_speed IS 'Shutter speed (e.g., 1/1000, 1")';
COMMENT ON COLUMN images.iso IS 'ISO value (e.g., 100, 400, 3200)';
COMMENT ON COLUMN images.date_taken IS 'Date and time the photo was taken';
