# Backlog

## BL-001 Core round flow
Priority: P0  
Status: todo

Implement canonical round execution:
- Round 1 Alignment
- Round 2 Requests
- Round 3 Agreement
- Round 4 Last Call (optional)

Acceptance criteria:
- rounds are triggered in order;
- each round generates an output artifact;
- admin controls progression.

## BL-002 Recruiting template loading
Priority: P0  
Status: todo

Load negotiation structure from `product/templates/negotiation_template_recruiting.json`.

Acceptance criteria:
- sections and topics come from template;
- no hardcoded duplicated structures across apps.

## BL-003 Shared vs private data separation
Priority: P0  
Status: todo

Separate:
- private party inputs
- shared report outputs

Acceptance criteria:
- hidden ranges and priorities are not shown to the counterparty;
- reports expose only allowed shared fields.

## BL-004 Round reports
Priority: P0  
Status: todo

Create a standard report schema for each round.

Acceptance criteria:
- same shared format for both parties;
- includes aligned points, ambiguous points, open issues, and next-step guidance.

## BL-005 Preparation privacy fix
Priority: P0  
Status: todo

Prevent party A from seeing party B preparation inputs before the correct phase.

Acceptance criteria:
- refresh on company/candidate app does not leak counterparty preparation data;
- visibility obeys round/state rules only.

## BL-006 Topic edit/delete in preparation
Priority: P0  
Status: todo

Allow users to edit or delete topics they added during preparation and Round 1 review.

Acceptance criteria:
- added topics can be modified;
- added topics can be removed before round lock;
- deletion is blocked after structural freeze.

## BL-007 Round snapshot model
Priority: P0  
Status: todo

Persist a snapshot of the negotiation state at each round boundary.

Acceptance criteria:
- previous round state can be inspected;
- later edits do not overwrite history;
- reports can reference round-specific data.

## BL-008 RFI engine for Round 1
Priority: P1  
Status: todo

Generate structured RFI items when:
- a field is missing;
- a value is ambiguous;
- units are mismatched;
- a topic lacks enough parameters.

Acceptance criteria:
- RFIs are grouped by responsible party;
- RFI responses can be applied before Round 2.

## BL-009 Topic freeze governance
Priority: P1  
Status: todo

After Round 1, new structural topics should be blocked except exceptional admin-approved cases.

Acceptance criteria:
- system prevents casual topic creation after Round 1;
- any exception is explicit and logged.

## BL-010 Compatibility view in Round 2
Priority: P1  
Status: todo

Add topic-level classification:
- compatible
- partially compatible
- incompatible
- deal-breaker risk

Acceptance criteria:
- every major topic gets one classification;
- output is visible in shared report.

## BL-011 Draft agreement generation
Priority: P1  
Status: todo

Produce a draft agreement in Round 3 from the latest aligned structure.

Acceptance criteria:
- closed points are separated from open points;
- unresolved blockers are explicit.

## BL-012 Last call guardrails
Priority: P1  
Status: todo

Implement last call only when:
- residual distance is small;
- no structural deal breaker remains unresolved.

Acceptance criteria:
- last call is optional;
- only one additional iteration is allowed.

## BL-013 Admin state machine
Priority: P1  
Status: todo

Introduce explicit negotiation states.

Acceptance criteria:
- state transitions are controlled;
- UI shows current state clearly;
- invalid transitions are blocked.

## BL-014 Template documentation
Priority: P1  
Status: todo

Document template schema used by product templates.

Acceptance criteria:
- external LLMs can infer required keys and allowed value types.

## BL-015 Prompt hardening
Priority: P1  
Status: todo

Replace placeholder prompts with round-specific operational prompts.

Acceptance criteria:
- prompts describe goal, allowed knowledge, forbidden leakage, and expected output.

## BL-016 Final report export
Priority: P2  
Status: todo

Generate a final structured summary for demo use.

Acceptance criteria:
- agreement / near-agreement / no-deal is explicit;
- topic summary is readable.

## BL-017 Audit log
Priority: P2  
Status: todo

Log major actions:
- round execution
- human edits
- state transitions
- topic additions/removals

Acceptance criteria:
- change trail is inspectable.

## BL-018 Controlled dynamic topics
Priority: P2  
Status: future

Allow semi-dynamic topic expansion within governance rules.

Acceptance criteria:
- max limits exist;
- readability is preserved.

## BL-019 Multi-negotiation support
Priority: P3  
Status: future

Support multiple distinct negotiations in parallel.

## BL-020 Procurement vertical
Priority: P3  
Status: future

Add a second template after recruiting is stable.