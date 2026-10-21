class Runtime:
    def handle(self, req: dict) -> dict:
        # Request-owned arena. It is not stored on the worker, and the
        # context manager releases it on success and on abort alike.
        with _Arena() as arena:
            fields = req.get("fields")
            if isinstance(fields, dict):
                arena.update(fields)
            if req.get("abort"):
                raise MemoryError("out of memory")
            if req.get("probe"):
                leaked = next(iter(arena.values()), None) if arena else None
                return {"leaked": leaked}
            return {"ok": True}


class _Arena(dict):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.clear()
        return False