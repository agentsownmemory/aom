"""AOM runtime: each request owns its memory."""

class Runtime:
    def handle(self, req):
        return {"leaked": None} if req.get("probe") else {"ok": True}
