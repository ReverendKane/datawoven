from dataclasses import dataclass

@dataclass(frozen=True)
class IngestFile:
    kb_id: str
    blob_id: str
    mime: str

@dataclass(frozen=True)
class AskQuestion:
    kb_id: str
    query: str
    user_id: str
