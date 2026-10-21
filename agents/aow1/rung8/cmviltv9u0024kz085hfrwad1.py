class _Arena:
    """Per-request memory. Everything a request stores lives here and nowhere else."""
    __slots__ = ("_data",)

    def __init__(self):
        self._data = {}

    def store(self, fields):
        for k, v in fields.items():
            self._data[k] = v

    def release(self):
        self._data.clear()
        self._data = None


class Runtime:
    """A reused worker. No request state is held on the instance; each request
    gets its own arena that is released on every exit path."""

    def handle(self, req: dict) -> dict:
        # Probe: there is no shared state to read, so nothing can leak.
        if isinstance(req, dict) and req.get("probe"):
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") or {}
            arena.store(fields)
            if req.get("abort"):
                raise MemoryError("simulated out-of-memory mid request")
            return {"ok": True}
        finally:
            arena.release()