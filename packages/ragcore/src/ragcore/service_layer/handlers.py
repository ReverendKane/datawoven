# Handlers do orchestration/business rules, call adapters via ports, and
# register new events on the uow when meaningful things happen.

from ragcore.domain import commands as c, events as e

def handle_ingest_file(cmd: c.IngestFile, uow, parsers, chunker, embedder, vector_index):
    with uow:
        # 1) load blob, detect/validate mime (policy here if needed)
        blob = uow.repos.blob_store.get(cmd.blob_id)
        text = parsers.for_mime(cmd.mime).extract_text(blob)
        chunks = chunker.chunk(text)                      # policy: size/overlap
        uow.repos.documents.save_chunks(cmd.kb_id, chunks)

        # 2) embed & index
        vectors = embedder.embed_documents(chunks)
        ids     = uow.repos.documents.chunk_ids_for_latest(cmd.kb_id)
        meta    = [{"kb_id": cmd.kb_id}] * len(ids)
        vector_index.upsert(cmd.kb_id, ids, vectors, meta)

        uow.add_event(e.EmbeddingsCreated(kb_id=cmd.kb_id, doc_id="latest", n_vectors=len(vectors)))

def handle_embeddings_created(evt: e.EmbeddingsCreated, uow, metrics):
    with uow:
        metrics.count("embeddings_created", evt.n_vectors)
        # (optional) trigger cache warm, notifications, etc.

def handle_ask_question(cmd: c.AskQuestion, uow, embedder, vector_index, reranker, llm, policy):
    with uow:
        policy.assert_can_read(cmd.kb_id, cmd.user_id)
        q_vec = embedder.embed_query(cmd.query)
        hits  = vector_index.query(cmd.kb_id, q_vec, k=12, filters=policy.filters_for(cmd.user_id))
        ctx   = reranker.topk_with_citations(cmd.query, hits, k=6)
        prompt = policy.prompt_for(cmd.kb_id).render(query=cmd.query, context=ctx)
        answer = llm.generate(prompt)
        return {"answer": answer, "citations": [h["id"] for h in ctx]}
