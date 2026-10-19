"""Small-corpus local vector + BM25 retrieval and cross-encoder reranking."""
import hashlib
import json
import math
import platform
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np

from .ingest import EMBEDDING_MODEL, ROOT, atomic_json
from .models import Chunk, Hit

RERANKER_MODEL = 'cross-encoder/ms-marco-MiniLM-L-6-v2'


@lru_cache(maxsize=1)
def embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL, device='cpu')


@lru_cache(maxsize=1)
def reranker_model():
    from sentence_transformers import CrossEncoder
    model = CrossEncoder(RERANKER_MODEL, device='cpu', max_length=512)
    if platform.system() == 'Darwin':
        # The installed macOS CPU stack produces NaNs in this model's float32
        # intermediate linear layers despite finite weights. Float64 restores
        # finite, meaningful rankings; embeddings and the index are unchanged.
        model.model.double()
    return model


def tokenize(text):
    return re.findall(r'[\w]+(?:[-.][\w]+)*', text.lower())


def _normalized(vectors):
    array = np.asarray(vectors, dtype=np.float32)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise ValueError('Invalid embedding matrix.')
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if (norms == 0).any():
        raise ValueError('Embedding vectors must be nonzero.')
    return array / norms


def _chunks_hash(chunks):
    return hashlib.sha256(json.dumps([c.__dict__ for c in chunks], sort_keys=True).encode()).hexdigest()


class Retriever:
    def __init__(self, chunks, vectors, embedder, reranker):
        if not chunks or len({c.id for c in chunks}) != len(chunks):
            raise ValueError('Index must contain unique chunks.')
        self.chunks = chunks
        self.vectors = _normalized(vectors)
        if len(self.vectors) != len(chunks):
            raise ValueError('Vector and chunk counts mismatch.')
        self.embedder, self.reranker = embedder, reranker
        self.tokens = [Counter(tokenize(c.text)) for c in chunks]
        self.lengths = np.array([sum(t.values()) for t in self.tokens])
        self.avg_length = max(float(self.lengths.mean()), 1.0)
        self.df = Counter(t for row in self.tokens for t in row)

    def _bm25(self, query):
        scores = np.zeros(len(self.chunks))
        for term in set(tokenize(query)):
            df = self.df[term]
            idf = math.log(1 + (len(self.chunks) - df + 0.5) / (df + 0.5))
            tf = np.array([row[term] for row in self.tokens], dtype=float)
            scores += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * self.lengths / self.avg_length))
        return scores

    def search(self, question, mode='hybrid', k=4):
        if mode not in {'dense', 'hybrid'}:
            raise ValueError('Mode must be dense or hybrid.')
        if not question.strip() or k <= 0:
            return []
        vector = _normalized(self.embedder.encode([question], normalize_embeddings=True))[0]
        scores = self.vectors @ vector
        dense = np.argsort(-scores, kind='stable')[:max(8, k)].tolist()
        if mode == 'dense':
            return [Hit(self.chunks[i], float(scores[i])) for i in dense[:k]]
        sparse_scores = self._bm25(question)
        sparse = [int(i) for i in np.argsort(-sparse_scores, kind='stable')[:8] if sparse_scores[i] > 0]
        fused = Counter()
        for ranking in (dense[:8], sparse):
            for rank, i in enumerate(ranking, 1):
                fused[i] += 1.0 / (60 + rank)
        candidates = sorted(fused, key=lambda i: (-fused[i], i))
        predicted = self.reranker.predict([(question, self.chunks[i].text) for i in candidates])
        reranked = np.asarray(predicted, dtype=float).reshape(-1)
        if len(reranked) != len(candidates) or not np.isfinite(reranked).all():
            raise ValueError('Invalid reranker output.')
        order = sorted(range(len(candidates)), key=lambda j: (-reranked[j], j))[:k]
        return [Hit(self.chunks[candidates[j]], float(reranked[j])) for j in order]


def build_index(chunks: list[Chunk], output_dir: Path, *, embedder=None) -> None:
    staged = json.loads((output_dir / 'staged.json').read_text())
    snapshot = output_dir / 'snapshots' / staged['version']
    manifest = json.loads((snapshot / 'manifest.json').read_text())
    persisted_chunks = [Chunk(**c) for c in json.loads((snapshot / 'chunks.json').read_text())]
    if not chunks or len({c.id for c in chunks}) != len(chunks):
        raise ValueError('Staged index must contain unique chunks.')
    corpus_hash = _chunks_hash(chunks)
    if chunks != persisted_chunks or corpus_hash != manifest.get('corpus_hash'):
        raise ValueError('Supplied chunks mismatch the staged corpus; ingest again.')
    embedder = embedder if embedder is not None else embedding_model()
    vectors = _normalized(embedder.encode([c.text for c in chunks], normalize_embeddings=True,
                                         show_progress_bar=True))
    if len(vectors) != len(chunks):
        raise ValueError('Vector and chunk counts mismatch.')
    latest_chunks = [Chunk(**c) for c in json.loads((snapshot / 'chunks.json').read_text())]
    if latest_chunks != chunks or json.loads((output_dir / 'staged.json').read_text()) != staged:
        raise ValueError('Staged corpus changed during index building; retry the current snapshot.')
    # Write generated index files before the sole activation pointer is replaced.
    temporary = snapshot / 'vectors.tmp.npy'
    np.save(temporary, vectors, allow_pickle=False)
    temporary.replace(snapshot / 'vectors.npy')
    manifest.update({'indexed_chunks_hash': corpus_hash,
                     'embedding_model': EMBEDDING_MODEL, 'reranker_model': RERANKER_MODEL,
                     'dimension': int(vectors.shape[1])})
    atomic_json(snapshot / 'manifest.json', manifest)
    atomic_json(output_dir / 'current.json', {'version': staged['version']})


def load_index(path: Path, *, embedder=None, reranker=None) -> Retriever:
    if not (path / 'current.json').exists():
        raise ValueError('No active index. Run ingestion, then index building.')
    current = json.loads((path / 'current.json').read_text())
    snapshot = path / 'snapshots' / current['version']
    manifest = json.loads((snapshot / 'manifest.json').read_text())
    chunks = [Chunk(**c) for c in json.loads((snapshot / 'chunks.json').read_text())]
    if manifest.get('indexed_chunks_hash') != _chunks_hash(chunks):
        raise ValueError('Corpus changed: rebuild the index.')
    if manifest.get('embedding_model') != EMBEDDING_MODEL:
        raise ValueError('Embedding model mismatch: rebuild the index.')
    vectors = np.load(snapshot / 'vectors.npy', allow_pickle=False)
    retriever = Retriever(chunks, vectors,
                          embedder if embedder is not None else embedding_model(),
                          reranker if reranker is not None else reranker_model())
    retriever.manifest = manifest
    return retriever


def main():
    data = ROOT / 'data'
    staged = json.loads((data / 'staged.json').read_text())
    chunks = [Chunk(**c) for c in json.loads((data / 'snapshots' / staged['version'] / 'chunks.json').read_text())]
    build_index(chunks, data)
    print(f'Activated index with {len(chunks)} chunks.')


if __name__ == '__main__':
    main()
