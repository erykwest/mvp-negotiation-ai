from core.repository import FileSessionRepository


def test_load_new_session_writes_default_state_without_recursive_save(tmp_path, monkeypatch):
    repository = FileSessionRepository(tmp_path)

    def fail_save(*args, **kwargs):
        raise AssertionError("load() should not recurse into save() for a new session.")

    monkeypatch.setattr(repository, "save", fail_save)

    state = repository.load("fresh-session")

    assert state["session_id"] == "fresh-session"
    assert repository.session_file("fresh-session").exists()
    assert state["workflow"]["current_phase"] == "ALIGNMENT"


def test_load_corrupt_session_rewrites_default_state_without_recursive_save(tmp_path, monkeypatch):
    repository = FileSessionRepository(tmp_path)
    session_file = repository.session_file("broken-session")
    session_file.write_text("{not-json", encoding="utf-8")

    def fail_save(*args, **kwargs):
        raise AssertionError("load() should not recurse into save() when repairing a corrupt session.")

    monkeypatch.setattr(repository, "save", fail_save)

    state = repository.load("broken-session")

    assert state["session_id"] == "broken-session"
    assert session_file.exists()
    assert session_file.with_suffix(".corrupt.json").exists()
