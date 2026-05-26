-- Add avatar_url column to person table
ALTER TABLE person ADD COLUMN IF NOT EXISTS avatar_url TEXT;
