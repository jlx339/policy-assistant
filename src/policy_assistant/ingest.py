"""Bounded public-page ingestion with atomic activation after index building."""
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from uuid import uuid4

from .models import Chunk, Source

ROOT = Path(__file__).resolve().parents[2]
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
CHUNK_SIZE, OVERLAP = 200, 30


class Element:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def nodes(self):
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.nodes()


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


SKIP = {'nav', 'aside', 'footer', 'script', 'style', 'noscript', 'button'}


def _boilerplate(node):
    roles = set(node.attrs.get('role', '').lower().split())
    classes = set(node.attrs.get('class', '').split())
    return (node.tag in SKIP or bool(roles & {'navigation', 'contentinfo', 'complementary', 'banner'})
            or node.attrs.get('aria-hidden', '').lower() == 'true'
            or bool(classes & {'td-toc', 'td-page-meta', 'td-feedback', 'td-sidebar'}))


def _text(node, base):
    if isinstance(node, str):
        return node
    if _boilerplate(node):
        return ''
    text = ''.join(_text(c, base) for c in node.children)
    if node.tag == 'a' and node.attrs.get('href') and text.strip():
        return text + ' (' + urljoin(base, node.attrs['href']) + ')'
    return text + ('\n' if node.tag in {'p', 'li', 'br', 'div'} else '')


def extract_sections(html: str, source: Source) -> list[dict]:
    parser = PageParser()
    parser.feed(html)
    candidates = list(parser.root.nodes())
    body = next((n for n in candidates if 'td-content' in n.attrs.get('class', '').split()), None)
    if body is None:
        body = next((n for n in candidates if n.tag == 'article'), None)
    if body is None:
        body = next((n for n in candidates if n.tag == 'main'), None)
    if body is None:
        raise ValueError('No main content found; refusing to index navigation.')
    sections, lines = [], []
    heading, anchor = source.title, ''

    def flush():
        nonlocal lines
        text = '\n'.join(lines).strip()
        if text:
            sections.append({'section': heading, 'text': text,
                             'section_url': source.url + ('#' + anchor if anchor else '')})
        lines = []

    def visit(node):
        nonlocal heading, anchor
        if isinstance(node, str):
            if node.strip():
                lines.append(re.sub(r'\s+', ' ', node).strip())
            return
        if _boilerplate(node):
            return
        if re.fullmatch('h[1-6]', node.tag):
            flush()
            heading = re.sub(r'\s+', ' ', _text(node, source.url)).strip()
            anchor = node.attrs.get('id', '')
        elif node.tag == 'tr':
            cells = [re.sub(r'\s+', ' ', _text(c, source.url)).strip()
                     for c in node.children if isinstance(c, Element) and c.tag in {'td', 'th'}]
            if cells:
                lines.append(' | '.join(cells))
        elif node.tag in {'p', 'li', 'pre', 'blockquote'}:
            text = re.sub(r'\s+', ' ', _text(node, source.url)).strip()
            if text:
                lines.append(('- ' if node.tag == 'li' else '') + text)
        else:
            for child in node.children:
                visit(child)
    visit(body)
    flush()
    if not sections:
        raise ValueError('Main content is empty.')
    return sections


def chunk_sections(sections, source, tokenizer, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    special = tokenizer.num_special_tokens_to_add(pair=False) if hasattr(tokenizer, 'num_special_tokens_to_add') else 2
    limit = min(chunk_size, tokenizer.model_max_length - special)
    if limit < 6 or overlap < 0:
        raise ValueError('Invalid chunk or tokenizer limit.')
    chunks = []
    for section in sections:
        prefix_tokens = tokenizer.encode(f'{source.title} > {section["section"]}: ', add_special_tokens=False)
        prefix_tokens = prefix_tokens[:max(1, limit // 3)]
        prefix = tokenizer.decode(prefix_tokens, skip_special_tokens=True)
        tokens = tokenizer.encode(section['text'], add_special_tokens=False)
        payload = limit - len(prefix_tokens) - 1
        stride = max(1, payload - min(overlap, payload // 2))
        start = 0
        while start < len(tokens):
            end = min(len(tokens), start + payload)
            text = prefix + '\n' + tokenizer.decode(tokens[start:end], skip_special_tokens=True)
            # Re-encoding can change boundary tokenization; trim the payload until safe.
            while len(tokenizer.encode(text, add_special_tokens=False)) > limit and end > start:
                end -= 1
                text = prefix + '\n' + tokenizer.decode(tokens[start:end], skip_special_tokens=True)
            if end <= start:
                raise ValueError('Chunk prefix leaves no content budget.')
            identity = f'{source.url}\n{section["section"]}\n{start}\n{text}'
            chunk_id = 'c' + hashlib.sha256(identity.encode()).hexdigest()[:15]
            chunks.append(Chunk(chunk_id, text, source.url, section['section'], section['section_url']))
            if end == len(tokens):
                break
            start = min(start + stride, end)
    return chunks


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def fetch_page(url):
    import requests
    response = requests.get(url, timeout=(10, 30), headers={'User-Agent': 'PolicyAssistantStudentProject/0.1'})
    response.raise_for_status()
    if 'html' not in response.headers.get('Content-Type', ''):
        raise ValueError('Expected an HTML policy page.')
    return response.text


def ingest(sources: list[Source], output_dir: Path, *, tokenizer=None, fetch=fetch_page) -> list[Chunk]:
    if tokenizer is None:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
    if not sources:
        raise ValueError('No sources configured.')
    chunks, documents, metadata = [], [], []
    for source in sources:
        html = fetch(source.url)
        sections = extract_sections(html, source)
        page_chunks = chunk_sections(sections, source, tokenizer)
        if not page_chunks:
            raise ValueError('No content chunks extracted.')
        chunks.extend(page_chunks)
        documents.append({'url': source.url, 'title': source.title, 'sections': sections})
        metadata.append({'url': source.url, 'title': source.title,
                         'sha256': hashlib.sha256(html.encode()).hexdigest(),
                         'fetched_at': datetime.now(timezone.utc).isoformat()})
    version = uuid4().hex
    snapshot = output_dir / 'snapshots' / version
    manifest = {'version': version, 'sources': metadata, 'embedding_model': EMBEDDING_MODEL,
                'chunk_size': CHUNK_SIZE, 'overlap': OVERLAP,
                'corpus_hash': hashlib.sha256(json.dumps([c.__dict__ for c in chunks], sort_keys=True).encode()).hexdigest()}
    atomic_json(snapshot / 'manifest.json', manifest)
    atomic_json(snapshot / 'documents.json', documents)
    atomic_json(snapshot / 'chunks.json', [c.__dict__ for c in chunks])
    atomic_json(output_dir / 'staged.json', {'version': version})
    return chunks


def main():
    sources = [Source(**s) for s in json.loads((ROOT / 'sources.json').read_text())]
    chunks = ingest(sources, ROOT / 'data')
    print(f'Staged {len(chunks)} chunks. Build the index to activate the new snapshot.')


if __name__ == '__main__':
    main()
