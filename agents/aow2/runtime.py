class Runtime:
    __slots__ = ()

    def handle(self, req: dict) -> dict:
        # This arena belongs exclusively to this invocation.
        arena = {}
        try:
            if req.get("probe", False):
                return {"leaked": next(iter(arena.values()), None)}

            fields = req.get("fields", {})
            if not isinstance(fields, dict):
                raise TypeError("fields must be a dictionary")

            for name, value in fields.items():
                arena[name] = value

            if req.get("abort", False):
                raise MemoryError("request aborted")

            return {"ok": True}
        finally:
            # Also runs on partial writes, aborts, and allocation failures.
            arena.clear()