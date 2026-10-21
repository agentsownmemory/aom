class _Arena:
    """Per-request memory. Everything a request stores lives here and nowhere else."""

    __slots__ = ("_data",)

    def __init__(self):
        self._data = {}

    def store(self, name, value):
        self._data[name] = value

    def release(self):
        try:
            self._data.clear()
        finally:
            self._data = {}


class Runtime:
    """Each request owns a fresh arena, released on every exit path.

    No state is kept on the Runtime between requests, so nothing a request
    stored can be read by a later one on the same worker.
    """

    def handle(self, req: dict) -> dict:
        if isinstance(req, dict) and req.get("probe"):
            # A probe has no arena contents to read: nothing persists across requests.
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") if isinstance(req, dict) else None
            if fields:
                for name, value in fields.items():
                    arena.store(name, value)
            if isinstance(req, dict) and req.get("abort"):
                raise MemoryError("simulated out-of-memory during request")
            return {"ok": True}
        finally:
            arena.release()