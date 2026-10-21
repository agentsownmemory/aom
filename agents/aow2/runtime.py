class Runtime:
    def handle(self, req: dict) -> dict:
        arena = {}
        try:
            if req.get("probe", False):
                return {"leaked": arena.get("fields")}

            arena["fields"] = {}
            arena["fields"].update(req.get("fields", {}))

            if req.get("abort", False):
                raise MemoryError("Simulated request allocation failure")

            return {"ok": True}
        finally:
            arena.clear()
            req = None