-- Add latitude and longitude columns to location table for map display
ALTER TABLE "public"."location"
    ADD COLUMN IF NOT EXISTS "latitude"  double precision,
    ADD COLUMN IF NOT EXISTS "longitude" double precision;
