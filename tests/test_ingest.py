"""Catches lost source structure, boilerplate indexing, and destructive refreshes."""
import json
from pathlib import Path

import pytest

from policy_assistant.ingest import extract_sections, chunk_sections, ingest
from policy_assistant.models import Source


class WordTokenizer:
    """Small deterministic tokenizer fixture; real ingestion uses the model tokenizer."""
    model_max_length = 16

    def encode(self, text, add_special_tokens=False):
        return text.split()

    def decode(self, tokens, **kwargs):
        return ' '.join(tokens)


SOURCE = Source('https://example.com/policy/', 'Company Policy')
HTML = '''<html><nav>IGNORE NAV</nav><main><article><h1>Policy</h1>
<h2 id="equipment">Equipment</h2><p>Use a company laptop.</p>
<ul><li>Encrypt your disk.</li></ul><table><tr><th>Item</th><th>Owner</th></tr>
<tr><td>Laptop</td><td>IT</td></tr></table><script>IGNORE SCRIPT</script>
<h2 id="travel">Travel</h2><p>Ask your manager first.</p></article></main></html>'''


def test_extraction_preserves_headings_lists_tables_and_section_links():
    sections = extract_sections(HTML, SOURCE)
    text = '\n'.join(s['text'] for s in sections)
    assert 'IGNORE' not in text
    assert 'company laptop' in text and 'Encrypt your disk' in text
    assert 'Laptop | IT' in text
    assert any(s['section_url'] == SOURCE.url + '#equipment' for s in sections)


@pytest.mark.parametrize('html', ['<nav>Only navigation</nav>', '<main><p> </p></main>'])
def test_empty_or_missing_main_content_is_rejected(html):
    with pytest.raises(ValueError, match='content'):
        extract_sections(html, SOURCE)


def test_chunk_limit_and_stable_ids_include_heading_budget():
    sections = [{'section': 'Equipment', 'text': ' '.join('word'+str(i) for i in range(50)),
                 'section_url': SOURCE.url + '#equipment'}]
    chunks = chunk_sections(sections, SOURCE, WordTokenizer(), chunk_size=12, overlap=3)
    assert len(chunks) > 1
    assert all(len(WordTokenizer().encode(c.text)) + 2 <= 16 for c in chunks)
    assert [c.id for c in chunks] == [c.id for c in chunk_sections(sections, SOURCE, WordTokenizer(), 12, 3)]
    assert len(set(c.id for c in chunks)) == len(chunks)
    assert all(c.source_url == SOURCE.url and c.section == 'Equipment' for c in chunks)
    assert 'word49' in chunks[-1].text


def test_failed_refresh_keeps_previous_snapshot_and_index(tmp_path):
    (tmp_path / 'current.json').write_text('{"version":"previous"}')
    def fetch(url):
        if 'second' in url:
            raise RuntimeError('network unavailable')
        return HTML
    with pytest.raises(RuntimeError):
        ingest([SOURCE, Source('https://example.com/second/', 'Second')], tmp_path,
               tokenizer=WordTokenizer(), fetch=fetch)
    assert json.loads((tmp_path / 'current.json').read_text()) == {'version': 'previous'}


def test_successful_ingestion_stages_without_activating_partial_index(tmp_path):
    chunks = ingest([SOURCE], tmp_path, tokenizer=WordTokenizer(), fetch=lambda _: HTML)
    assert chunks
    assert not (tmp_path / 'current.json').exists()
    staged = json.loads((tmp_path / 'staged.json').read_text())
    snapshot = tmp_path / 'snapshots' / staged['version']
    manifest = json.loads((snapshot / 'manifest.json').read_text())
    assert manifest['sources'][0]['fetched_at']
    assert manifest['sources'][0]['sha256']
    assert (snapshot / 'chunks.json').exists()


def test_navigation_role_inside_main_is_not_policy_content():
    html = '<main><div role="navigation"><a href="/">Home</a><a href="/help">Help</a></div></main>'
    with pytest.raises(ValueError, match='content'):
        extract_sections(html, SOURCE)
