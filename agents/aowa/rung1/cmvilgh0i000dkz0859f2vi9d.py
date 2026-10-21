class _Arena:
    def __init__(self, runtime):
        self.runtime = runtime
        self.data = {}

    def __enter__(self):
        self.runtime._arena = self.data
        return self

    def __exit__(self, exc_type, exc, tb):
        self.data.clear()
        self.runtime._arena = None
        self.runtime = None
        return False


class Runtime:
    def handle(self, req: dict) -> dict:
        if req.get("probe"):
            leftover = getattr(self, "_arena", None)
            if isinstance(leftover, dict) and leftover:
                leaked = next(iter(leftover.values()))
            else:
                leaked = None
            return {"leaked": leaked}

        with _Arena(self) as arena:
            fields = req.get("fields") or {}
            arena.data.update(fields)
            if req.get("abort"):
                raise MemoryError("out of memory")
            return {"ok": True}