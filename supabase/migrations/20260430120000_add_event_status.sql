-- ============================================================
-- Migration: Add event status column (draft/published)
-- ============================================================
-- Events can now be in 'draft' (only visible to host) or
-- 'published' (visible to everyone). Default is 'published'
-- for backward compatibility with existing events.
-- ============================================================

ALTER TABLE event
ADD COLUMN status text NOT NULL DEFAULT 'published';
