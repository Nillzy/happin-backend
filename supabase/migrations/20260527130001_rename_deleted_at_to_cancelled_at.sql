-- Migration: Rename event.deleted_at to event.cancelled_at to reflect cancellation semantics.
-- The action has cancellation side-effects (Stripe refunds), not classic soft-delete semantics.
ALTER TABLE event RENAME COLUMN deleted_at TO cancelled_at;
