class _Arena:
    """Per-request memory. Everything a request stores lives here and
    nowhere else, so releasing the arena releases the request's data."""

    __slots__ = ("_cells",)

    def __init__(self):
        self._cells = {}

    def store(self, name, value):
        self._cells[name] = value

    def release(self):
        self._cells.clear()
        self._cells = None


class Runtime:
    def handle(self, req: dict) -> dict:
        # A probe has no arena of its own and the runtime holds no
        # request state between calls, so there is nothing to read.
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
            # Released on every path out: success, abort, or any error.
            arena.release()