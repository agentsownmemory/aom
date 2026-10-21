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
    """A runtime where each request owns its own arena.

    The arena is created on entry to handle() and released in a finally block,
    so it is freed on every exit path: success, abort, or any other exception.
    No per-request state is kept on the Runtime instance, so there is nothing
    for a later request (probe or otherwise) to read.
    """

    def handle(self, req):
        # Probe requests never touch any request state; they get their own
        # (empty) arena like every other request, and nothing to read from it.
        arena = _Arena()
        try:
            if not isinstance(req, dict):
                return {"ok": False}

            if req.get("probe"):
                return {"leaked": None}

            fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.store(name, value)

            if req.get("abort"):
                # Model an out-of-memory crash mid request.
                raise MemoryError("simulated out of memory")

            return {"ok": True}
        finally:
            arena.release()
            del arena