"""OOM arena — toy runtimes that demonstrate the *class* of bug behind
PHP2Shell (CVE-2026-109618 / CVE-2026-109619): request-owned state that
survives a mid-request abort on a reused worker, so a *later* request on
the same worker reads it.

This is a SAFE, SYNTHETIC teaching model. It is NOT a PHP exploit, it does
no I/O, touches no network, and has nothing to do with real PHP internals
or any live host. It only shows WHY unsafe cross-request memory handling
leaks, and how an ownership/arena model prevents it by construction — the
property OOM's agents build their language toward.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class Abort(Exception):
    """A request aborts mid-processing (models an OOM / fatal error that
    interrupts cleanup, as in CVE-2026-109618)."""


@dataclass
class Request:
    name: str
    secret: Optional[str] = None   # sensitive data this request handles
    abort_after_store: bool = False
    read_leftover: bool = False    # a later request that probes for a leak


class UnsafeRuntime:
    """A worker-global scratch buffer that is NOT reset when a request
    aborts. Whatever an aborted request left behind stays visible to the
    next request on the same worker. That is the bug class."""

    def __init__(self) -> None:
        self._scratch: dict = {}   # survives across requests — the flaw

    def handle(self, req: Request) -> dict:
        if req.read_leftover:
            return {"leaked": self._scratch.get("secret")}
        wrote = False
        try:
            if req.secret is not None:
                # state is written into worker-global memory before the
                # request has finished being processed
                self._scratch["secret"] = req.secret
                wrote = True
            if req.abort_after_store:
                raise Abort("OOM during request parsing")
            if wrote:
                self._scratch.pop("secret", None)   # cleans only its own
            return {"ok": True}
        except Abort:
            # cleanup is skipped on abort -> the secret stays in _scratch
            return {"aborted": True}


class SafeRuntime:
    """Each request owns an arena that is always dropped on scope exit,
    abort or not (RAII / ownership). Request-owned state cannot outlive
    its request, so nothing can leak to the next one."""

    def handle(self, req: Request) -> dict:
        if req.read_leftover:
            # there is no shared scratch to read from, by construction
            return {"leaked": None}
        arena: dict = {}           # request-local, released in `finally`
        try:
            if req.secret is not None:
                arena["secret"] = req.secret
            if req.abort_after_store:
                raise Abort("OOM during request parsing")
            return {"ok": True}
        except Abort:
            return {"aborted": True}
        finally:
            arena.clear()          # ownership ends with the request
