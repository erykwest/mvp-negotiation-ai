# CODEX_IMPLEMENTATION_RULES

## Purpose
This document defines how Codex should operate on this repository.

Its goal is to reduce architectural drift, avoid incoherent code generation, and keep implementation aligned with the target MVP stack.

The target stack is:
- Next.js
- Vercel
- Supabase
- Stripe

Codex must treat these choices as fixed unless explicitly changed by the user.

## Primary Objective
Codex must help implement a production-oriented MVP starting from an already validated prototype logic.

Codex is not expected to invent product strategy.
Codex is expected to implement clearly scoped tasks inside the defined architecture.

## Non-Negotiable Constraints

### 1. Do not change the stack autonomously
Do not replace or introduce alternatives such as:
- Firebase
- Clerk
- Auth0
- custom Express backend
- random UI frameworks
- alternative billing providers

unless explicitly requested by the user.

### 2. Do not invent architecture
If a document defines an architectural boundary, respect it.

Examples:
- Supabase handles auth, persistence and authorization
- Stripe handles billing
- Vercel hosts the Next.js app
- frontend is not the source of truth for permissions

### 3. Do not move security to the client
Never implement business-critical enforcement only in frontend components.

Examples of logic that must not live only in the UI:
- access control
- subscription enforcement
- negotiation ownership validation
- invite authorization
- admin-only actions

### 4. Do not expose secrets
Never place secret values in:
- client code
- public config
- committed source files

Only public environment variables may be used in browser code.

## Implementation Philosophy

### Prefer small scoped changes
Codex should prefer:
- small patches
- focused features
- minimal surface area changes
- readable implementations

over:
- large rewrites
- speculative abstraction
- broad refactors without explicit request

### Preserve working code when possible
If an existing part works and is compatible with the target architecture, improve it incrementally instead of rewriting it completely.

### Refactor only with reason
Refactor when at least one of these is true:
- current code blocks the requested feature
- current code violates architecture
- duplication is creating real maintenance risk
- security or correctness requires change

Do not refactor just for style preference.

## Source of Truth Priority
When documents disagree, use this priority order:

1. explicit user instruction in current conversation
2. architecture documents in `docs/`
3. current repository constraints
4. inferred best practice

If something is ambiguous, prefer the least disruptive implementation consistent with the architecture.

## Required Reading Before Major Changes
Before implementing significant features, Codex should read and respect:
- `docs/00_ARCHITECTURE.md`
- `docs/10_SUPABASE.md`
- `docs/20_VERCEL_NEXTJS.md`
- `docs/30_STRIPE.md`
- this file

## Expected Work Pattern

### Step 1: Understand the task
Codex should identify:
- what feature is requested
- which layer it belongs to
- which documents constrain the implementation

### Step 2: Limit the scope
Codex should define the smallest meaningful implementation that satisfies the request.

### Step 3: Patch the correct layer
Examples:
- UI page request -> frontend layer
- access rule request -> Supabase schema / policies / server-side logic
- billing request -> Stripe + synced DB state
- deployment request -> environment and build config

### Step 4: Preserve boundaries
A frontend request must not silently create backend architecture changes unless necessary.
A billing request must not silently rework auth.
An auth request must not silently redesign the whole schema.

### Step 5: Explain file changes clearly
When generating a patch or implementation summary, Codex should explain:
- which files were added or changed
- why they were changed
- what assumptions were made

## Rules for Database and Supabase Changes

### Schema changes must be explicit
When changing schema, Codex should:
- name the affected tables
- explain the purpose of new columns / constraints
- preserve ownership logic
- preserve future compatibility where reasonable

### RLS is mandatory
For user-facing tables:
- enable RLS
- define access based on explicit ownership or participant linkage
- never leave sensitive tables wide open

### Profiles are app-level user records
Do not rely only on raw auth metadata for business logic.
Use `profiles` or equivalent app tables.

## Rules for Frontend Changes

### Keep pages and components simple
Prefer understandable components over highly abstract patterns.

### Do not bury logic inside presentation components
Complex business rules should be separated from visual rendering when possible.

### Respect public vs server-only boundaries
Do not import server-only secrets into client bundles.
Do not blur browser and server responsibilities.

### Do not copy Streamlit literally
The Streamlit prototype validates flow, not final UI structure.
Codex may redesign presentation as long as the validated business flow is preserved.

## Rules for Stripe Changes

### Stripe is for billing, not full authorization
Billing state must be synchronized into app data.

### Webhooks are required
Do not build billing logic that depends only on success redirects.

### Keep plans simple
For MVP:
- free
- pro monthly
- pro yearly

Avoid implementing advanced pricing models unless explicitly requested.

## Rules for Admin Features

### No public admin power by default
Platform admin capabilities must remain isolated and protected.

### Admin is platform-level
Do not confuse:
- negotiation participant roles
with
- platform admin roles

### No premature admin dashboard
Do not build a large admin UI unless explicitly requested.

## Allowed Assumptions
Codex may assume:
- the project is moving from local prototype to live MVP
- multi-user access is required
- invitation-based negotiation participation is required
- subscription support is planned
- GitHub is the source repository
- Vercel deployment is the target
- Supabase is the backend base

## Forbidden Behaviors
Codex must not:
- invent hidden infrastructure
- create parallel auth systems
- replace Supabase with another backend
- replace Stripe with another billing tool
- hardcode environment values
- disable RLS for convenience
- implement fake security in the UI only
- overengineer the MVP into an enterprise platform

## Preferred Output Style for Codex
When completing a task, Codex should provide:

### 1. Summary
What was implemented.

### 2. Files changed
Exact files added or modified.

### 3. Notes
Important assumptions, limits, or follow-up items.

### 4. Minimalism
Prefer the simplest correct implementation.

## MVP Mindset
This repository is building a serious MVP, not a throwaway toy.

That means:
- fast implementation is good
- clean boundaries are required
- shortcuts are acceptable only if they do not poison the architecture
- future growth should remain possible without full rewrite

Codex should optimize for:
- correctness
- clarity
- architectural consistency
- incremental evolution