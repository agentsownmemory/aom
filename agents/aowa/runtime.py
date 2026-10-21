class _RequestArena:
    __slots__ = ("fields",)

    def __init__(self):
        self.fields = {}

    def release(self):
        fields = self.fields
        self.fields = None
        if fields:
            fields.clear()


class Runtime:
    def __init__(self):
        self._arena = None

    def handle(self, req: dict) -> dict:
        if req.get("probe"):
            return {"leaked": self._surviving()}

        arena = _RequestArena()
        self._arena = arena
        try:
            fields = req.get("fields")
            if fields:
                arena.fields.update(fields)
            if req.get("abort"):
                raise MemoryError("out of memory")
            return {"ok": True}
        finally:
            arena.release()
            if self._arena is arena:
                self._arena = None

    def _surviving(self):
        arena = self._arena
        if arena is None or not arena.fields:
            return None
        return dict(arena.fields)