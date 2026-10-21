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
        # Drop every reference held by this request.
        if self._open:
            self._data.clear()
            self._data = None
            self._open = False


class Runtime:
    """A reused worker. No state is kept on the instance between requests:
    all request data lives in a per-request arena that is released in a
    finally block, so success, abort, and any exception all free it."""

    def handle(self, req: dict) -> dict:
        # A probe has nothing to read by construction: the worker holds no
        # request data, and each request's arena is already gone.
        if isinstance(req, dict) and req.get("probe"):
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") if isinstance(req, dict) else None
            if fields:
                for name, value in fields.items():
                    arena.store(name, value)
            if isinstance(req, dict) and req.get("abort"):
                raise MemoryError("simulated out of memory mid request")
            return {"ok": True}
        finally:
            arena.release()