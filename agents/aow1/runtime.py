class _Arena:
    """Per-request memory. Owned by exactly one request and released on every exit path."""

    __slots__ = ("_data", "_open")

    def __init__(self):
        self._data = {}
        self._open = True

    def store(self, name, value):
        if not self._open:
            raise RuntimeError("arena released")
        self._data[name] = value

    def release(self):
        if self._open:
            self._open = False
            try:
                self._data.clear()
            finally:
                self._data = None


class Runtime:
    def handle(self, req: dict) -> dict:
        # Probe requests get a fresh arena too; there is no shared state to read,
        # so the answer is None by construction.
        arena = _Arena()
        try:
            if isinstance(req, dict) and req.get("probe"):
                return {"leaked": None}

            fields = {}
            if isinstance(req, dict):
                fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.store(name, value)

            if isinstance(req, dict) and req.get("abort"):
                raise MemoryError("simulated out of memory during request")

            return {"ok": True}
        finally:
            arena.release()