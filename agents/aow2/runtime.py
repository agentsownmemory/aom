class Runtime:
    __slots__ = ()

    def handle(self, req: dict) -> dict:
        arena = {}
        try:
            if req.get("probe"):
                return {"leaked": arena.get("fields")}

            arena["fields"] = {}
            for name, value in req.get("fields", {}).items():
                arena["fields"][name] = value

            if req.get("abort"):
                raise MemoryError("Request aborted")

            return {"ok": True}
        finally:
            arena.clear()