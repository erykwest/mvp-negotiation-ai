import json

import pytest

from core.intraround_engine import (
    ANALYST_ACTION_CONTINUE,
    DEFAULT_MAX_CYCLES,
    INTRAROUND_PHASE,
    STOP_REASON_CONVERGED,
    STOP_REASON_LLM_ERROR,
    STOP_REASON_MAX_CYCLES,
    run_intraround_loop,
)
from core.llm_client import BaseLLMClient, LLMRequest
from tests.helpers import build_state, build_topic_tree


class QueuedClient(BaseLLMClient):
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def complete(self, request: LLMRequest) -> str:
        self.prompts.append(request.prompt)
        if not self.responses:
            raise AssertionError('Unexpected LLM call with no queued response.')
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False)


def test_intraround_loop_builds_cycles_and_filters_phase_unsafe_suggestions():
    state = build_state(
        topic_tree=build_topic_tree(include_round2_subtopic=True, round2_creator='candidate'),
        current_phase=INTRAROUND_PHASE,
    )
    client = QueuedClient(
        [
            _json(
                {
                    'message': 'Company clarifies budget and timing.',
                    'agreements': ['Base salary range is acceptable.'],
                    'open_issues': ['Notice period remains open.'],
                    'proposals': ['Clarify bonus timing.'],
                }
            ),
            _json(
                {
                    'message': 'Candidate confirms willingness to proceed.',
                    'agreements': ['Hybrid model is acceptable.'],
                    'open_issues': ['Bonus timing still open.'],
                    'proposals': ['Ask for a signing bonus clarification.'],
                }
            ),
            _json(
                {
                    'action': 'stop',
                    'reason': 'converged',
                    'summary': 'Round 2 reached a stable negotiation posture.',
                    'agreements': ['Base salary range is acceptable.'],
                    'open_issues': ['Need a bonus clarification.'],
                    'suggested_rfis': [
                        {
                            'target_side': 'candidate',
                            'subtopic_id': 'sub-signing-bonus',
                            'subtopic_title': 'Signing bonus',
                            'question': 'Can the signing bonus be paid at signing?',
                        },
                        {
                            'target_side': 'candidate',
                            'subtopic_id': 'sub-base-salary',
                            'subtopic_title': 'Base salary',
                            'question': 'This suggestion should be filtered out.',
                        },
                    ],
                }
            ),
        ]
    )

    loop = run_intraround_loop(state, INTRAROUND_PHASE, client=client)

    assert loop['enabled'] is True
    assert loop['phase'] == INTRAROUND_PHASE
    assert loop['stop_reason'] == STOP_REASON_CONVERGED
    assert loop['status'] == 'completed'
    assert loop['max_cycles'] == DEFAULT_MAX_CYCLES
    assert len(loop['cycles']) == 1
    assert loop['cycles'][0]['analyst_decision']['parsed']['action'] == 'stop'
    assert len(loop['suggested_rfis']) == 1
    assert loop['suggested_rfis'][0]['target_side'] == 'candidate'
    assert loop['suggested_rfis'][0]['subtopic_id'] == 'sub-signing-bonus'
    assert 'Return JSON only.' in client.prompts[0]
    assert 'output_schema' in client.prompts[2]


def test_intraround_loop_is_bounded_by_max_cycles():
    state = build_state(
        topic_tree=build_topic_tree(include_round2_subtopic=True, round2_creator='candidate'),
        current_phase=INTRAROUND_PHASE,
    )
    responses: list[str] = []
    for cycle in range(2):
        responses.extend(
            [
                _json({'message': f'Company cycle {cycle + 1}', 'agreements': [], 'open_issues': [], 'proposals': []}),
                _json({'message': f'Candidate cycle {cycle + 1}', 'agreements': [], 'open_issues': [], 'proposals': []}),
                _json(
                    {
                        'action': ANALYST_ACTION_CONTINUE,
                        'reason': 'max_cycles',
                        'summary': f'Cycle {cycle + 1} still needs more discussion.',
                        'agreements': [],
                        'open_issues': [],
                        'suggested_rfis': [],
                    }
                ),
            ]
        )

    client = QueuedClient(responses)
    loop = run_intraround_loop(state, INTRAROUND_PHASE, client=client, max_cycles=2)

    assert loop['stop_reason'] == STOP_REASON_MAX_CYCLES
    assert loop['status'] == 'completed'
    assert len(loop['cycles']) == 2
    assert len(client.prompts) == 6
    assert loop['draft_summary'] == 'Cycle 2 still needs more discussion.'


def test_intraround_loop_rejects_non_negotiation_phase():
    state = build_state(current_phase='ALIGNMENT')

    with pytest.raises(ValueError, match='only supported for NEGOTIATION'):
        run_intraround_loop(state, 'ALIGNMENT')


def test_intraround_loop_reports_llm_error_on_invalid_json():
    state = build_state(
        topic_tree=build_topic_tree(include_round2_subtopic=True, round2_creator='candidate'),
        current_phase=INTRAROUND_PHASE,
    )
    client = QueuedClient(
        [
            _json({'message': 'Company is fine.', 'agreements': [], 'open_issues': [], 'proposals': []}),
            _json({'message': 'Candidate is fine.', 'agreements': [], 'open_issues': [], 'proposals': []}),
            'not-json',
        ]
    )

    loop = run_intraround_loop(state, INTRAROUND_PHASE, client=client)

    assert loop['status'] == 'error'
    assert loop['stop_reason'] == STOP_REASON_LLM_ERROR
    assert 'valid JSON' in loop['error']
    assert len(loop['cycles']) == 1
    assert 'not-json' in loop['cycles'][0]['analyst_decision']['raw']
