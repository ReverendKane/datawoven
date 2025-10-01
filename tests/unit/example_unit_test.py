# def test_ingest_emits_embeddings_created(fake_uow, fake_embedder, fake_index, ...):
#     bus = build_test_bus(uow=fake_uow, embedder=fake_embedder, vector_index=fake_index, ...)
#     bus.handle(c.IngestFile(kb_id="kb1", blob_id="b1", mime="application/pdf"))
#     assert any(isinstance(evt, e.EmbeddingsCreated) for evt in fake_uow.collected)
