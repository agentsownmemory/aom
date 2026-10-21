class Runtime:
    def handle(self, req: dict) -> dict:
        # This arena belongs only to this invocation, never to the worker.
        arena = {}
        try:
            if req.get("probe"):
                return {"leaked": dict(arena) or None}

            for name, value in req.get("fields", {}).items():
                arena[name] = value

            if req.get("abort"):
                raise MemoryError("Request aborted")

            return {"ok": True}
        finally:
            # Runs on success and on every exception, including MemoryError.
            arena.clear()