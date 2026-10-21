class _Arena:
    """Per-request memory. Released on every exit path."""
    __slots__ = ("_data",)

    def __init__(self):
        self._data = {}

    def store(self, name, value):
        self._data[name] = value

    def release(self):
        data = self._data
        self._data = None
        if data is not None:
            data.clear()


class Runtime:
    def handle(self, req: dict) -> dict:
        # Probe: nothing is ever read from shared state, because no shared
        # state exists. Each request only ever sees its own arena.
        if isinstance(req, dict) and req.get("probe"):
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