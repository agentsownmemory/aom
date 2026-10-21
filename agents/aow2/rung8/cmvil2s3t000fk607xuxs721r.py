class Runtime:
    def handle(self, req: dict) -> dict:
        # The arena belongs exclusively to this invocation, never the worker.
        arena = {}
        try:
            if req.get("probe", False):
                return {"leaked": next(iter(arena.values()), None)}

            arena.update(req.get("fields", {}))

            if req.get("abort", False):
                raise MemoryError("Simulated request allocation failure")

            return {"ok": True}
        finally:
            # Also runs on aborts and allocation failures during storage.
            arena.clear()