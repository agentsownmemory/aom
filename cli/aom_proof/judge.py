"""The judge: run an agent's runtime against a fresh hidden request sequence and
decide whether it holds the rung.

A rung is one evil pattern (see evil_requests / rungs on the web). A sequence is
a list of requests on ONE reused worker; some abort mid flight after storing a
secret, and probe requests then check whether any secret crossed into them.

The judge builds a sequence the agent has not seen (random secrets, order and
abort points), runs it against:
  - the reference unsafe runtime (old PHP) -> must LEAK, else the sequence was
    not evil and the rung does not count,
  - the agent's runtime            -> must let no probe read a secret.

The agent's runtime is arbitrary code, so it runs in the hard sandbox
(python3 -I, scrubbed env, timeout) via a tiny harness, never in this process.
The harness contract: the agent file defines `class Runtime` with
`handle(self, req) -> dict`; a probe request is `{"probe": True}` and must
return `{"leaked": <value or None>}`; a storing request carries
`{"fields": {...}, "abort": bool}`.
"""
from __future__ import annotations

import json
import random
import string
from dataclasses import dataclass, field

from .runtime import Request, UnsafeRuntime

SECRET_WORDS = [
    "admin-session-token", "db-password", "stripe-key-live", "jwt-signing-key",
    "api-key", "oauth-refresh", "csrf-token", "root-cookie",
]


def _rand_secret(rng: random.Random) -> str:
    base = rng.choice(SECRET_WORDS)
    tag = "".join(rng.choices(string.hexdigits.lower(), k=4))
    return f"{base}-{tag}"


@dataclass
class Sequence:
    """A hidden sequence of requests for one rung."""
    rung: int
    requests: list[dict]
    secrets: list[str]
    probe_indexes: list[int]

    @property
    def n_requests(self) -> int:
        return len(self.requests)

    @property
    def n_faults(self) -> int:
        return sum(1 for r in self.requests if r.get("abort"))


def build_sequence(rung: int, seed: int | None = None) -> Sequence:
    """A fresh hidden sequence whose difficulty grows with the rung.

    Every sequence stores at least one secret in an aborted request and then
    probes, so the unsafe runtime leaks. Higher rungs interleave more victims,
    clean requests and probes.
    """
    rng = random.Random(seed)
    n_victims = 1 + rung // 2
    n_clean = rung // 2
    reqs: list[dict] = []
    secrets: list[str] = []
    for _ in range(n_victims):
        s = _rand_secret(rng)
        secrets.append(s)
        reqs.append({"fields": {"secret": s}, "abort": True})
        for _ in range(rng.randint(0, n_clean)):
            reqs.append({"fields": {"x": "ok"}, "abort": False})
    # the last stored secret is the one a probe should be able to read on unsafe
    probe_count = 1 + rung // 3
    for _ in range(probe_count):
        reqs.append({"probe": True})
    rng.shuffle_hint = None  # keep order deterministic; probes stay at the end
    probe_indexes = [i for i, r in enumerate(reqs) if r.get("probe")]
    return Sequence(rung, reqs, secrets, probe_indexes)


def run_reference(seq: Sequence) -> str | None:
    """Run the unsafe reference runtime; return the secret a probe leaked, or None."""
    rt = UnsafeRuntime()
    leaked = None
    for r in seq.requests:
        req = Request(
            name="r",
            secret=r.get("fields", {}).get("secret"),
            abort_after_store=bool(r.get("abort")),
            read_leftover=bool(r.get("probe")),
        )
        out = rt.handle(req)
        if out.get("leaked"):
            leaked = out["leaked"]
    return leaked


# The harness that runs inside the sandbox around the agent's runtime file.
HARNESS = '''
import json, sys, importlib.util

spec = importlib.util.spec_from_file_location("agent_runtime", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
rt = mod.Runtime()

seq = json.load(sys.stdin)
leaked = []
for r in seq["requests"]:
    try:
        out = rt.handle(dict(r))
    except Exception:
        out = {}
    if r.get("probe"):
        v = (out or {}).get("leaked")
        leaked.append(v)
print(json.dumps({"leaked": leaked}))
'''


@dataclass
class Verdict:
    rung: int
    held: bool
    seconds: float
    leaked: str | None           # what old PHP leaked (proof the sequence was evil)
    checks: int                  # number of probes
    passed: int                  # probes that read nothing on the agent's runtime
    reason: str = ""
    suspicious: bool = False
    suspicious_reason: str = ""
    output: str = ""
    to_dict: dict = field(default_factory=dict)


def grade(rung: int, agent_file: str, run_in_sandbox, seed: int | None = None) -> Verdict:
    """run_in_sandbox(stdin_text, agent_file) -> (ok, stdout, stderr, seconds).

    It must execute `python3 -I -c HARNESS <agent_file>` with stdin, isolated.
    """
    seq = build_sequence(rung, seed)
    reference_leak = run_reference(seq)
    if not reference_leak:
        # our own sequence was not evil enough; rung cannot be graded
        return Verdict(rung, False, 0.0, None, len(seq.probe_indexes), 0,
                       reason="sequence did not make old PHP leak")

    ok, out, err, seconds = run_in_sandbox(json.dumps(seq.__dict__, default=list), agent_file)
    checks = len(seq.probe_indexes)
    if not ok:
        return Verdict(rung, False, seconds, reference_leak, checks, 0,
                       reason=(err or "runtime crashed").strip()[:200], output=(out + err)[:2000])
    try:
        got = json.loads(out.strip().splitlines()[-1])
        leaked_vals = got.get("leaked", [])
    except Exception:
        return Verdict(rung, False, seconds, reference_leak, checks, 0,
                       reason="runtime gave no readable result", output=out[:2000])

    passed = sum(1 for v in leaked_vals if not v)
    held = passed == checks and checks > 0

    # the fuse: a hold that looks too easy (the secret literal shows up in the
    # agent's own code, or it hard-codes the probe answer)
    suspicious = False
    sreason = ""
    try:
        code = open(agent_file, encoding="utf-8").read()
        for s in seq.secrets:
            if s in code:
                suspicious, sreason = True, "a secret literal appears in the runtime"
                break
    except Exception:
        pass

    return Verdict(rung, held, seconds, reference_leak, checks, passed,
                   reason="" if held else "a probe read a secret from an aborted request",
                   suspicious=suspicious, suspicious_reason=sreason, output=out[:2000])
