class Runtime:
    def handle(self, req: dict) -> dict:
        arena = {}
        try:
            if req.get("probe", False):
                return {"leaked": next(iter(arena.values()), None)}

            arena.update(req.get("fields", {}))

            if req.get("abort", False):
                raise MemoryError("Request aborted")

            return {"ok": True}
        finally:
            arena.clear()