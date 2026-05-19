-- Migration: Add deleted_at column to event table for soft-delete support.
-- Events with deleted_at set are hidden from public queries after 48 hours.
ALTER TABLE event ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;
