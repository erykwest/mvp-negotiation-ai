# PRD MVP

## 1. Product Name
Negotiation Assistant — Recruiting MVP

## 2. Purpose
Build a browser-based MVP that demonstrates a structured negotiation between two parties:
- Company
- Candidate

The MVP must prove that the system can:
1. collect separate inputs from each party;
2. structure the negotiation by sections and topics;
3. capture priority and deal breaker signals;
4. run readable rounds;
5. support human intervention between rounds;
6. produce a final report that is understandable and auditable.

## 3. Product Positioning
This product is not an autonomous decision-maker.
It is a workflow and structuring engine that helps humans negotiate with more clarity, less ambiguity, and better traceability.

## 4. Scope of This MVP
### Included
- Single use case: recruiting
- Two parties only
- Browser-based UI
- Separate apps/views for company, candidate, admin
- Structured negotiation template
- Round-based flow:
  - Round 1: Alignment
  - Round 2: Requests
  - Round 3: Agreement
  - Round 4: Last Call (optional)
- Priority scale 1–5
- Deal breaker yes/no
- Shared round reports
- Human-in-the-loop between rounds
- Final negotiation summary

### Excluded
- Multi-supplier or multi-candidate parallel negotiations
- Real semantic normalization across complex documents
- Advanced scheduling
- Real ATS / CRM integrations
- Full procurement mode
- Real multilingual support
- Automatic arbitration outside controlled last call

## 5. Core User Story
As a company or candidate,
I want to prepare my negotiation inputs privately,
compare them through a structured round flow,
and receive a readable output,
so that I can move toward an informed human decision.

## 6. Main Actors
### Company
Represents the employer side.

### Candidate
Represents the applicant side.

### Admin
Runs the process, triggers rounds, reviews outputs, and produces the shared report.

## 7. Negotiation Model
The negotiation is organized as:
- sections
- topics
- per-party values and preferences
- round outputs
- final summary

Each topic may contain:
- label
- description
- value type
- current value
- preferred value
- min acceptable
- max acceptable
- priority (1–5)
- deal breaker (true/false)
- notes

## 8. Initial Recruiting Sections
The recruiting template starts with these sections:
1. Role & Responsibilities
2. Compensation
3. Work Mode
4. Benefits
5. Tools & Equipment

## 9. Privacy Model
The MVP must clearly separate:
- private party inputs
- shared round outputs

Private inputs include, at minimum:
- internal priorities
- private acceptable ranges
- private notes
- negotiation intent

Shared outputs include, at minimum:
- aligned topics
- ambiguities
- RFI items
- compatible points
- incompatible points
- proposed compromise language
- final summary

Rule:
The system must not expose one party’s hidden priorities or reserved thresholds directly to the other party.

## 10. Round Logic
### Round 1 — Alignment
Goal:
reduce misunderstanding and identify ambiguities.

Outputs:
- aligned topics
- ambiguous topics
- missing information
- RFI list
- topic structure validated for later rounds

Rules:
- topic additions are allowed only here
- new topics must be normalized into the structured model
- after the round, humans can edit values and respond to RFIs

### Round 2 — Requests
Goal:
express positions, requests, trade-offs, and preliminary concessions.

Outputs:
- topic-by-topic request map
- compatibility signals
- incompatible points
- preliminary compromise proposal

Rules:
- no new structural topics unless treated as exceptional RFI
- humans can recalibrate priorities and positions after the round

### Round 3 — Agreement
Goal:
stabilize a near-final proposal.

Outputs:
- draft agreement
- closed points
- open residual points
- deal breaker status
- likely outcome

Rules:
- no new topics
- only limited adjustments
- system should converge or explain why it cannot

### Round 4 — Last Call
Goal:
attempt one final structured recovery when the distance is small.

Outputs:
- final compromise proposal
- final no-deal explanation
- accept/reject decision basis

Rules:
- optional
- only one extra iteration
- only for residual open points
- not available if structural deal breakers are unresolved

## 11. Human-in-the-Loop Requirements
After each round:
- the round stops;
- users can review the output;
- users can modify allowed inputs;
- admin explicitly advances the process.

This is a workflow, not an uninterrupted chatbot loop.

## 12. State Model
Suggested states:
- Draft
- Preparation
- Round 1 Active
- Awaiting Review
- Round 2 Active
- Awaiting Review
- Round 3 Active
- Last Call
- Preliminary Agreement
- No Deal
- Archived

## 13. UX Requirements
The MVP should feel simple and readable.
Priority rules:
1. clarity over sophistication;
2. explicit structure over hidden magic;
3. understandable reports over complex scoring.

Minimum expectations:
- users understand what round they are in;
- users understand what is private vs shared;
- users understand what changed from the previous round;
- users understand why a topic is blocked.

## 14. Functional Requirements
### FR-001 Separate party input
Company and candidate must provide inputs separately.

### FR-002 Structured template
The negotiation must use a recruiting template with predefined sections and topics.

### FR-003 Topic attributes
Each topic must support priority and deal breaker fields.

### FR-004 Round execution
Admin must be able to trigger round processing in order.

### FR-005 Shared reports
Each round must produce a readable shared report.

### FR-006 Human review
The process must pause between rounds for human review and edits.

### FR-007 Topic governance
Topic additions are allowed only until the end of Round 1.

### FR-008 Final summary
The system must produce a final summary of agreement, near-agreement, or no-deal.

## 15. Non-Functional Requirements
- Readable markdown/json-oriented internal structure
- Deterministic enough for demo use
- Easy to inspect and debug
- Easy for external LLMs and coding agents to understand
- Auditable and explainable outputs

## 16. Success Criteria
The MVP is successful if a demo can clearly show:
1. two parties entering private negotiation data;
2. a structured round flow;
3. ambiguity detection and RFI in round 1;
4. topic-level requests and incompatibilities in round 2;
5. a draft agreement or motivated no-deal in round 3/4;
6. a final report that a human can read without extra explanation.