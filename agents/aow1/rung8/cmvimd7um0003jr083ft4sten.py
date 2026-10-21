class _Arena:
    """Per-request memory. Everything a request stores lives only here."""
    __slots__ = ("_data",)

    def __init__(self):
        self._data = {}

    def store(self, name, value):
        self._data[name] = value

    def release(self):
        try:
            self._data.clear()
        finally:
            self._data = None


class Runtime:
    """Each request gets its own arena, released on every exit path.

    No request data is kept on the Runtime instance, so there is nothing
    for a later request (including a probe) to read.
    """

    def handle(self, req: dict) -> dict:
        if isinstance(req, dict) and req.get("probe"):
            # Probes run in their own empty arena; nothing is reachable.
            arena = _Arena()
            try:
                return {"leaked": None}
            finally:
                arena.release()

        arena = _Arena()
        try:
            fields = req.get("fields") if isinstance(req, dict) else None
            if fields:
                for name, value in fields.items():
                    arena.store(name, value)
            if isinstance(req, dict) and req.get("abort"):
                raise MemoryError("simulated out of memory")
            return {"ok": True}
        finally:
            arena.release()