class _Arena:
    """Per-request memory. Owned by exactly one request and released on every exit path."""

    __slots__ = ("_data", "_closed")

    def __init__(self):
        self._data = {}
        self._closed = False

    def store(self, fields):
        if self._closed:
            raise RuntimeError("arena released")
        for k, v in (fields or {}).items():
            self._data[k] = v

    def release(self):
        if not self._closed:
            self._data.clear()
            self._closed = True
            self._data = None


class Runtime:
    """A reused worker. No request-derived state is held on the instance:
    each request allocates its own arena, which is released in a finally block
    on success, abort, or any other exception, so nothing outlives the request."""

    def handle(self, req: dict) -> dict:
        if isinstance(req, dict) and req.get("probe"):
            # Nothing is stored on the worker between requests, so there is
            # nothing to read by construction.
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") if isinstance(req, dict) else None
            arena.store(fields)
            if isinstance(req, dict) and req.get("abort"):
                raise MemoryError("simulated out of memory mid request")
            return {"ok": True}
        finally:
            arena.release()
            del arena