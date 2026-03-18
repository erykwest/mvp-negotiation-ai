# ARCHITECTURE

## Purpose
This document defines the target architecture for the live MVP of the Negotiation Assistant.

The current Streamlit prototype is useful for validating flows and logic, but it is not the final production frontend.

The production-oriented MVP architecture is:

- Frontend: Next.js
- Hosting / Deployment: Vercel
- Backend: Supabase
- Billing: Stripe
- Source control: GitHub

## High-Level Principles

### 1. Clear separation of concerns
The system must be separated into:
- presentation layer
- business logic
- data layer
- infrastructure / deployment layer

### 2. Backend is the source of truth
All critical state must live in Supabase.
Frontend must never be the source of truth for:
- permissions
- subscription status
- negotiation ownership
- participant access
- usage limits

### 3. Frontend must stay thin
Next.js is responsible for:
- rendering UI
- collecting user input
- calling backend services
- showing state and results

Next.js must not become a hidden backend full of duplicated business rules.

### 4. Sensitive actions must be server-side
Sensitive logic must run only in trusted environments:
- Stripe webhook handling
- admin operations
- invite flows requiring privileged access
- any usage of secret keys

### 5. Authorization must be enforced at database level
Access control must not rely only on frontend conditions.
Supabase Row Level Security (RLS) is mandatory.

## Core Components

## Frontend: Next.js
Responsibilities:
- authentication screens
- dashboard
- negotiation creation flow
- invitation flow UI
- negotiation round UI
- subscription / billing UI
- account area

Non-responsibilities:
- privileged admin actions
- direct handling of secret keys
- final enforcement of permissions

## Hosting: Vercel
Responsibilities:
- deploy Next.js app
- manage environments
- manage environment variables
- provide preview deployments for branches

Non-responsibilities:
- user management
- database
- billing state
- business data persistence

## Backend: Supabase
Responsibilities:
- authentication
- database
- row-level authorization
- persistence of app data
- profiles
- negotiations
- participants
- rounds
- messages / proposals if introduced later
- usage / quota support if introduced later

Non-responsibilities:
- frontend rendering
- public hosting of the app UI

## Billing: Stripe
Responsibilities:
- checkout
- recurring subscriptions
- customer portal
- billing lifecycle
- billing webhooks

Non-responsibilities:
- application authorization by itself
- direct UI ownership
- negotiation logic

Stripe is the billing engine. Supabase is the source of truth for app access after webhook synchronization.

## GitHub
Responsibilities:
- source of code
- source of technical documentation
- source of Codex implementation instructions
- collaboration and versioning

## MVP Functional Model

### User Roles
For the MVP, define only these application roles:

- owner
  - creates a negotiation
  - invites the counterpart
- invited
  - joins a negotiation through invitation
  - participates only in assigned negotiations
- platform_admin
  - global platform operator
  - not a normal negotiation participant
  - handles maintenance and support

Important:
platform_admin is a platform-level role, not a negotiation-level role.

## Suggested Main Flows

### Flow 1: Authentication
1. user signs up or signs in
2. profile is created or loaded
3. user accesses dashboard

### Flow 2: Negotiation creation
1. owner creates a negotiation
2. negotiation record is stored
3. owner is inserted as participant

### Flow 3: Invitation
1. owner enters counterpart email
2. system creates invitation relationship
3. invited user receives email
4. invited user signs up or signs in
5. invited user is attached to the negotiation

### Flow 4: Negotiation participation
1. both participants access only authorized negotiations
2. each participant interacts with permitted data only
3. all reads and writes respect RLS

### Flow 5: Billing
1. user selects plan
2. Stripe checkout completes
3. Stripe webhook fires
4. app state in Supabase is updated
5. usage rules and premium access depend on synced plan state

## Non-Goals for the First Live MVP
Do not introduce these unless explicitly needed:
- microservices
- custom standalone backend server
- event bus
- advanced admin dashboard
- complex team / workspace model
- per-action paid billing
- complex enterprise permissions

## Migration Mindset from Streamlit
The Streamlit prototype validates:
- flow sequence
- business assumptions
- interaction pattern

The production MVP should preserve:
- business logic
- user flow
- negotiation structure

The production MVP should replace:
- Streamlit UI
- local session-driven state
- prototype-only shortcuts

## Coding Guidance for Codex
Codex must:
- preserve architectural boundaries
- keep logic modular
- avoid hidden coupling between billing, auth and UI
- use Supabase as persistent backend
- use Stripe only for billing lifecycle
- use Vercel assumptions for deployment

Codex must not:
- introduce Firebase
- expose secrets in frontend code
- bypass RLS
- implement authorization only in React components
- invent new infrastructure without explicit instruction