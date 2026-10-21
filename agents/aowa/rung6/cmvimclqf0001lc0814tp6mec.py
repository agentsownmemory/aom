import sys
import traceback


class _Arena:
    __slots__ = ("data",)

    def __init__(self):
        self.data = {}

    def store(self, fields):
        if isinstance(fields, dict):
            self.data.update(fields)

    def release(self):
        data = self.data
        self.data = None
        if data is not None:
            data.clear()


def _run(req):
    arena = _Arena()
    try:
        if req.get("probe"):
            return {"leaked": None}
        arena.store(req.get("fields"))
        if req.get("abort"):
            raise MemoryError()
        return {"ok": True}
    finally:
        arena.release()
        arena = None
        req = None


class Runtime:
    __slots__ = ()

    def handle(self, req: dict) -> dict:
        try:
            return _run(req)
        except BaseException:
            tb = sys.exc_info()[2]
            if tb is not None:
                traceback.clear_frames(tb)
            del tb
            req = None
            raise
        finally:
            req = None