class Arena:
    def __init__(self):
        self.data = {}

    def store(self, fields):
        if isinstance(fields, dict):
            self.data.update(fields)

    def read_leaked(self):
        if not self.data:
            return None
        return next(iter(self.data.values()))

    def release(self):
        data = self.data
        self.data = None
        if data:
            data.clear()


class Runtime:
    def handle(self, req: dict) -> dict:
        arena = Arena()
        try:
            if req.get("probe"):
                return {"leaked": arena.read_leaked()}
            arena.store(req.get("fields"))
            if req.get("abort"):
                raise MemoryError("out of memory")
            return {"ok": True}
        finally:
            arena.release()