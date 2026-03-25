# mvp-negotiation-ai

Negotiation MVP for a human-in-the-loop hiring workflow.

## Current architecture

- `company_app.py`, `candidate_app.py`, and `admin_app.py` are the canonical Streamlit entrypoints.
- `app/` is preserved as a legacy prototype and is no longer the primary workflow surface.
- `core/` contains the shared domain, storage, validation, LLM, and report logic.
- Session state is persisted behind a repository contract; the default backend is local JSON files in `data/<session_id>.json`, and a Supabase/Postgres backend is also supported.
- Negotiation structure is template-driven from `product/templates/negotiation_template_recruiting.json`.
- Shared structure and private party inputs are persisted separately, with a merged admin/runtime view rebuilt on load.
- Each completed round appends an immutable snapshot of the negotiation boundary state for later inspection.
- Workflow state is explicit and normalized on load: `ROUND_OPEN -> ROUND_REVIEW -> ROUND_OPEN/COMPLETED`.

## Run locally

Use the repo virtualenv for all commands in this project:

```powershell
.\.venv\Scripts\python.exe --version
```

Install dependencies into the repo venv if needed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Canonical Streamlit commands:

```powershell
.\.venv\Scripts\python.exe -m streamlit run company_app.py --server.port 8501
.\.venv\Scripts\python.exe -m streamlit run candidate_app.py --server.port 8502
.\.venv\Scripts\python.exe -m streamlit run admin_app.py --server.port 8503
```

Optional launcher:

```powershell
.\run_app.ps1 company
.\run_app.ps1 candidate
.\run_app.ps1 admin
```

Required environment variables:

- `GROQ_API_KEY` for live LLM-backed negotiation rounds
- `NEGOTIATION_STORAGE_BACKEND` optional backend selector: `file` (default) or `supabase`
- `NEGOTIATION_DATA_DIR` optional override for local JSON storage when using the `file` backend
- `NEGOTIATION_SESSION_ID` optional fallback session ID when the UI does not provide one
- `SUPABASE_DB_URL` or `DATABASE_URL` required when using the `supabase` backend
- `NEGOTIATION_DB_TABLE` optional override for the Postgres table name; defaults to `negotiation_sessions`

## Session model

Each role-based app exposes a `Session ID` field in the sidebar. All participants must use the same value to collaborate on the same negotiation.

- New browser sessions get a generated session ID to reduce accidental collisions.
- The sidebar shows a copy/share-friendly session value and backend-agnostic storage messaging.
- Sharing the page URL with `?session=<id>` keeps everyone on the same negotiation.
- Company and candidate apps load side-specific views that hide counterparty priorities, deal breakers, notes, and raw positions.

## Core modules

- `core/workflow.py`: phase labels, workflow state machine, default state, and transition helpers.
- `core/repository.py`: repository contract plus the file-backed session repository.
- `core/postgres_repository.py`: Supabase/Postgres-backed implementation of the same repository contract.
- `core/storage.py`: compatibility facade for state mutations and workflow actions.
- `core/validation.py`: state, review, transition, and report validation.
- `core/llm_client.py`: provider abstraction and Groq implementation.
- `core/negotiation.py`: prompt building, round orchestration, and round error collection.
- `core/report.py`: markdown report generation.

## Tests

Run the full suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The repository includes unit and integration-style tests for:

- storage and workflow transitions
- prompt generation and round orchestration
- report generation
- corrupt session recovery and session isolation
- review gating for dynamic topics and LLM failures
- the intended happy-path negotiation flow

## Notes

- `prompts/`, `product/`, and many files under `docs/` still contain placeholders and should not be treated as runtime sources of truth unless they are wired into the application.
- The current persistence boundary to preserve for future backends is the repository contract: `load(session_id)` and `save(session_id, state)`.
- Supabase setup details live in `docs/supabase_setup.md`, and the one-shot migration helper from local JSON files lives in `scripts/migrate_sessions_to_supabase.py`.
