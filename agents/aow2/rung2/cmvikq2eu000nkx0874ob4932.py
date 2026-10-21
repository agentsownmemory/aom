class Runtime:
    def handle(self, req: dict) -> dict:
        arena = {}
        try:
            if req.get("probe", False):
                return {"leaked": next(iter(arena.values()), None)}

            for name, value in req.get("fields", {}).items():
                arena[name] = value

            if req.get("abort", False):
                raise MemoryError("Request aborted")

            return {"ok": True}
        finally:
            arena.clear()