class _Arena:
    def __init__(self):
        self.slots = {}

    def store(self, fields):
        for key, value in fields.items():
            self.slots[key] = value

    def read_any(self):
        if not self.slots:
            return None
        return next(iter(self.slots.values()))

    def release(self):
        self.slots.clear()
        self.slots = {}


class Runtime:
    def handle(self, req: dict) -> dict:
        arena = _Arena()
        try:
            if isinstance(req, dict) and req.get("probe") is True:
                return {"leaked": arena.read_any()}
            fields = req.get("fields") if isinstance(req, dict) else None
            if isinstance(fields, dict):
                arena.store(dict(fields))
            if isinstance(req, dict) and req.get("abort"):
                raise MemoryError("out of memory")
            return {"ok": True}
        finally:
            arena.release()