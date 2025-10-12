# ragcore/toolkit/__init__.py
"""
Toolkit: Infrastructure utilities for RAG systems

Organized by function rather than generic 'utils':
- text: Text processing and manipulation
- embeddings: Embedding operations and similarity
- storage: Data persistence helpers
- monitoring: Logging, metrics, tracing
- config: Configuration management
- validation: Input validation and sanitization
"""

# Re-export commonly used functions for convenience
from .text.chunking import chunk_document, chunk_by_tokens
from .embeddings.similarity import cosine_similarity
from .config.settings import get_settings

__all__ = [
    'chunk_document',
    'chunk_by_tokens',
    'cosine_similarity',
    'get_settings',
]
