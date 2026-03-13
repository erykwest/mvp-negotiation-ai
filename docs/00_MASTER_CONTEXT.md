# MASTER CONTEXT

## Project
Negotiation Assistant

## Current Goal
Build a browser-based MVP for assisted negotiation, starting from the recruiting use case.

## Product Scope (MVP)
Two-party negotiation:
- Company
- Candidate

Negotiation rounds:
1. Alignment
2. Requests
3. Agreement
4. Last Call (optional)

## Current Repository Strategy
The existing codebase remains active.
New folders (`docs/`, `product/`, `prompts/`, `tests/`) are the strategic layer and source of truth for product evolution.
We do not refactor the whole repo yet.

## Current Implementation State
Current app is an early technical prototype.
It is not yet a real multi-user web application.
It still contains technical debt and temporary structures.

## Source of Truth Files
- docs/00_MASTER_CONTEXT.md
- docs/02_PRD_MVP.md
- docs/11_DECISIONS_ADR.md
- docs/12_BUG_LOG.md
- docs/14_BACKLOG.md

## Current Priorities
1. Fill core strategic docs
2. Freeze MVP boundaries
3. Clean main negotiation flow
4. Choose one official UI path
5. Prepare next implementation pass

## Known Gaps
- Duplicate or unclear negotiation flow logic
- Parallel UI structure
- Single-session prototype logic
- Strategic docs not yet connected to code decisions
