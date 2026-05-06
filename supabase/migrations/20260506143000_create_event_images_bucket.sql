-- Create public storage bucket for event cover images
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'event-images',
  'event-images',
  true,
  10485760, -- 10 MB
  ARRAY['image/jpeg', 'image/png', 'image/webp']
);

-- Allow authenticated users to upload files
CREATE POLICY "authenticated_upload" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'event-images');

-- Allow authenticated users to update/overwrite their uploads
CREATE POLICY "authenticated_update" ON storage.objects
  FOR UPDATE TO authenticated
  USING (bucket_id = 'event-images');

-- Allow authenticated users to delete their uploads
CREATE POLICY "authenticated_delete" ON storage.objects
  FOR DELETE TO authenticated
  USING (bucket_id = 'event-images');

-- Allow public read access (cover images are public)
CREATE POLICY "public_read" ON storage.objects
  FOR SELECT
  USING (bucket_id = 'event-images');
