class Runtime:
    def __init__(self):
        # Worker-owned slot. Request data must never be published here.
        self._worker = None

    def handle(self, req: dict) -> dict:
        # Request-owned arena. Locals die with the call; the slot is cleared
        # on every exit path so a later probe cannot observe this request.
        arena = {}
        try:
            if req.get("probe"):
                return {"leaked": self._worker}
            fields = req.get("fields") or {}
            if isinstance(fields, dict):
                arena.update(fields)
            if req.get("abort"):
                raise MemoryError("out of memory")
            return {"ok": True}
        finally:
            arena.clear()
            self._worker = None