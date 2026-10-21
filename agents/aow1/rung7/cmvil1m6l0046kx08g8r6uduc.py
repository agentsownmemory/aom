class Arena:
    """Per-request memory. Every request gets a brand new one."""

    __slots__ = ("_slots", "_open")

    def __init__(self):
        self._slots = {}
        self._open = True

    def store(self, name, value):
        if not self._open:
            raise RuntimeError("arena released")
        # Key by (type, name) so values are never returned as the wrong type.
        self._slots[(type(value), name)] = value

    def read(self, name):
        if not self._open:
            return None
        for (_, n), v in self._slots.items():
            if n == name:
                return v
        return None

    def release(self):
        self._slots.clear()
        self._open = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False  # propagate any exception after releasing


class Runtime:
    def handle(self, req: dict) -> dict:
        # No state lives on the Runtime: everything lives in the request arena,
        # which is released on every path out (success, abort, error).
        with Arena() as arena:
            if req.get("probe"):
                # Reads only this request's own (empty) arena.
                return {"leaked": arena.read("leaked")}

            fields = req.get("fields") or {}
            for name, value in fields.items():
                arena.store(name, value)

            if req.get("abort"):
                raise MemoryError("out of memory (simulated)")

            return {"ok": True}