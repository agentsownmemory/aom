class Arena:
    def __init__(self):
        self._cells = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False

    def put_all(self, fields):
        for key, value in fields.items():
            self._cells[key] = value

    def contents(self):
        if not self._cells:
            return None
        return dict(self._cells)

    def release(self):
        cells = self._cells
        self._cells = None
        if cells is not None:
            cells.clear()


class Runtime:
    def handle(self, req: dict) -> dict:
        with Arena() as arena:
            if req.get("probe") is True:
                return {"leaked": arena.contents()}
            fields = req.get("fields") or {}
            if fields:
                arena.put_all(fields)
            if req.get("abort"):
                raise MemoryError("out of memory")
            return {"ok": True}