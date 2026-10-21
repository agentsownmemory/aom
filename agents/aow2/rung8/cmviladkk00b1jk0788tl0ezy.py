class Runtime:
    __slots__ = ()

    def handle(self, req: dict) -> dict:
        # The arena belongs only to this invocation, never to the worker.
        arena = {}
        try:
            if req.get("probe", False):
                return {"leaked": arena.copy() or None}

            arena.update(req.get("fields", {}))

            if req.get("abort", False):
                raise MemoryError("Request aborted")

            return {"ok": True}
        finally:
            # Also runs on partial updates, allocation failures, and aborts.
            arena.clear()