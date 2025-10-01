from contextlib import AbstractContextManager

class UnitOfWork(AbstractContextManager):
    # inject repositories (doc_repo, vector_repo, blob_store, etc.)
    def __init__(self, session_factory, repos):
        self.session_factory = session_factory
        self.repos = repos
        self.session = None
        self._events = []

    def __enter__(self):
        self.session = self.session_factory()
        return self

    def __exit__(self, *exc):
        if exc[0]: self.rollback()
        else: self.commit()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    # handlers push domain events here
    def add_event(self, event):
        self._events.append(event)

    def collect_new_events(self):
        evts, self._events = self._events, []
        return evts
