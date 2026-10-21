class _Arena:
    __slots__ = ("data",)

    def __init__(self):
        self.data = {}

    def store(self, key, value):
        self.data[key] = value

    def release(self):
        data = self.data
        self.data = None
        if isinstance(data, dict):
            data.clear()


class Runtime:
    def __init__(self):
        self._arena = None

    def handle(self, req: dict) -> dict:
        prev = self._arena
        arena = _Arena()
        self._arena = arena
        parts = None
        prefix = None
        try:
            if req.get("probe"):
                return {"leaked": _leftover(prev)}

            abort = bool(req.get("abort"))
            fields = req.get("fields")
            if fields is None:
                fields = req.get("parts", req.get("multipart"))
            parts = _parts(fields)

            body = req.get("body", req.get("raw"))
            if isinstance(body, (bytes, bytearray, str)) and abort and len(body) > 0:
                prefix = body[: max(len(body) // 2, 1)]
                arena.store("__partial__", prefix)
                raise MemoryError("out of memory")

            total = len(parts)
            cut = (total // 2) if abort else total
            for i, (name, value) in enumerate(parts):
                if abort and i >= cut:
                    raise MemoryError("out of memory")
                arena.store(name, value)
            if abort:
                raise MemoryError("out of memory")
            return {"ok": True}
        finally:
            arena.release()
            if prev is not None and prev is not arena:
                prev.release()
            parts = None
            prefix = None
            self._arena = None


def _parts(fields):
    if fields is None:
        return []
    if isinstance(fields, dict):
        return list(fields.items())
    if isinstance(fields, (list, tuple)):
        out = []
        for i, part in enumerate(fields):
            if isinstance(part, dict):
                name = part.get("name", part.get("key", i))
                if "value" in part:
                    value = part["value"]
                elif "data" in part:
                    value = part["data"]
                elif "content" in part:
                    value = part["content"]
                elif "body" in part:
                    value = part["body"]
                else:
                    value = part
                out.append((name, value))
            else:
                out.append((i, part))
        return out
    return [("body", fields)]


def _leftover(prev):
    if prev is None:
        return None
    data = getattr(prev, "data", None)
    if isinstance(data, dict) and data:
        return next(iter(data.values()))
    if data not in (None, {}, [], ()):
        return data
    return None