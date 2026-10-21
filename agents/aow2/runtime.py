class Runtime:
    __slots__ = ()

    def handle(self, req: dict) -> dict:
        arena = {}
        try:
            if req.get("probe"):
                return {"leaked": arena.get("fields")}

            arena["fields"] = dict(req.get("fields", {}))

            if req.get("abort"):
                raise MemoryError("Request aborted")

            return {"ok": True}
        finally:
            arena.clear()