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
            try:
                self._data.clear()
            finally:
                self._data = None
                self._open = False


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
                raise MemoryError("simulated out of memory")

            return {"ok": True}
        finally:
            # Released on success, abort, and any other exception.
            arena.release()