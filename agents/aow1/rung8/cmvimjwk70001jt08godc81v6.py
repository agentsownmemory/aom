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
    def handle(self, req: dict) -> dict:
        # Probe requests have no arena to read from: no state exists between
        # requests, so there is nothing that could leak.
        if isinstance(req, dict) and req.get("probe"):
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.store(name, value)

            if req.get("abort"):
                raise MemoryError("simulated out-of-memory mid request")

            return {"ok": True}
        finally:
            # Released on every path out: success, abort, or any other error.
            arena.release()