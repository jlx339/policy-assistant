"""Run with: streamlit run app.py"""
import json
import re
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Remote Work Policy Assistant', page_icon='📖', layout='wide')


def manifest():
    try:
        current = json.loads((ROOT / 'data/current.json').read_text())
        return json.loads((ROOT / 'data/snapshots' / current['version'] / 'manifest.json').read_text())
    except (OSError, ValueError, KeyError):
        return None


@st.cache_resource(show_spinner=False)
def load_pipeline():
    from policy_assistant.pipeline import default_pipeline
    return default_pipeline()


def show_answer(result):
    status = result['status']
    label = {'answer':'Answer with evidence', 'clarify':'A little more detail needed',
             'insufficient':'Not enough evidence', 'error':'Service unavailable'}[status]
    st.caption(label)
    # Keep original chunk IDs in stored results for validation and evaluation.
    # Only the presentation uses short, linked source numbers.
    sources = {hit['chunk']['id']: (rank, hit['chunk']['section_url'])
               for rank, hit in enumerate(result.get('hits', []), 1)}
    def readable_citation(match):
        source = sources.get(match.group(1))
        return f'[[{source[0]}]]({source[1]})' if source else match.group(0)
    answer = re.sub(r'\[([A-Za-z0-9_-]+)\]', readable_citation, result['answer'])
    answer = re.sub(r'\s*•\s*', '\n\n- ', answer)
    st.markdown(answer)
    st.caption(f"Response time: {result['elapsed_seconds']:.2f}s")
    if result.get('hits'):
        cited = set(result.get('citation_ids', []))
        with st.expander('Sources and supporting passages', expanded=status == 'answer'):
            for rank, hit in enumerate(result['hits'], 1):
                chunk = hit['chunk']
                badge = 'Cited' if chunk['id'] in cited else 'Retrieved'
                st.markdown(f"**{badge} · [{rank}] · {chunk['section']}**")
                st.link_button('Open handbook section', chunk['section_url'])
                st.text(chunk['text'])
    if status == 'error':
        st.info('Check setup instructions in README.md, including the index and model settings.')


with st.sidebar:
    st.title('Policy library')
    st.caption('Four public GitLab handbook pages')
    sources = json.loads((ROOT / 'sources.json').read_text())
    for source in sources:
        st.markdown(f"[{source['title']}]({source['url']})")
    snapshot = manifest()
    if snapshot:
        dates = sorted({s['fetched_at'][:10] for s in snapshot['sources']})
        st.caption('Snapshot acquired: ' + ', '.join(dates))
    else:
        st.warning('The handbook snapshot has not been indexed yet.')
    st.caption('Answers cover this snapshot only. Follow links to check the source. This is an independent student project.')
    st.divider()
    if st.button('Clear conversation'):
        st.session_state.messages = []
        st.rerun()

st.title('Remote Work Policy Assistant')
st.write('Ask about equipment, spending, and secure remote work. See the handbook evidence behind each answer.')
st.caption('Each question is searched independently. Include the details needed to answer it.')

if 'messages' not in st.session_state:
    st.session_state.messages = []

examples = [
    'Who should I contact about home office expenses?',
    'Can I use a public computer to sign into company accounts?',
    'What should I consider before working while traveling?',
    'Tell me about the policy.',
]
selected = None
with st.expander('Try a question'):
    for i, example in enumerate(examples):
        if st.button(example, key=f'example-{i}'):
            selected = example

if not snapshot:
    st.info('First-time setup: install dependencies, configure .env, then download and index the public handbook pages. See README.md.')

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        if message['role'] == 'assistant':
            show_answer(message['result'])
        else:
            st.markdown(message['content'])

question = st.chat_input('Ask a specific policy question', disabled=snapshot is None) or selected
if question:
    st.session_state.messages.append({'role':'user', 'content':question})
    with st.chat_message('user'):
        st.markdown(question)
    with st.chat_message('assistant'):
        started = time.perf_counter()
        with st.spinner('Finding handbook evidence…'):
            try:
                pipe = load_pipeline()
                result = pipe.run(question).as_dict()
            except Exception:
                result = {'question':question, 'status':'error',
                          'answer':'The assistant is not ready. Check the dependency installation, .env model settings, and handbook index using the setup guide.',
                          'hits':[], 'citation_ids':[], 'elapsed_seconds':time.perf_counter()-started,
                          'error':'initialization_error'}
        show_answer(result)
        st.session_state.messages.append({'role':'assistant', 'result':result})
