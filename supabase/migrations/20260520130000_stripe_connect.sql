-- ============================================================
-- Migration: Stripe Connect – person fields, ticket_order, ticket FK
-- ============================================================

-- 1. person – Connect account status
ALTER TABLE public.person
    ADD COLUMN stripe_connect_account_id text UNIQUE,
    ADD COLUMN stripe_connect_charges_enabled boolean NOT NULL DEFAULT false,
    ADD COLUMN stripe_connect_payouts_enabled boolean NOT NULL DEFAULT false,
    ADD COLUMN stripe_connect_onboarding_completed_at timestamptz;

-- 2. event – payout recipient (defaults to creator)
ALTER TABLE public.event
    ADD COLUMN payout_person_id uuid REFERENCES public.person(person_id);

-- 3. ticket_order – checkout state before ticket issuance
CREATE TYPE public.ticket_order_status AS ENUM ('pending', 'paid', 'expired', 'failed');

CREATE TABLE public.ticket_order (
    ticket_order_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id uuid NOT NULL REFERENCES public.event(event_id) ON DELETE CASCADE,
    person_id uuid NOT NULL REFERENCES public.person(person_id) ON DELETE CASCADE,
    ticket_option_id uuid REFERENCES public.ticket_option(ticket_option_id),
    quantity integer NOT NULL DEFAULT 1 CHECK (quantity > 0),
    amount_total_cents integer NOT NULL CHECK (amount_total_cents >= 0),
    application_fee_cents integer NOT NULL DEFAULT 0 CHECK (application_fee_cents >= 0),
    stripe_checkout_session_id text UNIQUE,
    stripe_payment_intent_id text,
    status public.ticket_order_status NOT NULL DEFAULT 'pending',
    paid_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_ticket_order_event ON public.ticket_order(event_id);
CREATE INDEX idx_ticket_order_person ON public.ticket_order(person_id);
CREATE INDEX idx_ticket_order_status ON public.ticket_order(status);

ALTER TABLE public.ticket_order ENABLE ROW LEVEL SECURITY;

-- Users can read their own orders
CREATE POLICY "users_select_own_orders" ON public.ticket_order
    FOR SELECT USING (person_id IN (
        SELECT p.person_id FROM public.person p WHERE p.supabase_user_id = auth.uid()
    ));

-- Hosts can read orders for their events
CREATE POLICY "hosts_select_event_orders" ON public.ticket_order
    FOR SELECT USING (event_id IN (
        SELECT eh.event_id FROM public.event_host eh
        JOIN public.person p ON p.person_id = eh.person_id
        WHERE p.supabase_user_id = auth.uid()
    ));

-- Backend service role handles inserts/updates (no user-facing write policy)
CREATE POLICY "service_role_all" ON public.ticket_order
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 4. ticket – link to order for paid tickets
ALTER TABLE public.ticket
    ADD COLUMN ticket_order_id uuid REFERENCES public.ticket_order(ticket_order_id);
