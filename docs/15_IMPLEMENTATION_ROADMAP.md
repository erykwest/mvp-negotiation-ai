# 15 Implementation Roadmap

## Purpose

This document converts the long-range product roadmap into an implementation-oriented artifact.

It is meant to answer these practical questions:

- what we should build next
- what belongs to MVP vs later platform evolution
- which modules are affected
- what a phase must prove before we move on
- how to split phases into implementation-ready work

The source of truth for product vision remains the long-range roadmap. This document is the engineering translation layer.

---

## Planning Rules

### Product boundary

For now the product remains:

- a role-based negotiation workflow
- human-in-the-loop
- file-backed
- recruiting-first

We should not expand into multi-domain, multi-party procurement, or semantic normalization-heavy workflows until the current negotiation protocol is stable.

### Delivery rule

Each phase must produce:

- visible product behavior
- testable backend behavior
- a report or decision artifact that justifies the next phase

### Engineering rule

Prefer incremental extension of the current architecture:

- `company_app.py`
- `candidate_app.py`
- `admin_app.py`
- `core/`

Do not re-platform the app unless a specific phase requires it.

---

## Current Baseline

The repository already supports:

- separate company, candidate, and admin interfaces
- per-session file-backed state
- round-based workflow
- dynamic topics in round 2
- final report generation
- human review between rounds
- automated tests around storage, negotiation, validation, and reports

This means Phase 0 and most of Phase 1 are effectively underway or partially complete.

---

## Delivery Tracks

The roadmap is easier to implement if we split it into five delivery tracks.

### Track A - Negotiation workflow

- round states
- human review
- pause / resume / reconsideration
- last call

### Track B - Structured data model

- priorities
- ranges
- deal breakers
- dynamic topics
- RFI objects

### Track C - Orchestration and timing

- scheduling
- deadlines
- reminders
- direct negotiation mode vs rigid competition mode

### Track D - Multi-party comparison

- one-to-many negotiations
- public/private clarification spaces
- candidate or supplier selection
- comparison matrix

### Track E - Semantic intelligence

- topic normalization
- document extraction
- multilingual normalization
- meta-negotiation insights

---

## Implementation Phases

## Phase 0 - Recruiting Core Demo

### Goal

Keep the current recruiting prototype stable and demoable.

### What must exist

- role-based flow works end-to-end
- report is readable
- session handling is understandable
- errors do not break the demo

### Engineering scope

- stabilize existing Streamlit flow
- improve run instructions and local ergonomics
- keep file-backed persistence
- keep legacy `app/` flow read-only

### Main modules

- `company_app.py`
- `candidate_app.py`
- `admin_app.py`
- `core/storage.py`
- `core/report.py`

### Exit criteria

- a demo user can complete one negotiation without manual file edits
- tests pass
- README is sufficient for local setup

---

## Phase 1 - Structured Human In The Loop

### Goal

Make the workflow explicitly stateful and editable between rounds.

### Product changes

- round 1, round 2, round 3 are separate steps
- each round ends in review
- users can change priorities and inputs before advancing
- admin controls progression

### Implementation slices

1. state machine hardening
2. clearer review gating
3. explicit editing vs review vs closed states
4. audit-friendly round summaries

### Data additions

- optional per-round metadata
- timestamps for round execution and review
- actor action log placeholder structure

### Acceptance criteria

- every round can be rerun without corrupting state
- advancing requires valid review state
- report shows round-by-round progression clearly

### Dependency

This phase must be fully stable before adding RFI logic.

---

## Phase 2 - Structured RFI

### Goal

Turn round 1 into semantic alignment, not just summarization.

### Product changes

- system generates RFI items after initial inputs
- each RFI is assigned to one side or both sides
- users answer RFIs before round 2
- unresolved RFIs block or warn before negotiation continues

### Implementation slices

1. define RFI model
2. create RFI generation step in admin workflow
3. add company/candidate RFI response UI
4. merge resolved RFIs into state before round 2
5. expose unresolved RFIs in report

### Suggested data shape

- `rfis: []`
- each item should minimally include:
  - `id`
  - `phase`
  - `type`
  - `topic`
  - `question`
  - `target_side`
  - `status`
  - `response_company`
  - `response_candidate`

### RFI classes to support first

- missing data
- ambiguous statement
- incomparable units
- possible new topic

### Acceptance criteria

- at least one round-1 result can emit RFIs
- each side only sees actionable RFIs for itself
- admin sees resolved vs unresolved RFIs clearly

### Dependency

Requires stable review gating from Phase 1.

---

## Phase 3 - Controlled Dynamic Structure

### Goal

Allow semi-flexible negotiation without losing comparability.

### Product changes

- macro sections remain fixed
- topics and subtopics can be added in controlled windows
- deal breakers and weights can exist below macro-topic level
- hard caps prevent topic explosion

### Implementation slices

1. extend dynamic topic model into topic/subtopic hierarchy
2. add per-topic weight
3. add per-topic deal breaker
4. enforce max counts per section
5. surface added topics in review and report

### Suggested rules

- only editable in allowed phases
- must belong to a known macro section
- must have owner and explanation
- must remain readable in report output

### Acceptance criteria

- users can add new subtopics without breaking the phase flow
- admin can still understand the negotiation at a glance
- tests cover caps and invalid additions

---

## Phase 4 - Real Scheduling

### Goal

Make time part of the workflow, not an external manual convention.

### Product changes

- negotiation start date
- round deadlines
- reminder timing
- autosave vs submit
- direct negotiation mode and competition mode

### Implementation slices

1. add timeline model
2. add round deadlines and status transitions
3. distinguish draft/autosave from submitted state
4. define direct mode timing rules
5. define competition mode timing rules

### Important constraint

Do not build full notifications infrastructure first.
Start with persisted deadlines and computed statuses, then add reminders later.

### Acceptance criteria

- the app can determine whether a round is open, overdue, or submitted
- direct mode and rigid mode follow different timing rules
- timeline data appears in admin/report views

---

## Phase 5 - Reconsideration Pause

### Goal

Stop hopeless negotiations early and cleanly.

### Product changes

- new workflow state: reconsideration pause
- triggered by incompatible deal breakers or impossible ranges
- state can later be reopened

### Implementation slices

1. add pause state to workflow
2. define pause triggers
3. define reopen conditions
4. produce non-sensitive pause report

### Suggested trigger sources

- explicit deal breaker conflict
- non-overlapping mandatory range
- unresolved blocking RFI

### Acceptance criteria

- admin can see why the negotiation is paused
- neither side sees hidden strategy
- reopening is possible after material changes

---

## Phase 6 - Last Call Arbitration

### Goal

Introduce a controlled neutral compromise mechanism at the end.

### Product changes

- optional round 4
- platform proposes one final compromise
- parties can only accept or reject

### Implementation slices

1. define eligibility rules for last call
2. define neutral arbitration input bundle
3. define last-call proposal schema
4. add accept/reject handling
5. reflect last call outcome in final report

### Constraint

Do not expose hidden party strategy before last call.
Arbitration must be platform-only and auditable.

### Acceptance criteria

- last call only activates under explicit rules
- proposal is structured and explainable
- accept/reject outcome is persisted and reportable

---

## Phase 7 - One-To-Many Negotiation

### Goal

Evolve from one company vs one candidate to one initiator vs multiple participants.

### Product changes

- shared base negotiation
- per-participant private threads
- public clarification layer
- synchronized rounds

### Implementation slices

1. define negotiation template instance vs participant instance
2. isolate private state per participant
3. add public RFI or clarification surface
4. add admin overview across participants

### Major architecture consequence

This is the phase where file-backed persistence may become too limiting.
Prepare for a database-backed repository here, not earlier.

### Acceptance criteria

- one base negotiation can spawn multiple participant negotiations
- private and public clarifications stay separate
- admin can compare progress without leaking identities

---

## Phase 8 - Progressive Selection

### Goal

Support narrowing the field across rounds.

### Product changes

- internal suitability signals
- internal-only elimination decisions
- no public rankings

### Implementation slices

1. define internal evaluation summary
2. define elimination event model
3. remove excluded participants from later rounds
4. preserve audit history

### Acceptance criteria

- excluded parties stop receiving future round access
- internal decisions are reviewable
- no participant-facing ranking leaks

---

## Phase 9 - Structured Comparison

### Goal

Compare heterogeneous offers beyond price.

### Product changes

- comparison matrix
- common vs missing vs divergent topics
- structured support for decision makers

### Implementation slices

1. define comparison view model
2. map current structured topics into matrix form
3. highlight missing or implicit items
4. support internal decision summaries

### Acceptance criteria

- at least partially heterogeneous offers can be compared side-by-side
- missing data is explicit
- comparison stays readable to non-technical users

---

## Phase 10 - Document-Centric Negotiation

### Goal

Use uploaded documents as inputs without losing structure.

### Product changes

- document upload
- assisted extraction
- suggested topics from documents

### Implementation slices

1. file ingestion pipeline
2. extraction summary model
3. review-and-confirm extracted topics
4. attach extracted structure to negotiation state

### Acceptance criteria

- documents enrich the negotiation structure
- raw documents do not replace the structured negotiation layer

---

## Phase 11+ Platform Expansion

These phases should remain explicitly post-MVP platform work:

- Phase 11: multi-vertical templates
- Phase 12: semantic normalization
- Phase 13: multilingual comparison
- Phase 14: meta-negotiation intelligence

These should not enter implementation until the one-to-many and comparison layers are proven.

---

## Recommended Build Order

## Now

1. Finish Phase 1 gaps
2. Implement Phase 2 RFI
3. Implement Phase 3 controlled dynamic structure
4. Add Phase 5 reconsideration before full scheduling complexity

## Next

1. Implement Phase 4 scheduling
2. Implement Phase 6 last call

## Later

1. Implement Phase 7 one-to-many
2. Implement Phase 8 progressive selection
3. Implement Phase 9 structured comparison

## Much later

1. Documents
2. Multi-vertical templates
3. Semantic normalization
4. Multilingual support
5. Meta-insights

---

## Suggested Epics For The Near Term

## Epic A - Deal breakers and range model

### Why

The long-range roadmap references them repeatedly, but the current app only partially reflects them.

### Deliverables

- structured range support per major topic
- explicit deal breaker flags
- validation rules for incompatibility

### Blocks

- reconsideration pause
- last call eligibility

---

## Epic B - RFI engine

### Why

This is the first real semantic step that changes the quality of the workflow.

### Deliverables

- RFI model
- RFI generation
- RFI response UX
- unresolved-RFI gating

### Blocks

- meaningful round 2
- early semantic alignment

---

## Epic C - Topic hierarchy

### Why

Dynamic structure needs a more formal model than the current flat dynamic topics list.

### Deliverables

- macro topic
- topic
- subtopic
- weight
- deal breaker

### Blocks

- structured comparison
- arbitration

---

## Epic D - Workflow states expansion

### Why

The roadmap requires richer states than editing/review/closed.

### Deliverables

- draft
- submitted
- review
- paused
- closed
- optional last-call

### Blocks

- scheduling
- reconsideration
- multi-party orchestration

---

## Definition Of Ready For Implementation

A feature or phase is ready only if it has:

- user-visible goal
- data model impact
- UI touchpoints
- validation rules
- report impact
- acceptance criteria
- tests to add

If one of these is missing, the work should be refined before implementation starts.

---

## Suggested Ticket Template

Use this structure when converting a phase slice into implementation tasks:

### Title

Short imperative title.

### Why

Business or workflow reason.

### Product behavior

What the user can now do.

### Engineering changes

- backend or core logic
- UI changes
- validation
- report changes

### Acceptance criteria

- explicit observable outcomes

### Tests

- unit tests
- flow tests

### Out of scope

- what this ticket must not expand into

---

## Immediate Next Ticket Candidates

These are the most implementation-ready next tickets from the roadmap:

1. Add structured deal breakers and topic ranges to the current state model.
2. Introduce RFI objects and a round-1 clarification step.
3. Block round-2 progression on unresolved blocking RFIs.
4. Replace flat dynamic topics with controlled topic/subtopic entities.
5. Add reconsideration pause state triggered by incompatible deal breakers.

---

## Final Note

This document is not a second product vision.
It is the bridge between vision and implementation.

Use the long-range roadmap to decide direction.
Use this implementation roadmap to decide what to build next.
