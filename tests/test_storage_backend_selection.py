from core import storage


def test_build_repository_defaults_to_file_backend(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class DummyFileRepository:
        def __init__(self, data_dir):
            captured["data_dir"] = data_dir

    monkeypatch.delenv("NEGOTIATION_STORAGE_BACKEND", raising=False)
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "FileSessionRepository", DummyFileRepository)

    repository = storage._build_repository()

    assert isinstance(repository, DummyFileRepository)
    assert captured["data_dir"] == tmp_path


def test_build_repository_uses_supabase_backend_when_requested(monkeypatch):
    marker = object()

    def fake_postgres_repository():
        return marker

    monkeypatch.setenv("NEGOTIATION_STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(storage, "PostgresSessionRepository", fake_postgres_repository)

    repository = storage._build_repository()

    assert repository is marker


def test_build_repository_accepts_postgres_alias(monkeypatch):
    marker = object()

    def fake_postgres_repository():
        return marker

    monkeypatch.setenv("NEGOTIATION_STORAGE_BACKEND", "postgres")
    monkeypatch.setattr(storage, "PostgresSessionRepository", fake_postgres_repository)

    repository = storage._build_repository()

    assert repository is marker
