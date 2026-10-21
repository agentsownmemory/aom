class _Arena:
    """Per-request memory. Everything a request stores lives here and nowhere else."""

    __slots__ = ("_data", "_open")

    def __init__(self):
        self._data = {}
        self._open = True

    def store(self, name, value):
        if not self._open:
            raise RuntimeError("arena released")
        self._data[name] = value

    def release(self):
        # Drop every reference held by this arena.
        try:
            self._data.clear()
        finally:
            self._data = None
            self._open = False


class Runtime:
    """A reused worker: no request state is held on the instance.

    Each call to handle() creates its own arena, and the arena is released in a
    finally block, so every exit path (success, abort, any exception, including
    MemoryError) frees the request's data. Probes never consult any stored
    state; there is none to find, because nothing is kept on the worker.
    """

    def handle(self, req):
        if isinstance(req, dict) and req.get("probe"):
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") if isinstance(req, dict) else None
            if fields:
                for name, value in fields.items():
                    arena.store(name, value)
            if isinstance(req, dict) and req.get("abort"):
                raise MemoryError("out of memory while handling request")
            return {"ok": True}
        finally:
            arena.release()