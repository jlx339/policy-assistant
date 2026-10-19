"""Catches inflated metrics, missing review claims, and silent query failures."""
import pytest
from policy_assistant.evaluate import retrieval_metrics, summarize, evaluate_case, validate_labels, review_fingerprint


def test_retrieval_metrics_use_unique_ids_and_actual_return_count():
    assert retrieval_metrics(['a', 'c'], {'a', 'b'}) == {'recall_at_4':0.5, 'precision_at_4':0.5}
    assert retrieval_metrics(['a', 'a', 'c'], {'a', 'b'}) == {'recall_at_4':0.5, 'precision_at_4':0.5}
    assert retrieval_metrics([], {'a'}) == {'recall_at_4':0.0, 'precision_at_4':0.0}


def row(qid='Q01', status='answer', expected='answer', recall=0.5):
    return {'id':qid, 'mode':'hybrid', 'expected_status':expected, 'status':status,
            'answer':'Example [a]', 'citation_ids':['a'], 'hits':[{'chunk':{'id':'a'}}],
            'elapsed_seconds':2.0, 'error':None,
            'retrieval':{'recall_at_4':recall, 'precision_at_4':0.5},
            'required_sources_retrieved':True}


def test_unanswerable_cases_excluded_from_retrieval_macro_and_zero_claims_undefined():
    rows = [row(), row('Q02', status='insufficient', expected='insufficient', recall=0.0)]
    result = summarize(rows, {})
    assert result['recall_at_4'] == 0.5
    assert result['faithfulness'] is None
    assert result['reviewed_answers'] == 0
    assert result['answer_coverage'] == 0.5


def test_supported_claims_weighted_by_claim_counts():
    rows = [row(), row('Q02')]
    reviews = {'hybrid:Q01':{'supported_claims':2, 'total_claims':2, 'correct':True, 'citation_support':True},
               'hybrid:Q02':{'supported_claims':1, 'total_claims':2, 'correct':False, 'citation_support':False}}
    for r in rows:
        reviews[f'{r["mode"]}:{r["id"]}']['answer_hash'] = review_fingerprint(r)
    result = summarize(rows, reviews)
    assert result['faithfulness'] == 0.75
    assert result['correct_answer_rate'] == 0.5
    assert result['reviewed_answers'] == 2


def test_incomplete_review_does_not_claim_overall_faithfulness():
    rows = [row(), row('Q02')]
    reviews = {'hybrid:Q01':{'supported_claims':2, 'total_claims':2, 'correct':True, 'citation_support':True}}
    assert summarize(rows, reviews)['faithfulness'] is None


def test_impossible_review_counts_rejected():
    with pytest.raises(ValueError, match='claim'):
        summarize([row()], {'hybrid:Q01':{'supported_claims':3, 'total_claims':2, 'answer_hash':review_fingerprint(row())}})


def test_pipeline_exception_is_kept_as_failed_case():
    class Broken:
        def run(self, question, mode):
            raise RuntimeError('secret provider payload')
    case={'id':'Q01','question':'Example?', 'category':'direct', 'expected_status':'answer', 'required_source_urls':[]}
    result=evaluate_case(case, Broken(), 'hybrid', {'Q01':['a']})
    assert result['status']=='error' and result['retrieval']['recall_at_4']==0
    assert 'secret' not in str(result)


def test_labels_must_match_snapshot_and_frozen_questions():
    with pytest.raises(ValueError, match='snapshot|labels'):
        validate_labels({'reviewed':False}, [], [], 'current')


def test_old_human_review_cannot_score_a_changed_answer():
    original = row()
    original['answer'] = 'The original source-supported answer. [a]'
    reviews = {'hybrid:Q01':{'supported_claims':2, 'total_claims':2, 'correct':True,
                              'citation_support':True}}
    changed = {**original, 'answer':'An unrelated unsupported answer. [a]'}
    assert summarize([changed], reviews)['faithfulness'] is None


def test_review_binding_changes_with_answer_or_evidence():
    from policy_assistant.evaluate import review_fingerprint
    original = row()
    original['question'] = 'Original question?'
    original['hits'] = [{'chunk':{'id':'a', 'text':'Original evidence'}}]
    signed = {'supported_claims':1, 'total_claims':1, 'correct':True, 'citation_support':True,
              'answer_hash':review_fingerprint(original)}
    assert summarize([original], {'hybrid:Q01':signed})['faithfulness'] == 1.0
    assert summarize([{**original,'answer':'Changed claim [a]'}], {'hybrid:Q01':signed})['faithfulness'] is None
    changed_evidence = {**original, 'hits':[{'chunk':{'id':'a', 'text':'Changed evidence'}}]}
    assert summarize([changed_evidence], {'hybrid:Q01':signed})['faithfulness'] is None


def test_evaluation_checkpoints_and_resumes_without_repeating_queries(tmp_path, monkeypatch):
    import policy_assistant.evaluate as module
    import json
    calls, waits = [], []
    def fake_case(case, pipe, mode, relevant):
        calls.append((mode, case['id']))
        if case['id'] == 'Q02':
            raise KeyboardInterrupt()
        return {'mode':mode, 'id':case['id']}
    monkeypatch.setattr(module, 'evaluate_case', fake_case)
    monkeypatch.setattr(module.time, 'sleep', waits.append)
    payload = {'rows':[]}
    cases = [{'id':'Q01'}, {'id':'Q02'}]
    path = tmp_path / 'results.json'
    with pytest.raises(KeyboardInterrupt):
        module.run_cases(cases, ['dense'], None, {}, payload, path, 65)
    saved = json.loads(path.read_text())
    assert saved['rows'] == [{'mode':'dense', 'id':'Q01'}]
    monkeypatch.setattr(module, 'evaluate_case', lambda case, *args: {'mode':'dense','id':case['id']})
    module.run_cases(cases, ['dense'], None, {}, saved, path, 65)
    assert len(saved['rows']) == 2
    assert waits == [65,65]
