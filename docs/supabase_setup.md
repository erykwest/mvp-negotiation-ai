# Supabase Setup

This repository is currently organized around a single persistence contract:

- `load(session_id)`
- `save(session_id, state)`

The initial Supabase integration should keep that contract intact and store the full canonical negotiation state as one `jsonb` document per session.

## Database Schema

Apply the migration in `supabase/migrations/001_initial_negotiation_sessions.sql`.

It creates:

- `public.negotiation_sessions`
- `session_id` as the primary key
- `state` as the canonical `jsonb` payload
- `created_at` and `updated_at` timestamps

The table is intentionally minimal. Do not split the negotiation state into multiple tables until the application needs explicit cross-session querying.

## Provisioning Steps

1. Create a Supabase project.
2. Open the SQL editor or use the Supabase CLI.
3. Run the initial migration.
4. Capture the Postgres connection string for server-side use.
5. Configure the app to read a direct Postgres URL from an environment variable.

Recommended environment variable names:

- `SUPABASE_DB_URL`
- `DATABASE_URL`

Use one of them consistently in the Python backend. The app should connect through Postgres directly, not through browser-side Supabase client calls.

## Runtime Expectations

- The backend should treat `session_id` as the stable row key.
- Inserts and updates should upsert the full `state` document.
- `updated_at` should change whenever a session is written.
- `state` should always remain a JSON object, not an array or scalar.

## Migration Notes

- The current repository still has file-backed session storage.
- A database-backed repository should be introduced behind the existing repository contract.
- Existing `data/*.json` files can be migrated into `negotiation_sessions` with a one-shot import script.

## Assumptions

- Authentication and RLS are out of scope for this first storage pass.
- This setup is for trusted server-side access only.
- The table is meant to hold the authoritative session snapshot, not a normalized analytics model.
