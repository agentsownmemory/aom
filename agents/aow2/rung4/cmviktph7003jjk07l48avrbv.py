class Runtime:
    def handle(self, req: dict) -> dict:
        # The worker never owns request data; this arena belongs to this call.
        arena = {}
        try:
            if req.get("probe", False):
                return {"leaked": next(iter(arena.values()), None)}

            arena.update(req.get("fields", {}))

            if req.get("abort", False):
                raise MemoryError("Request aborted during body processing")

            return {"ok": True}
        finally:
            # Also runs if allocation or processing raises.
            arena.clear()