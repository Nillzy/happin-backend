-- Ticket-Status von TEXT mit CHECK-Constraint zu Enum konvertieren
CREATE TYPE ticket_status AS ENUM ('active', 'used', 'expired');

ALTER TABLE ticket DROP CONSTRAINT IF EXISTS ticket_status_check;

ALTER TABLE ticket
    ALTER COLUMN status DROP DEFAULT,
    ALTER COLUMN status TYPE ticket_status USING status::ticket_status,
    ALTER COLUMN status SET DEFAULT 'active';
