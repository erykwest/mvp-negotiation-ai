from core.negotiation import run_single_round
from tests.helpers import build_state


class SequencedClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def complete(self, request):
        self.prompts.append(request.prompt)
        if not self.responses:
            raise AssertionError('Unexpected LLM call')
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_negotiation_round_returns_loop_artifact_and_feeds_final_prompts():
    client = SequencedClient(
        [
            '{"message":"Company cycle 1","agreements":["salary band aligned"],"open_issues":["notice period"],"suggested_rfis":[]}',
            '{"message":"Candidate cycle 1","agreements":["salary band aligned"],"open_issues":["base salary still open"],"suggested_rfis":[]}',
            '{"action":"stop","reason":"converged after one cycle","agreements":["salary band aligned"],"open_issues":["notice period"],"suggested_rfis":[{"target_side":"candidate","scope":"Base salary","question":"Can you confirm the review timing?"}]}',
            'final-company',
            'final-candidate',
            'final-summary',
        ]
    )

    result = run_single_round(build_state(current_phase='NEGOTIATION'), 'NEGOTIATION', client=client)

    assert result['company'] == 'final-company'
    assert result['candidate'] == 'final-candidate'
    assert result['summary'] == 'final-summary'
    assert 'loop' in result
    assert result['loop']['phase'] == 'NEGOTIATION'
    assert result['loop']['status'] == 'completed'
    assert result['loop']['stop_reason'] == 'converged after one cycle'
    assert result['loop']['cycles'][0]['analyst_decision']['action'] == 'stop'
    assert result['loop']['suggested_rfis'][0]['question'] == 'Can you confirm the review timing?'
    assert len(client.prompts) == 6
    assert 'INTRA-ROUND LOOP' in client.prompts[3]
    assert 'Company cycle 1' in client.prompts[3]
    assert 'converged after one cycle' in client.prompts[5]


def test_non_negotiation_rounds_do_not_return_loop_artifact():
    for phase in ('ALIGNMENT', 'CLOSING'):
        client = SequencedClient(['company', 'candidate', 'summary'])

        result = run_single_round(build_state(current_phase=phase), phase, client=client)

        assert result == {'company': 'company', 'candidate': 'candidate', 'summary': 'summary'}
        assert 'loop' not in result
        assert len(client.prompts) == 3


def test_negotiation_loop_failure_still_returns_defensible_round_shape():
    client = SequencedClient(
        [
            RuntimeError('provider unavailable'),
            '{"message":"Candidate cycle 1","agreements":[],"open_issues":[],"suggested_rfis":[]}',
            '{"action":"stop","reason":"converged","agreements":[],"open_issues":[],"suggested_rfis":[]}',
            'final-company',
            'final-candidate',
            'final-summary',
        ]
    )

    result = run_single_round(build_state(current_phase='NEGOTIATION'), 'NEGOTIATION', client=client)

    assert result['company'] == 'final-company'
    assert result['candidate'] == 'final-candidate'
    assert result['summary'] == 'final-summary'
    assert result['loop']['status'] == 'failed'
    assert result['loop']['stop_reason'] == 'llm_error'
    assert len(client.prompts) == 6
