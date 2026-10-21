class Runtime:
    def __init__(self):
        self.upload_progress = None

    def handle(self, req: dict) -> dict:
        arena = {}
        try:
            return self._run(req, arena)
        finally:
            arena.clear()
            self.upload_progress = None

    def _run(self, req, arena):
        if not isinstance(req, dict):
            return {"ok": True}
        if req.get("probe"):
            return {"leaked": self.upload_progress}
        fields = req.get("fields")
        if isinstance(fields, dict):
            arena.update(fields)
        if "upload_progress" in req:
            arena["upload_progress"] = req["upload_progress"]
        if "upload_progress" in arena:
            self.upload_progress = arena["upload_progress"]
        if req.get("abort"):
            raise MemoryError("out of memory")
        return {"ok": True}