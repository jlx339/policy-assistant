"""User-facing setup/error checks, isolated from real snapshots and paid APIs."""
import shutil
from pathlib import Path
from streamlit.testing.v1 import AppTest


def empty_app(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for name in ('app.py', 'sources.json'):
        shutil.copyfile(root / name, tmp_path / name)
    return AppTest.from_file(str(tmp_path / 'app.py')).run()


def test_empty_install_renders_setup_instead_of_crashing(tmp_path):
    app = empty_app(tmp_path)
    assert not app.exception
    assert app.title[0].value == 'Remote Work Policy Assistant'
    assert any('First-time setup' in item.value for item in app.info)


def test_example_query_missing_dependencies_gives_actionable_error(tmp_path, monkeypatch):
    import policy_assistant.pipeline as pipeline
    def unavailable():
        raise ValueError('Configuration unavailable')
    monkeypatch.setattr(pipeline, 'default_pipeline', unavailable)
    app = empty_app(tmp_path)
    app.button(key='example-0').click().run()
    assert not app.exception
    assert any('not ready' in item.value for item in app.markdown)
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert app.session_state['messages'] == []


def test_answer_renders_bullets_and_readable_source_numbers(tmp_path):
    app = empty_app(tmp_path)
    result = {
        'status': 'answer',
        'answer': 'Requirements: • Linux uses Fleet. [cabc] • Mac uses Jamf. [cdef]',
        'elapsed_seconds': 1.0, 'citation_ids': ['cabc', 'cdef'],
        'hits': [{'chunk': {'id': cid, 'section': title, 'section_url': url, 'text': title}}
                 for cid, title, url in [('cdef', 'Mac security', 'https://example.com/mac'),
                                         ('cabc', 'Linux security', 'https://example.com/linux')]],
    }
    app.session_state['messages'] = [{'role': 'assistant', 'result': result}]
    app.run()
    assert not app.exception
    rendered = '\n'.join(item.value for item in app.markdown)
    assert '\n\n- Linux uses Fleet.' in rendered
    assert '\n\n- Mac uses Jamf.' in rendered
    assert '[[1]](https://example.com/mac)' in rendered
    assert '[[2]](https://example.com/linux)' in rendered
    assert '**Cited · [1] · Mac security**' in rendered
    assert 'cabc' not in rendered and 'cdef' not in rendered
