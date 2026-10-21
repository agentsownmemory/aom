class _Arena:
    """Per-request memory. Everything a request stores lives here and nowhere else."""

    __slots__ = ("_data",)

    def __init__(self):
        self._data = {}

    def store(self, name, value):
        self._data[name] = value

    def release(self):
        # Drop every reference held by this arena.
        try:
            self._data.clear()
        finally:
            self._data = None


class Runtime:
    def handle(self, req: dict) -> dict:
        # A probe has no arena of its own and nothing shared to read.
        if isinstance(req, dict) and req.get("probe"):
            return {"leaked": None}

        arena = _Arena()
        try:
            fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.store(name, value)
                # An abort models an OOM crash partway through the body,
                # after some of the fields have already been stored.
                if req.get("abort") and len(arena._data) >= max(1, len(fields) // 2):
                    raise MemoryError("out of memory during multipart body")
            if req.get("abort"):
                raise MemoryError("out of memory")
            return {"ok": True}
        finally:
            # Released on every path out: success, abort, or OOM.
            arena.release()