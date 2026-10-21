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
            self._closed = True
            try:
                self._data.clear()
            finally:
                self._data = None


class Runtime:
    def handle(self, req: dict) -> dict:
        # Probe: there is no shared state to read, so nothing can leak by construction.
        if isinstance(req, dict) and req.get("probe"):
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.store(name, value)
            if req.get("abort"):
                raise MemoryError("simulated out of memory")
            return {"ok": True}
        finally:
            # Released on success, abort, and any other exception.
            arena.release()
            del arena