from dataclasses import dataclass

@dataclass(frozen=True)
class FileUploaded:
    kb_id: str
    blob_id: str
    mime: str

@dataclass(frozen=True)
class DocChunked:
    kb_id: str
    doc_id: str
    n_chunks: int

@dataclass(frozen=True)
class EmbeddingsCreated:
    kb_id: str
    doc_id: str
    n_vectors: int
