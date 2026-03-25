create table if not exists public.negotiation_sessions (
  session_id text primary key,
  state jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint negotiation_sessions_session_id_not_blank check (btrim(session_id) <> ''),
  constraint negotiation_sessions_state_is_object check (jsonb_typeof(state) = 'object')
);

create or replace function public.set_negotiation_sessions_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_negotiation_sessions_updated_at on public.negotiation_sessions;

create trigger set_negotiation_sessions_updated_at
before update on public.negotiation_sessions
for each row
execute function public.set_negotiation_sessions_updated_at();

comment on table public.negotiation_sessions is 'Canonical negotiation session state for the Streamlit MVP.';
comment on column public.negotiation_sessions.state is 'Full serialized negotiation state as maintained by the repository contract.';
