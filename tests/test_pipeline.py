"""Catches unsafe answer acceptance, provider leakage, and fabricated success."""
import pytest
from policy_assistant.models import Chunk, Hit
from policy_assistant.pipeline import Pipeline

CHUNK = Chunk('c123', 'Company laptops must use disk encryption.', 'https://example.com', 'Devices', 'https://example.com#devices')
HIT = Hit(CHUNK, 1.0)
GOOD = {'status': 'answer', 'answer': 'Company laptops must use disk encryption. [c123]', 'citation_ids': ['c123']}


class Client:
    def __init__(self, response=None, verdict=None, fail_verify=False, fail_generate=False):
        self.response = GOOD if response is None else response
        self.verdict = {'supported': True, 'citations_supported': True, 'correct_status': True} if verdict is None else verdict
        self.fail_verify, self.fail_generate = fail_verify, fail_generate
    def generate(self, question, context):
        if self.fail_generate:
            raise RuntimeError('secret-key-in-provider-payload')
        return self.response
    def verify(self, question, context, response):
        if self.fail_verify:
            raise RuntimeError('secret-key-in-provider-payload')
        assert CHUNK.text in context  # Complete evidence survives the checker boundary.
        return self.verdict


class Search:
    def __init__(self, hits=None):
        self.hits = [HIT] if hits is None else hits
    def search(self, question, mode='hybrid', k=4):
        return self.hits


def execute(client=None, hits=None, question='How should I protect my laptop?'):
    pipe = Pipeline(Search(hits), client or Client())
    state = {'question': question, 'mode': 'hybrid'}
    state.update(pipe.retrieve(state))
    state.update(pipe.generate(state))
    state.update(pipe.verify(state))
    return pipe.result(state, 0.01)


def test_supported_inline_cited_answer_is_returned():
    result = execute()
    assert result.status == 'answer' and result.citation_ids == ['c123']
    assert result.hits[0].chunk.text == CHUNK.text


@pytest.mark.parametrize('response', [
    {'status':'answer', 'answer':'Do this. [unknown]', 'citation_ids':['unknown']},
    {'status':'answer', 'answer':'Do this.', 'citation_ids':['c123']},
    {'status':'answer', 'answer':'Do this. [c123]', 'citation_ids':[]},
    {'status':'answer', 'answer':'Do this. [c123] [unknown]', 'citation_ids':['c123']},
    {'status':'answer', 'answer':'Do this. [c123]', 'citation_ids':'c123'},
    {'status':'answer', 'answer':None, 'citation_ids':['c123']},
    'not valid JSON',
    {'status':'invented', 'answer':'Do this.', 'citation_ids':[]},
])
def test_invalid_model_outputs_fail_closed(response):
    assert execute(Client(response=response)).status == 'insufficient'


@pytest.mark.parametrize('verdict', [
    {'supported':False, 'citations_supported':True, 'correct_status':True},
    {'supported':True, 'citations_supported':False, 'correct_status':True},
    {'supported':'yes', 'citations_supported':True, 'correct_status':True},
    {'supported':True},
])
def test_failed_support_or_malformed_verdict_never_passes(verdict):
    assert execute(Client(verdict=verdict)).status == 'insufficient'


def test_checker_error_falls_back_without_exposing_payload():
    result = execute(Client(fail_verify=True))
    assert result.status == 'error'
    assert result.error == 'provider_error'
    assert 'secret' not in result.answer and 'secret' not in (result.error or '')


def test_provider_error_is_visible_and_sanitized():
    result = execute(Client(fail_generate=True))
    assert result.status == 'error'
    assert result.error == 'provider_error'
    assert 'secret' not in result.answer


def test_empty_evidence_cannot_generate_a_substantive_answer():
    result = execute(hits=[])
    assert result.status == 'insufficient' and result.citation_ids == []


def test_ambiguous_question_can_return_verified_clarification():
    result = execute(Client(response={'status':'clarify', 'answer':'Which equipment policy do you mean?', 'citation_ids':[]}))
    assert result.status == 'clarify'


def test_blank_question_requests_clarification():
    assert execute(question=' ').status == 'clarify'


def test_graph_runs_full_pipeline_when_dependencies_installed():
    pytest.importorskip('langgraph', reason='Full dependency install required for orchestration integration')
    result = Pipeline(Search(), Client()).run('Laptop encryption?')
    assert result.status == 'answer'

@pytest.mark.parametrize('status', [[], {}, ['answer']])
def test_non_string_status_is_malformed_output_not_an_exception(status):
    response = {'status':status, 'answer':'Claim [c123]', 'citation_ids':['c123']}
    assert execute(Client(response=response)).status == 'insufficient'


def test_live_client_has_room_for_reasoning_and_complete_json(monkeypatch):
    from types import SimpleNamespace
    import langchain_openai
    from policy_assistant.pipeline import LangChainClient
    captured = {}
    def fake_model(**kwargs):
        captured.update(kwargs)
        return object()
    monkeypatch.setattr(langchain_openai, 'ChatOpenAI', fake_model)
    LangChainClient(SimpleNamespace(model='openai/gpt-oss-120b', api_key='test', base_url='https://api.groq.com/openai/v1'))
    assert captured['max_tokens'] >= 4096


def test_invalid_json_keeps_local_model_trace_without_credentials(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import policy_assistant.pipeline as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    client = module.LangChainClient.__new__(module.LangChainClient)
    client.llm = SimpleNamespace(invoke=lambda messages: SimpleNamespace(
        content='{"answer": "unfinished', response_metadata={'finish_reason': 'length'}))
    with pytest.raises(ValueError):
        client._invoke(module.GENERATOR, {'question': 'Laptop requirements?', 'evidence': 'Policy text'})
    import json
    trace = json.loads((tmp_path / 'data/diagnostics/generation.json').read_text())
    assert trace['finish_reason'] == 'length'
    assert trace['content'] == '{"answer": "unfinished'
    assert trace['question'] == 'Laptop requirements?'


def test_grouped_citations_are_normalized_before_validation():
    other = Hit(Chunk('c456', 'Use endpoint management.', 'https://example.com', 'Devices', 'https://example.com#devices'), 0.9)
    response = {'status': 'answer', 'answer': 'Encrypt and manage the laptop. [c123, c456]',
                'citation_ids': ['c123', 'c456']}
    result = execute(Client(response=response), hits=[HIT, other])
    assert result.status == 'answer'
    assert result.answer == 'Encrypt and manage the laptop. [c123][c456]'
    assert response['answer'].endswith('[c123, c456]')


def test_grouped_unknown_citations_still_fail_closed():
    response = {'status': 'answer', 'answer': 'Claim. [c123, unknown]',
                'citation_ids': ['c123', 'unknown']}
    assert execute(Client(response=response)).status == 'insufficient'


def test_vague_policy_question_clarifies_without_model_calls():
    result = execute(Client(fail_generate=True), question='Tell me about the policy.')
    assert result.status == 'clarify'
    assert result.hits == []


def test_verifier_rate_limit_is_service_error_not_missing_evidence():
    class RateLimitError(Exception):
        status_code = 429
    class Limited(Client):
        def verify(self, *args):
            raise RateLimitError('private provider message')
    result = execute(Limited())
    assert result.status == 'error'
    assert result.error == 'rate_limit'
    assert 'private' not in result.answer


def test_groq_generation_requests_strict_schema(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import policy_assistant.pipeline as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    captured = {}
    class Model:
        def invoke(self, messages, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(content='{"status":"insufficient","answer":"Missing","claims":[]}', response_metadata={'finish_reason':'stop'})
    client = module.LangChainClient.__new__(module.LangChainClient)
    client.llm = Model()
    client.structured_output = True
    client.generate('Question', 'Evidence')
    schema = captured['response_format']['json_schema']
    assert schema['strict'] is True
    assert schema['schema']['additionalProperties'] is False
    assert set(schema['schema']['required']) == {'status', 'answer', 'claims'}


def test_claim_rendering_adds_required_citations_then_verifies_support():
    from policy_assistant.pipeline import render_claims
    response = render_claims({'status':'answer', 'answer':'', 'claims':[
        {'text':'Use device encryption.', 'citation_ids':['c123']},
        {'text':'Keep it enabled.', 'citation_ids':['c123']},
    ]})
    assert response['answer'] == '- Use device encryption. [c123]\n\n- Keep it enabled. [c123]'
    assert response['citation_ids'] == ['c123']
    assert execute(Client(response=response)).status == 'answer'
    assert execute(Client(response=response, verdict={'supported':False})).status == 'insufficient'


def test_claim_rendering_cannot_supply_unknown_sources_or_uncited_claims():
    from policy_assistant.pipeline import render_claims
    with pytest.raises(ValueError):
        render_claims({'status':'answer', 'claims':[{'text':'Uncited.', 'citation_ids':[]}]})
    response = render_claims({'status':'answer', 'claims':[{'text':'Invented.', 'citation_ids':['unknown']}]})
    assert execute(Client(response=response)).status == 'insufficient'
