# DECISIONS ADR

## ADR-001
### Title
Keep current repository structure and add a strategic documentation layer

### Context
The repository already contains working prototype code and active references.

### Decision
Do not rebuild the repo from scratch.
Add `docs/`, `product/`, `prompts/`, and `tests/` as strategic layers without breaking current code.

### Consequences
- Faster progress
- Less breakage risk
- Temporary coexistence of old and new structure

---

## ADR-002
### Title
MVP use case is recruiting negotiation

### Context
The broader vision is multi-domain negotiation, but MVP needs a narrow and testable use case.

### Decision
Start with company vs candidate negotiation.

### Consequences
- Clearer topic model
- Easier UI
- Easier validation

---

## ADR-003
### Title
MVP supports up to 4 rounds

### Context
Negotiation must converge and not expand indefinitely.

### Decision
Use:
1. Alignment
2. Requests
3. Agreement
4. Last Call (optional)

### Consequences
- Controlled flow
- Easier reporting
- Better UX
