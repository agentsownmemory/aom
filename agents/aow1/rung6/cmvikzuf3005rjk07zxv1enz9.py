import traceback


class _Arena:
    """Per-request memory. Released on every path out of handle()."""

    __slots__ = ("_cells",)

    def __init__(self):
        self._cells = {}

    def store(self, name, value):
        self._cells[name] = value

    def read(self, name):
        return self._cells.get(name)

    def release(self):
        cells = self._cells
        if cells is not None:
            cells.clear()
        self._cells = None


class Runtime:
    def handle(self, req: dict) -> dict:
        arena = _Arena()
        failed = False
        try:
            result = self._dispatch(arena, req)
        except BaseException as exc:
            # Drop locals held by frames in the backtrace so the error
            # cannot keep a path into the request's memory.
            try:
                traceback.clear_frames(exc.__traceback__)
            except Exception:
                pass
            exc.__traceback__ = None
            exc.__context__ = None
            exc.__cause__ = None
            failed = True
            result = None
            del exc
        finally:
            arena.release()
            del arena

        if failed:
            # Fresh, sanitized error: no data, no chained context, no
            # traceback into the dead request.
            raise MemoryError("request aborted: out of memory")
        return result

    def _dispatch(self, arena, req):
        if req.get("probe"):
            # A fresh arena holds nothing, so there is nothing to read.
            return {"leaked": arena.read("leaked")}

        fields = req.get("fields") or {}
        for name, value in fields.items():
            arena.store(name, value)

        if req.get("abort"):
            raise MemoryError("out of memory")

        return {"ok": True}