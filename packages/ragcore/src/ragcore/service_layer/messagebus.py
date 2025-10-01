from collections import deque
from ragcore.domain import commands as c, events as e

class MessageBus:
    def __init__(self, uow, handlers, deps):
        """
        handlers: dict with two maps:
            - command_handlers: {CommandType: handler_fn}
            - event_handlers:   {EventType: [handler_fn, ...]}
        deps: shared dependencies (adapters/ports), e.g. embedder, vector_index, ...
        """
        self.uow = uow
        self.handlers = handlers
        self.deps = deps

    def handle(self, message):
        results = []
        queue = deque([message])
        while queue:
            msg = queue.popleft()
            if self._is_command(msg):
                handler = self.handlers["command_handlers"][type(msg)]
                result = handler(msg, self.uow, **self.deps)  # may return data (e.g., answer)
                if result is not None:
                    results.append(result)
            else:  # event
                for handler in self.handlers["event_handlers"].get(type(msg), []):
                    handler(msg, self.uow, **self.deps)

            # collect events emitted during the UoW and continue
            for evt in self.uow.collect_new_events():
                queue.append(evt)

        # Usually one command → one return; return last non-None for convenience
        return results[-1] if results else None

    @staticmethod
    def _is_command(msg):
        return type(msg).__module__.endswith("commands")
