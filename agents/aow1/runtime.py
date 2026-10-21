class _Arena:
    """Per-request memory. Owns everything stored during one request."""
    __slots__ = ("_data",)

    def __init__(self):
        self._data = {}

    def store(self, name, value):
        self._data[name] = value

    def release(self):
        # Drop every reference the arena holds.
        self._data.clear()
        self._data = None


class Runtime:
    def __init__(self):
        # No request-visible state lives on the worker between requests.
        pass

    def handle(self, req: dict) -> dict:
        # Probe: there is no worker-level storage, so nothing can be read.
        if req.get("probe"):
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.store(name, value)
            if req.get("abort"):
                raise MemoryError("simulated out of memory mid-request")
            return {"ok": True}
        finally:
            # Released on every path out: success, abort, or OOM.
            arena.release()