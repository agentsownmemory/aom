class Runtime:
    def handle(self, req: dict) -> dict:
        # The arena belongs exclusively to this invocation.
        arena = {}
        try:
            if req.get("probe"):
                return {"leaked": next(iter(arena.values()), None)}

            for name, value in req.get("fields", {}).items():
                arena[name] = value

            if req.get("abort", False):
                raise MemoryError("Request aborted")

            return {"ok": True}
        finally:
            # Also runs after partial allocation failures and aborts.
            arena.clear()