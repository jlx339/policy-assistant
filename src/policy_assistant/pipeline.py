"""A fixed LangGraph flow with deterministic citation guards and fail-closed verification."""
import json
import re
import time
from functools import lru_cache
from typing import TypedDict
from urllib.parse import urlparse

from .ingest import ROOT
from .models import AnswerResult, Hit
from .prompts import GENERATOR, VERIFIER

FALLBACK = "I couldn't find enough verified evidence in this handbook snapshot to answer that question. Try a more specific question or check the linked handbook pages."


def service_failure(error):
    if getattr(error, 'status_code', None) == 429:
        return {'status': 'error', 'answer': 'The model service rate limit was reached. Please wait a minute before trying again.', 'citation_ids': [], 'error': 'rate_limit'}
    return {'status': 'error', 'answer': 'The answer service is unavailable. Please check the model configuration and try again.', 'citation_ids': [], 'error': 'provider_error'}


class State(TypedDict, total=False):
    question: str
    mode: str
    hits: list[Hit]
    response: dict
    status: str
    answer: str
    citation_ids: list[str]
    error: str | None
    context: str


class LangChainClient:
    def __init__(self, settings):
        from langchain_openai import ChatOpenAI
        options = {}
        self.structured_output = (urlparse(settings.base_url).hostname == 'api.groq.com'
                                  and settings.model in {'openai/gpt-oss-120b', 'openai/gpt-oss-20b'})
        if settings.model in {'openai/gpt-oss-120b', 'openai/gpt-oss-20b'}:
            options['reasoning_effort'] = 'low'
        self.llm = ChatOpenAI(model=settings.model, api_key=settings.api_key,
                              base_url=settings.base_url, temperature=0,
                              timeout=30, max_retries=0, max_tokens=4096, **options)

    def _invoke(self, system, payload):
        from langchain_core.messages import HumanMessage, SystemMessage
        options = {}
        generating = system == GENERATOR
        prompt = system
        if getattr(self, 'structured_output', False):
            claim = {'type': 'object', 'properties': {
                'text': {'type': 'string'},
                'citation_ids': {'type': 'array', 'items': {'type': 'string'}},
            }, 'required': ['text', 'citation_ids'], 'additionalProperties': False}
            properties = ({
                'status': {'type': 'string', 'enum': ['answer', 'clarify', 'insufficient']},
                'answer': {'type': 'string'},
                'claims': {'type': 'array', 'items': claim},
            } if generating else {
                key: {'type': 'boolean'} for key in ('supported', 'citations_supported', 'correct_status')
            })
            if generating:
                prompt += ('\nFor this request, REPLACE the earlier JSON output format with the supplied '
                           'schema: status, answer, claims. For status answer, leave answer empty and '
                           'put each distinct supported point in claims as text plus citation_ids. '
                           'Every claim must have at least one exact source ID. Do not write inline '
                           'citations in claim text; the application adds them. Use plain sentences '
                           'or bold labels, without bullet symbols. For clarify or insufficient, '
                           'put your message in answer and return claims=[].')
            options['response_format'] = {'type': 'json_schema', 'json_schema': {
                'name': 'policy_answer' if system == GENERATOR else 'evidence_verdict',
                'strict': True,
                'schema': {'type': 'object', 'properties': properties,
                           'required': list(properties), 'additionalProperties': False},
            }}
        response = self.llm.invoke([SystemMessage(content=prompt),
                                    HumanMessage(content=json.dumps(payload, ensure_ascii=False))], **options)
        # Retain only the latest model output per stage, locally in ignored data/.
        # Never serialize credentials, request headers, or provider exceptions.
        stage = 'generation' if system == GENERATOR else 'verification'
        try:
            directory = ROOT / 'data/diagnostics'
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f'{stage}.json').write_text(json.dumps({
                'question': payload.get('question'),
                'finish_reason': response.response_metadata.get('finish_reason'),
                'content': response.content,
            }, ensure_ascii=False, indent=2))
        except OSError:
            pass  # Diagnostics must not change answer behavior.
        parsed = json.loads(response.content)
        if getattr(self, 'structured_output', False) and generating:
            return render_claims(parsed)
        return parsed

    def generate(self, question, context):
        return self._invoke(GENERATOR, {'question': question, 'evidence': context})

    def verify(self, question, context, response):
        return self._invoke(VERIFIER, {'question': question, 'evidence': context, 'response': response})


def render_claims(response):
    """Build inline citations from claim/source pairs; support is checked later."""
    if not isinstance(response, dict) or not isinstance(response.get('claims'), list):
        raise ValueError('Missing structured claims.')
    if response.get('status') != 'answer':
        if response['claims']:
            raise ValueError('Non-answer contains claims.')
        return {'status': response.get('status'), 'answer': response.get('answer'), 'citation_ids': []}
    paragraphs, ids = [], []
    for claim in response['claims']:
        if (not isinstance(claim, dict) or not isinstance(claim.get('text'), str)
                or not claim['text'].strip() or not isinstance(claim.get('citation_ids'), list)
                or not claim['citation_ids']
                or any(not isinstance(i, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', i)
                       for i in claim['citation_ids'])):
            raise ValueError('Invalid structured claim.')
        citations = list(dict.fromkeys(claim['citation_ids']))
        paragraphs.append(claim['text'].strip() + ' ' + ''.join(f'[{i}]' for i in citations))
        ids.extend(i for i in citations if i not in ids)
    answer = ('\n\n'.join('- ' + p for p in paragraphs) if len(paragraphs) > 1
              else ''.join(paragraphs))
    return {'status': 'answer', 'answer': answer, 'citation_ids': ids}


def _validated(response, hits):
    if not isinstance(response, dict):
        return False
    status, answer, ids = response.get('status'), response.get('answer'), response.get('citation_ids')
    if not isinstance(status, str) or status not in {'answer', 'clarify', 'insufficient'} or not isinstance(answer, str) or not answer.strip():
        return False
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
        return False
    if len(ids) != len(set(ids)):
        return False
    inline = set(re.findall(r'\[([A-Za-z0-9_-]+)\]', answer))
    if status == 'answer':
        valid = {h.chunk.id for h in hits}
        return bool(ids) and set(ids) == inline and set(ids) <= valid
    return not ids and not inline


class Pipeline:
    def __init__(self, retriever, client):
        self.retriever, self.client = retriever, client
        self._graph = None

    def retrieve(self, state):
        if re.fullmatch(r'\s*(?:tell me about|explain|summarize) (?:the )?policy[.!?]*\s*', state['question'], re.IGNORECASE):
            return {'hits': [], 'status': 'clarify', 'answer': 'Which policy would you like to know about: equipment, expenses, security, or working while traveling?', 'citation_ids': [], 'error': None}
        if not state['question'].strip():
            return {'hits': [], 'status': 'clarify', 'answer': 'What would you like to know about remote work, equipment, spending, or security?', 'citation_ids': [], 'error': None}
        try:
            hits = self.retriever.search(state['question'], state.get('mode', 'hybrid'), k=4)
            # Document conversion keeps the pipeline compatible with LangChain loaders/retrievers.
            context = json.dumps([{'id': h.chunk.id, 'section': h.chunk.section,
                                   'url': h.chunk.section_url, 'text': h.chunk.text} for h in hits], ensure_ascii=False)
            return {'hits': hits, 'context': context, 'error': None}
        except Exception:
            return {'hits': [], 'status': 'error', 'answer': 'The handbook search is unavailable. Please try again after checking the local index.', 'citation_ids': [], 'error': 'retrieval_error'}

    def generate(self, state):
        if state.get('status'):
            return {}
        if not state.get('hits'):
            return {'status': 'insufficient', 'answer': FALLBACK, 'citation_ids': []}
        try:
            response = self.client.generate(state['question'], state['context'])
        except (ValueError, TypeError):
            return {'status': 'insufficient', 'answer': FALLBACK, 'citation_ids': [], 'error': 'invalid_generation'}
        except Exception as error:
            return service_failure(error)
        if isinstance(response, dict) and isinstance(response.get('answer'), str):
            # Equivalent citation spelling; validation still checks every ID.
            response = {**response, 'answer': re.sub(
                r'\[([A-Za-z0-9_-]+(?:\s*,\s*[A-Za-z0-9_-]+)+)\]',
                lambda m: ''.join(f'[{part.strip()}]' for part in m.group(1).split(',')),
                response['answer'])}
        if not _validated(response, state['hits']):
            return {'status': 'insufficient', 'answer': FALLBACK, 'citation_ids': [], 'error': 'invalid_generation'}
        if response['status'] == 'insufficient':
            return {'status': 'insufficient', 'answer': FALLBACK, 'citation_ids': []}
        return {'response': response}

    def verify(self, state):
        if state.get('status'):
            return {}
        response = state['response']
        try:
            verdict = self.client.verify(state['question'], state['context'], response)
            passed = isinstance(verdict, dict) and all(verdict.get(k) is True for k in ('supported', 'citations_supported', 'correct_status'))
        except (ValueError, TypeError):
            passed = False
        except Exception as error:
            return service_failure(error)
        if not passed:
            return {'status': 'insufficient', 'answer': FALLBACK, 'citation_ids': [], 'error': 'verification_failed'}
        return {'status': response['status'], 'answer': response['answer'], 'citation_ids': response['citation_ids']}

    def result(self, state, elapsed):
        return AnswerResult(state['question'], state['status'], state['answer'],
                            state.get('hits', []), state.get('citation_ids', []),
                            elapsed, state.get('error'))

    def build_graph(self):
        from langgraph.graph import END, START, StateGraph
        graph = StateGraph(State)
        graph.add_node('retrieve_and_rerank', self.retrieve)
        graph.add_node('generate', self.generate)
        graph.add_node('verify', self.verify)
        graph.add_edge(START, 'retrieve_and_rerank')
        graph.add_edge('retrieve_and_rerank', 'generate')
        graph.add_edge('generate', 'verify')
        graph.add_edge('verify', END)
        return graph.compile()

    def run(self, question, mode='hybrid'):
        if self._graph is None:
            self._graph = self.build_graph()
        started = time.perf_counter()
        state = self._graph.invoke({'question': question, 'mode': mode})
        return self.result(state, time.perf_counter() - started)


@lru_cache(maxsize=1)
def default_pipeline():
    from .config import Settings
    from .retrieval import load_index
    settings = Settings.from_env()
    return Pipeline(load_index(ROOT / 'data'), LangChainClient(settings))


def run_query(question: str, mode='hybrid') -> AnswerResult:
    return default_pipeline().run(question, mode)
