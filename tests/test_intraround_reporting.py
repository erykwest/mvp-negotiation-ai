from core.report import build_report
from core.validation import validate_review_readiness, validate_report_inputs
from tests.helpers import build_state


def _build_negotiation_result(loop: dict | None = None) -> dict:
    result = {
        'company': 'Company is aligned on compensation and timing.',
        'candidate': 'Candidate is aligned on benefits and flexibility.',
        'summary': 'The round converged on the main open items.',
    }
    if loop is not None:
        result['loop'] = loop
    return result


def test_validate_review_readiness_allows_negotiation_result_without_loop():
    state = build_state(current_phase='NEGOTIATION', status='review')

    errors = validate_review_readiness(state, 'NEGOTIATION', _build_negotiation_result())

    assert errors == []


def test_validate_review_readiness_accepts_negotiation_loop_artifact():
    state = build_state(current_phase='NEGOTIATION', status='review')
    result = _build_negotiation_result(
        {
            'enabled': True,
            'phase': 'NEGOTIATION',
            'status': 'completed',
            'stop_reason': 'converged',
            'agreements': ['Base salary range aligned'],
            'open_issues': ['Notice period still open'],
            'suggested_rfis': [
                {
                    'target_side': 'candidate',
                    'scope': 'benefits',
                    'question': 'Please clarify relocation support.',
                }
            ],
        }
    )

    errors = validate_review_readiness(state, 'NEGOTIATION', result)

    assert errors == []


def test_validate_review_readiness_rejects_malformed_negotiation_loop_artifact():
    state = build_state(current_phase='NEGOTIATION', status='review')
    result = _build_negotiation_result(loop='not-a-dict')

    errors = validate_review_readiness(state, 'NEGOTIATION', result)

    assert 'malformed intra-round loop artifact' in ' '.join(errors)


def test_validate_report_inputs_accepts_negotiation_loop_artifact():
    state = build_state(current_phase='NEGOTIATION', status='review')
    results = {'NEGOTIATION': _build_negotiation_result({'status': 'completed', 'agreements': []})}

    errors = validate_report_inputs(state, results)

    assert errors == []


def test_build_report_omits_loop_section_when_result_has_no_loop():
    state = build_state(current_phase='NEGOTIATION', status='review')
    results = {'NEGOTIATION': _build_negotiation_result()}

    report = build_report(state, results)

    assert '### Intra-round loop' not in report
    assert 'Stop reason:' not in report


def test_build_report_renders_negotiation_loop_concisely():
    state = build_state(current_phase='NEGOTIATION', status='review')
    results = {
        'NEGOTIATION': _build_negotiation_result(
            {
                'enabled': True,
                'phase': 'NEGOTIATION',
                'status': 'completed',
                'stop_reason': 'converged',
                'agreements': ['Base salary range aligned', 'Hybrid work arrangement aligned'],
                'open_issues': ['Notice period still open'],
                'suggested_rfis': [
                    {
                        'target_side': 'candidate',
                        'scope': 'benefits',
                        'question': 'Please clarify relocation support.',
                    }
                ],
            }
        )
    }

    report = build_report(state, results)

    assert '### Intra-round loop' in report
    assert '- Status: `completed`' in report
    assert '- Stop reason: `converged`' in report
    assert '- Agreements: Base salary range aligned, Hybrid work arrangement aligned' in report
    assert '- Open issues: Notice period still open' in report
    assert '- Suggested RFIs:' in report
    assert '  - candidate | benefits: Please clarify relocation support.' in report
