# VERCEL_AND_NEXTJS

## Purpose
This document defines how the frontend and deployment layer must be handled.

The production-facing frontend stack is:
- Next.js for the application
- Vercel for hosting and deployment

## Why This Stack
This stack is chosen because it provides:
- fast UI development
- production-friendly web architecture
- simple GitHub-based deployment
- clean path from MVP to more mature product

## Role of Next.js
Next.js is the frontend application layer.

It is responsible for:
- pages and routes
- authentication screens
- dashboard UI
- negotiation interface
- billing screens
- account screens
- client-side interactions
- server-side handlers when needed

Next.js is not the long-term source of truth for business permissions.
Critical state remains in Supabase.

## Role of Vercel
Vercel is the hosting and deployment platform.

It is responsible for:
- building the Next.js app
- deploying environments
- preview builds for branches
- environment variable management
- production hosting

Vercel is not the database and not the auth engine.

## Repository and Deployment Model

### GitHub
GitHub is the source repository.

### Deployment flow
1. code is pushed to GitHub
2. Vercel builds the project
3. preview deployment is created for branches if configured
4. production deployment updates from the selected branch

## Environment Strategy

At minimum, assume:
- local development environment
- preview environment
- production environment

Do not hardcode environment-specific URLs or keys.

## Required Environment Variables

Public variables:
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY
- NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY

Server-side variables:
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- SUPABASE_SERVICE_ROLE_KEY

Optional later:
- APP_BASE_URL
- SMTP settings if custom email flow is introduced

## Public vs Server-Side Rule

### Public variables
May be exposed to the frontend bundle.
These are safe only if they are designed to be public.

### Server-side variables
Must never be shipped to the browser.
They must only be used in trusted server contexts.

## Frontend Architecture Guidance

### Keep UI modular
The app should be organized into reusable sections such as:
- auth
- dashboard
- negotiations
- invitations
- billing
- account

### Keep business logic out of UI components
React components should render and orchestrate.
They should not become the final location of business enforcement.

### Keep server-side integration explicit
Server-only code should be clearly separated from browser-only code.

## Suggested Functional Areas

### Public area
- landing page optional
- sign in
- sign up
- password reset

### Authenticated user area
- dashboard
- create negotiation
- invitation flow
- negotiation list
- negotiation detail
- billing / plan page
- account page

### Optional later admin area
Not required in MVP phase 1.

## Sensitive Actions
The following should not rely only on client-side code:
- subscription verification
- invite acceptance logic if privileged
- admin actions
- usage limit enforcement
- any action using secret keys

## UI Transition from Streamlit
The new Next.js UI does not need to copy Streamlit literally.

It should preserve:
- validated flows
- key states
- user journey

It should improve:
- navigation
- persistence
- UX clarity
- multi-user behavior
- browser-quality presentation

## Performance and Simplicity Guidance
For the MVP:
- prefer simple, readable structure
- avoid premature optimization
- avoid overengineering
- prefer maintainability over clever abstractions

## Codex Instructions

Codex must:
- build the frontend in Next.js
- assume deployment on Vercel
- use environment variables correctly
- separate client-safe code from server-only code
- keep the app modular and readable

Codex must not:
- recreate the MVP in Streamlit
- hardcode secrets
- move business-critical access rules into UI only
- introduce unnecessary infrastructure complexity
