class _Arena:
    """Per-request memory. Everything a request stores lives here and nowhere else."""

    __slots__ = ("_data",)

    def __init__(self):
        self._data = {}

    def store(self, name, value):
        self._data[name] = value

    def release(self):
        # Drop every reference held by this arena.
        self._data.clear()
        self._data = None


class Runtime:
    """A worker whose requests each own a private arena.

    No request state is kept on the Runtime instance. The arena is created
    at the start of handle() and released in a finally block, so it is freed
    on success, on abort, and on any other exception (including MemoryError).
    A probe never touches shared state: there is none to read.
    """

    def handle(self, req):
        if isinstance(req, dict) and req.get("probe"):
            # No cross-request state exists, so there is nothing to leak.
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") if isinstance(req, dict) else None
            if fields:
                for name, value in fields.items():
                    arena.store(name, value)
            if isinstance(req, dict) and req.get("abort"):
                raise MemoryError("simulated out of memory during request")
            return {"ok": True}
        finally:
            arena.release()
            del arena