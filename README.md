# mvp-negotiation-ai

Negotiation MVP for a human-in-the-loop hiring workflow.

## Current architecture

- `company_app.py`, `candidate_app.py`, and `admin_app.py` are the canonical Streamlit entrypoints.
- `app/` is preserved as a legacy prototype and is no longer the primary workflow surface.
- `core/` contains the shared domain, storage, validation, LLM, and report logic.
- Session state is persisted per session in `data/<session_id>.json`.

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
- `NEGOTIATION_DATA_DIR` optional override for session JSON storage
- `NEGOTIATION_SESSION_ID` optional fallback session ID when the UI does not provide one

## Session model

Each role-based app exposes a `Session ID` field in the sidebar. All participants must use the same value to collaborate on the same negotiation.

- New browser sessions get a generated session ID to reduce accidental collisions.
- The sidebar shows a copy/share-friendly session value and the backing file path.
- Sharing the page URL with `?session=<id>` keeps everyone on the same negotiation.

## Core modules

- `core/workflow.py`: phase labels, default state, and workflow constants.
- `core/repository.py`: repository contract plus the file-backed session repository.
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
