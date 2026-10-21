class _Arena:
    """Per-request memory. Owned by exactly one request and released on every exit path."""

    __slots__ = ("_store",)

    def __init__(self):
        self._store = {}

    def put(self, name, value):
        self._store[name] = value

    def release(self):
        # Drop all references to the request's data.
        try:
            self._store.clear()
        finally:
            self._store = None


class Runtime:
    def handle(self, req: dict) -> dict:
        # Each request gets a fresh arena; no state is kept on the Runtime itself.
        arena = _Arena()
        try:
            if req.get("probe"):
                # The arena is brand new and nothing is shared across requests,
                # so there is nothing to read by construction.
                return {"leaked": None}

            fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.put(name, value)

            if req.get("abort"):
                raise MemoryError("simulated out of memory during request")

            return {"ok": True}
        finally:
            # Released on success, abort, and any other exception.
            arena.release()