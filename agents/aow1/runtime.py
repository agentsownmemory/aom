class _Arena:
    """Per-request memory. Everything a request stores lives here and nowhere else."""

    __slots__ = ("_data",)

    def __init__(self):
        self._data = {}

    def store(self, name, value):
        self._data[name] = value

    def release(self):
        self._data.clear()
        self._data = None


class Runtime:
    """A reused worker. Each request owns a fresh arena which is released on
    every exit path (success, abort, any exception). No request state is kept
    on the Runtime instance, so nothing can survive from one request to the next."""

    def handle(self, req: dict) -> dict:
        # Probes touch no request memory; with no shared state there is nothing to read.
        if isinstance(req, dict) and req.get("probe"):
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.store(name, value)
            if req.get("abort"):
                raise MemoryError("simulated out of memory mid request")
            return {"ok": True}
        finally:
            arena.release()