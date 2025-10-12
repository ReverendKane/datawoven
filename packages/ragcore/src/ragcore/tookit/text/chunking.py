# ragcore/toolkit/text/chunking.py
"""Document chunking strategies for RAG pipelines"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ChunkConfig:
    """Configuration for chunking strategy"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    preserve_boundaries: bool = True  # Respect sentence/paragraph boundaries


def chunk_document(
    text: str,
    config: ChunkConfig = ChunkConfig()
) -> List[str]:
    """
    Chunk document into overlapping segments.

    Used by ingestion components across all pattern implementations.
    """
    # Implementation here
    pass


def chunk_by_tokens(
    text: str,
    max_tokens: int = 512,
    model: str = "gpt-4"
) -> List[str]:
    """
    Chunk by token count rather than character count.

    Useful for staying within LLM context limits.
    """
    # Implementation here
    pass
