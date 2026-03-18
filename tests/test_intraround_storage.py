from core import storage
from core.repository import FileSessionRepository
from core.workflow import WORKFLOW_STATE_ROUND_OPEN
from tests.helpers import build_state


def configure_repo(tmp_path, monkeypatch):
    repository = FileSessionRepository(tmp_path)
    monkeypatch.setattr(storage, '_repository', repository)
    return repository


def build_negotiation_result(loop: dict | None = None) -> dict:
    result = {
        'company': 'Company is aligned.',
        'candidate': 'Candidate is aligned.',
        'summary': 'The round converged.',
    }
    if loop is not None:
        result['loop'] = loop
    return result


def build_loop_artifact() -> dict:
    return {
        'enabled': True,
        'phase': 'NEGOTIATION',
        'status': 'completed',
        'stop_reason': 'converged',
        'agreements': ['Base salary aligned'],
        'open_issues': ['Notice period still open'],
        'suggested_rfis': [
            {
                'target_side': 'candidate',
                'scope': 'benefits',
                'question': 'Please clarify relocation support.',
            }
        ],
    }


def test_reset_workflow_clears_shared_output_results_and_snapshots(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = 'reset-loop'
    storage.save_state(build_state(current_phase='NEGOTIATION', status=WORKFLOW_STATE_ROUND_OPEN), session_id=session_id)
    storage.save_round_result('NEGOTIATION', build_negotiation_result(build_loop_artifact()), session_id=session_id)

    pre_reset = storage.load_state(session_id)
    assert pre_reset['results']['NEGOTIATION']['loop']['status'] == 'completed'
    assert pre_reset['shared_outputs']['results']['NEGOTIATION']['loop']['status'] == 'completed'
    assert storage.get_latest_loop_artifact(pre_reset, 'NEGOTIATION') is not None

    storage.reset_workflow(session_id=session_id)
    post_reset = storage.load_state(session_id)

    assert post_reset['results'] == {}
    assert post_reset['shared_outputs']['results'] == {}
    assert post_reset['round_snapshots'] == []
    assert storage.get_latest_loop_artifact(post_reset, 'NEGOTIATION') is None


def test_rewind_phase_prunes_reopened_results_and_snapshot_loop_artifacts(tmp_path, monkeypatch):
    configure_repo(tmp_path, monkeypatch)
    session_id = 'rewind-loop'
    storage.save_state(build_state(current_phase='ALIGNMENT', status=WORKFLOW_STATE_ROUND_OPEN), session_id=session_id)
    storage.save_round_result('ALIGNMENT', build_negotiation_result(), session_id=session_id)
    storage.advance_phase(session_id=session_id)
    storage.save_round_result('NEGOTIATION', build_negotiation_result(build_loop_artifact()), session_id=session_id)
    storage.advance_phase(session_id=session_id)

    pre_rewind = storage.load_state(session_id)
    assert pre_rewind['workflow']['current_phase'] == 'CLOSING'
    assert storage.get_latest_loop_artifact(pre_rewind, 'NEGOTIATION') is not None
    assert storage.load_round_snapshots(session_id, phase='NEGOTIATION')

    updated = storage.rewind_phase(session_id=session_id)
    post_rewind = storage.load_state(session_id)

    assert updated['workflow']['current_phase'] == 'NEGOTIATION'
    assert updated['workflow']['status'] == WORKFLOW_STATE_ROUND_OPEN
    assert 'NEGOTIATION' not in post_rewind['results']
    assert 'CLOSING' not in post_rewind['results']
    assert 'NEGOTIATION' not in post_rewind['shared_outputs']['results']
    assert 'CLOSING' not in post_rewind['shared_outputs']['results']
    assert storage.load_round_snapshots(session_id, phase='NEGOTIATION') == []
    assert storage.get_latest_loop_artifact(post_rewind, 'NEGOTIATION') is None
