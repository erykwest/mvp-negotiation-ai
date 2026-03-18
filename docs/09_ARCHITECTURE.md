# 09 Architecture

## Summary

The Python code is the authoritative implementation source for this repository. Most documentation, prompt assets, and product templates remain placeholders and do not currently drive runtime behavior.

The repository now has one recommended runtime architecture:

- `company_app.py`
- `candidate_app.py`
- `admin_app.py`
- shared logic in `core/`

The older `app/` multi-page Streamlit flow is preserved only as a legacy prototype.

## Runtime map

### UI entrypoints

- `company_app.py` captures shared job context, company position, company priorities, and company-authored dynamic topics.
- `candidate_app.py` captures candidate position, candidate priorities, and candidate-authored dynamic topics.
- `admin_app.py` runs workflow rounds, advances phases, and exports the final report.
- `app/` remains available for reference only and should not be extended as the primary UX.

### Shared modules

- `core/workflow.py` defines workflow phases, labels, and default state.
- `core/repository.py` manages file-backed session persistence.
- `core/storage.py` exposes mutation helpers used by the Streamlit apps.
- `core/validation.py` validates round readiness, workflow transitions, and report inputs.
- `core/llm_client.py` isolates provider communication behind a small client abstraction.
- `core/negotiation.py` builds prompts and orchestrates round execution.
- `core/report.py` builds the final markdown report.

### Persistence model

- State is stored per session in `data/<session_id>.json`.
- Session IDs are user-controlled from the role-based apps and normalized before file writes.
- The repository remains file-backed, but the persistence boundary is now explicit and replaceable.

### LLM integration

- `core/llm_client.py` currently supports Groq as the default provider.
- The app calls the provider through `BaseLLMClient` / `ask_llm(...)`.
- Negotiation orchestration accepts an injected client for testing and future provider portability.

### Workflow transitions

- `ALIGNMENT -> NEGOTIATION -> CLOSING`
- Each completed round moves the workflow into `review`.
- Advancing from negotiation to closing requires all dynamic topics to be answered by both sides.
- Report generation validates state and result completeness before producing output.

## Architectural drift

### Duplicate app surfaces

The repository still contains two UI models:

- canonical role-based apps
- legacy `app/` prototype

This is intentional only as a transition aid. New feature work should target the role-based apps.

### Placeholder assets

The following areas remain mostly documentary or placeholder-only:

- `docs/`
- `prompts/`
- `product/templates/`

These should not be mistaken for active runtime configuration.

### Working tree vs snapshot metadata

Historical snapshot files such as `repo_tree.txt` and `git_tracked.txt` can drift from the live repository. They are auxiliary artifacts, not repository truth.

## Key risks and current mitigations

### Single-process file storage

Risk:
The app still uses local JSON files, which is simple but fragile for concurrent or multi-user production use.

Mitigation:
Storage is now session-aware and isolated behind `FileSessionRepository`.

### UI-to-storage coupling

Risk:
Streamlit forms still operate close to the persisted shape.

Mitigation:
Validation and workflow logic have been separated so a future service layer can replace the thin storage facade incrementally.

### Provider lock-in and thin transport layer

Risk:
Only one provider is implemented today, with limited resilience behavior.

Mitigation:
A client abstraction now isolates transport concerns and supports test injection.

### Testing gaps

Risk:
The repo originally had no effective tests around storage, transitions, prompts, or reports.

Mitigation:
Unit and integration-style tests now cover these core paths.

### Encoding and localization drift

Risk:
Mixed encoding and partially corrupted source strings made the UI harder to maintain.

Mitigation:
Files touched in this refactor were normalized to ASCII-first strings.

## Prioritized roadmap

1. Keep extending only the role-based apps and freeze the legacy `app/` flow except for break/fix maintenance.
2. Introduce a service layer between Streamlit and `core/storage.py` if business rules continue to grow.
3. Replace file persistence with a database-backed repository while preserving the current repository interface.
4. Decide whether prompt assets should become real runtime dependencies or remain documentation; avoid half-connected prompt abstractions.
5. Add stronger provider resilience such as retries, request IDs, and structured response validation.
