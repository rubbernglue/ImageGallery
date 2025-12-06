-- Create the main table for image metadata
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    image_id VARCHAR(255) UNIQUE NOT NULL, -- The unique key derived from the path (e.g., 'sheetfilm/5x7_0041-0045/0042_Panchro400')
    film_type VARCHAR(50) NOT NULL,       -- 'rollfilm' or 'sheetfilm'
    batch_info VARCHAR(255) NOT NULL,     -- The folder name (e.g., '5x7_0041-0045')
    filename_base VARCHAR(255) NOT NULL,  -- The unique filename part (e.g., '0042_Panchro400')
    film_stock VARCHAR(100),              -- Extracted film stock (e.g., 'Panchro400', 'tmax100')
    thumbnail_path VARCHAR(512) NOT NULL, -- Path to the 600px version
    highres_path VARCHAR(512) NOT NULL,   -- Path to the 2560px version
    description TEXT,                     -- User-added description or notes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast searching on film type and film stock
CREATE INDEX idx_images_type_stock ON images (film_type, film_stock);

-- Create a table for unique tags
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- Create a junction table for the many-to-many relationship between images and tags
CREATE TABLE image_tags (
    image_id INTEGER REFERENCES images(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (image_id, tag_id)
);

-- Function to update the updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW(); 
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to use the function when the 'images' table is updated
CREATE TRIGGER update_image_updated_at
BEFORE UPDATE ON images
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();

-- Optional: Create a full-text search index if you want complex text searching on descriptions
-- CREATE INDEX idx_images_description_fts ON images USING gin (to_tsvector('english', description));
