ALTER TABLE public.person
  ADD COLUMN supabase_user_id UUID UNIQUE;

CREATE INDEX idx_person_supabase_user_id ON public.person USING btree (supabase_user_id);
