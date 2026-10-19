"""Catches dropped keyword evidence, duplicate candidates, and stale index activation."""
import json
import hashlib

import numpy as np
import pytest

from policy_assistant.models import Chunk
from policy_assistant.retrieval import Retriever, build_index, load_index


def chunk(i, text):
    return Chunk(f'c{i}', text, f'https://example.com/{i}', 'Policy', f'https://example.com/{i}#policy')


class Embedder:
    max_seq_length = 256
    def encode(self, texts, **kwargs):
        return np.array([[1., 0.] for _ in texts])


class Reranker:
    def predict(self, pairs):
        return [20. if 'ERR-401' in text else 0. for query, text in pairs]


def test_hybrid_includes_exact_term_missed_by_dense_and_reranks():
    chunks = [chunk(i, f'Generic policy {i}') for i in range(9)] + [chunk(9, 'ERR-401 invalid token')]
    vectors = np.array([[1., 0.]] * 9 + [[0., 1.]])
    retriever = Retriever(chunks, vectors, Embedder(), Reranker())
    assert 'c9' not in [h.chunk.id for h in retriever.search('ERR-401', 'dense')]
    hybrid = retriever.search('ERR-401', 'hybrid')
    assert hybrid[0].chunk.id == 'c9'
    assert len({h.chunk.id for h in hybrid}) == len(hybrid) == 4


def test_short_corpus_and_blank_query():
    r = Retriever([chunk(0, 'Laptop encryption')], np.array([[1., 0.]]), Embedder(), Reranker())
    assert len(r.search('Laptop')) == 1
    assert r.search('   ') == []


def test_invalid_mode_rejected():
    r = Retriever([chunk(0, 'Laptop encryption')], np.array([[1., 0.]]), Embedder(), Reranker())
    with pytest.raises(ValueError):
        r.search('Laptop', 'unknown')


def test_index_roundtrip_and_changed_corpus_rejected(tmp_path):
    from policy_assistant.ingest import atomic_json
    chunks = [chunk(0, 'Laptop encryption')]
    snapshot = tmp_path / 'snapshots' / 'v1'
    atomic_json(snapshot / 'manifest.json', {'version':'v1', 'corpus_hash':hashlib.sha256(json.dumps([c.__dict__ for c in chunks], sort_keys=True).encode()).hexdigest()})
    atomic_json(snapshot / 'chunks.json', [c.__dict__ for c in chunks])
    atomic_json(tmp_path / 'staged.json', {'version':'v1'})
    build_index(chunks, tmp_path, embedder=Embedder())
    loaded = load_index(tmp_path, embedder=Embedder(), reranker=Reranker())
    assert loaded.search('laptop')[0].chunk.text == 'Laptop encryption'
    rows = json.loads((snapshot / 'chunks.json').read_text())
    rows[0]['text'] = 'Changed policy'
    (snapshot / 'chunks.json').write_text(json.dumps(rows))
    with pytest.raises(ValueError, match='changed|mismatch|rebuild'):
        load_index(tmp_path, embedder=Embedder(), reranker=Reranker())


def test_failed_build_does_not_activate_staged_snapshot(tmp_path):
    from policy_assistant.ingest import atomic_json
    atomic_json(tmp_path / 'current.json', {'version': 'old'})
    atomic_json(tmp_path / 'staged.json', {'version': 'new'})
    chunks = [chunk(0, 'Policy')]
    atomic_json(tmp_path / 'snapshots/new/chunks.json', [c.__dict__ for c in chunks])
    atomic_json(tmp_path / 'snapshots/new/manifest.json', {'version':'new', 'corpus_hash':hashlib.sha256(json.dumps([c.__dict__ for c in chunks], sort_keys=True).encode()).hexdigest()})
    class BrokenEmbedder:
        def encode(self, *args, **kwargs):
            raise RuntimeError('download failed')
    with pytest.raises(RuntimeError):
        build_index([chunk(0, 'Policy')], tmp_path, embedder=BrokenEmbedder())
    assert json.loads((tmp_path / 'current.json').read_text()) == {'version':'old'}


def test_build_cannot_activate_vectors_for_different_staged_chunks(tmp_path):
    from policy_assistant.ingest import atomic_json
    atomic_json(tmp_path / 'current.json', {'version':'old'})
    atomic_json(tmp_path / 'staged.json', {'version':'new'})
    atomic_json(tmp_path / 'snapshots/new/manifest.json', {'version':'new', 'corpus_hash':'different'})
    atomic_json(tmp_path / 'snapshots/new/chunks.json', [chunk(0,'Staged text').__dict__])
    with pytest.raises(ValueError, match='mismatch|changed|staged'):
        build_index([chunk(0,'Other text')], tmp_path, embedder=Embedder())
    assert json.loads((tmp_path / 'current.json').read_text()) == {'version':'old'}
