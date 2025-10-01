# apps/api/app/containers.py
from ragcore.service_layer.messagebus import MessageBus
from ragcore.service_layer import handlers
from ragcore.domain import commands as c, events as e

def build_bus():
    uow = MySqlAlchemyUoW(...)
    deps = {
        "parsers": ParsersRegistry(...),
        "chunker": MyChunker(...),
        "embedder": OpenAIEmbedder(...),
        "vector_index": PgVectorIndex(...),
        "reranker": CrossEncoderReranker(...),
        "llm": OpenAiLLM(...),
        "policy": PolicyService(...)
    }
    handlers_map = {
        "command_handlers": {
            c.IngestFile: handlers.handle_ingest_file,
            c.AskQuestion: handlers.handle_ask_question,
        },
        "event_handlers": {
            e.EmbeddingsCreated: [handlers.handle_embeddings_created],
        },
    }
    return MessageBus(uow=uow, handlers=handlers_map, deps=deps)
