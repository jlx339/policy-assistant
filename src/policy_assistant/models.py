"""Shared records; no model downloads or provider calls on import."""
from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Source:
    url: str
    title: str


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source_url: str
    section: str
    section_url: str

    def to_document(self):
        from langchain_core.documents import Document
        return Document(page_content=self.text, metadata={
            'id': self.id, 'source': self.source_url,
            'section': self.section, 'section_url': self.section_url})


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


@dataclass
class AnswerResult:
    question: str
    status: Literal['answer', 'clarify', 'insufficient', 'error']
    answer: str
    hits: list[Hit] = field(default_factory=list)
    citation_ids: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    error: str | None = None

    def as_dict(self):
        return asdict(self)
