class _Arena:
    """Per-request memory. Owned by exactly one request and released on every exit path."""

    __slots__ = ("_data", "_closed")

    def __init__(self):
        self._data = {}
        self._closed = False

    def store(self, name, value):
        if self._closed:
            raise RuntimeError("arena released")
        self._data[name] = value

    def release(self):
        if not self._closed:
            self._data.clear()
            self._closed = True
            self._data = None


class Runtime:
    def handle(self, req: dict) -> dict:
        # Probe: there is no shared state at all, so nothing can be read.
        if isinstance(req, dict) and req.get("probe"):
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.store(name, value)
            if req.get("abort"):
                raise MemoryError("simulated out of memory during request")
            return {"ok": True}
        finally:
            # Released on success, abort, or any other exception.
            arena.release()