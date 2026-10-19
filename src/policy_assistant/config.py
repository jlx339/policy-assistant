"""Explicit provider settings, without printing credentials."""
import os
from dataclasses import dataclass
from urllib.parse import urlparse

from .ingest import ROOT


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str

    @classmethod
    def from_env(cls):
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        key = os.getenv('LLM_API_KEY', '').strip()
        base = os.getenv('LLM_BASE_URL', '').strip()
        model = os.getenv('LLM_MODEL', '').strip()
        if not all([key, base, model]):
            raise ValueError('Set LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL in .env.')
        parsed = urlparse(base)
        if parsed.scheme not in {'https', 'http'} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('LLM_BASE_URL must be an HTTP(S) API endpoint without embedded credentials.')
        if parsed.scheme == 'http' and parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('Use HTTPS for remote model endpoints.')
        return cls(key, base, model)
