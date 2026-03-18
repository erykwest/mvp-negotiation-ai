# SUPABASE

## Purpose
This document defines how Supabase must be used in the project.

Supabase is the backend foundation of the application.

It is responsible for:
- authentication
- persistence
- authorization
- core application data

## Main Responsibilities

### 1. Authentication
Supabase Auth manages:
- sign up
- sign in
- sign out
- sessions
- password reset
- user identity

### 2. Database
Supabase Postgres stores the application state.

### 3. Authorization
Supabase RLS policies enforce who can read and write which rows.

### 4. User-related app data
Application-level user data must be stored in project tables, not only in auth tables.

## Required Core Tables

The exact schema can evolve, but the MVP should include at least:

### profiles
Purpose:
stores app-level user data

Suggested fields:
- id
- email
- full_name optional
- platform_role
- plan
- subscription_status
- created_at
- updated_at

Notes:
- id should match auth user id
- platform_role supports normal users and platform admins
- plan and subscription state will later be synced from Stripe

### negotiations
Purpose:
stores negotiation containers

Suggested fields:
- id
- owner_user_id
- title optional
- status
- created_at
- updated_at

Suggested statuses:
- draft
- active
- closed
- cancelled

### participants
Purpose:
links users to negotiations

Suggested fields:
- id
- negotiation_id
- user_id
- participant_role
- invitation_status
- created_at
- updated_at

Suggested participant_role values:
- owner
- invited

Suggested invitation_status values:
- pending
- accepted
- declined

### invitations
Purpose:
tracks invite flows explicitly if needed

Suggested fields:
- id
- negotiation_id
- invited_email
- invited_by_user_id
- status
- token optional
- created_at
- expires_at optional

This table is optional but strongly recommended if invite lifecycle is important.

## Optional Future Tables
Not mandatory in the first pass, but likely later:
- rounds
- round_entries
- negotiation_messages
- audit_logs
- usage_events

## Data Ownership Rules

### profiles
A normal user can read and update only their own profile unless platform admin logic explicitly allows otherwise.

### negotiations
A user can access a negotiation only if they are a participant in it.

### participants
A user can access participant records only for negotiations they belong to.

### invitations
Only privileged server-side logic or authorized owners should create invite records.

## RLS Principles

### Mandatory rule
Every user-facing table must have RLS enabled.

### Do not trust the frontend
The frontend may hide buttons, but true enforcement must happen in RLS.

### Ownership must be explicit
Do not infer access from vague UI state.
Access should be derived from actual rows in:
- participants
- ownership fields
- platform role if explicitly needed

## Example Access Philosophy

### Negotiation read
Allowed only if current user is listed in participants for that negotiation.

### Negotiation creation
Allowed for authenticated users.

### Negotiation update
Allowed only if current user belongs to that negotiation and action rules permit it.

### Cross-user access
Never allowed by default.

## Profiles and Auth Relationship
Supabase Auth stores identity data.
The app must maintain a matching profile row.

Required behavior:
- when a new user is created, ensure a profile row exists
- app UI should read from profiles, not directly depend on raw auth metadata for business logic

## Invite Flow Guidance
Invitation logic should follow this model:

1. owner creates negotiation
2. owner enters counterpart email
3. invitation record is created
4. invited user receives email
5. invited user signs in or signs up
6. invited user is linked to negotiation as participant
7. invitation status becomes accepted

Important:
the system should not grant negotiation access only because an email was typed.
Actual participant linkage must exist in the database.

## Secrets and Security
Never expose the Supabase service role key in frontend code.

Allowed in frontend:
- public Supabase URL
- anon public key

Allowed only in trusted server-side contexts:
- service role key
- admin operations
- invite operations requiring elevated privileges

## Platform Admin Model
platform_admin is a role stored at app level, typically in profiles.

Important:
platform_admin is not the same as a negotiation participant role.

This role is for:
- support
- maintenance
- moderation
- inspection if explicitly implemented

Do not expose admin capabilities by default in normal user UI.

## Expected Environment Variables

Public:
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY

Server-side only:
- SUPABASE_SERVICE_ROLE_KEY

## Codex Instructions

Codex must:
- use Supabase as the only backend database and auth provider
- design schema around explicit ownership and participants
- enable RLS on all user-facing tables
- avoid direct trust in UI state
- keep platform admin logic separate from participant logic

Codex must not:
- introduce Firebase
- store business-critical data only in client state
- use service role key in browser code
- skip profile creation strategy
- create open access tables without RLS