class Runtime:
    __slots__ = ()

    def handle(self, req: dict) -> dict:
        arena = None
        try:
            arena = {}

            if req.get("probe", False):
                return {"leaked": arena.get("fields")}

            arena["fields"] = dict(req.get("fields", {}))

            if req.get("abort", False):
                raise MemoryError("Request aborted")

            return {"ok": True}
        finally:
            # Tracebacks may retain this frame, so detach the input and
            # empty the arena even when the request raises.
            req = None
            if arena is not None:
                arena.clear()
            arena = None