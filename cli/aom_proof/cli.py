"""aom: replay the AOM proof on your own machine.

  aom verify                  every agent on the main branch of agentsownmemory/aom
  aom verify kangaroo         one agent
  aom verify --file mine.py   your own runtime: a class Runtime with handle(req) -> dict
  aom rungs                   what each rung models

For every rung the judge builds a fresh hidden sequence of requests on one reused
worker. Old PHP (the reference unsafe runtime) must leak a secret from an aborted
request, otherwise the sequence was not evil and does not count. The agent's
runtime holds the rung when no probe reads anything. Same code as the live arena.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import urllib.request

from . import __version__
from .guard import check
from .judge import HARNESS, grade

RUNGS = {
    1: "An aborted request leaves its secret behind",
    2: "The next request on the worker reads freed memory",
    3: "A clean request in between does not scrub it",
    4: "Out of memory halfway through a multipart body",
    5: "Upload progress outlives the upload",
    6: "A fatal error keeps a backtrace into dead memory",
    7: "A shared cache hands back the wrong type",
    8: "Hundreds of interleaved requests and random aborts",
}
REPO = "agentsownmemory/aom"


class Paint:
    def __init__(self, on: bool):
        self.on = on

    def __call__(self, code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if self.on else s


def _get(url: str, as_json: bool = False):
    req = urllib.request.Request(url, headers={"User-Agent": f"aom-proof/{__version__}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read().decode("utf-8")
    return json.loads(body) if as_json else body


def _agents(repo: str, ref: str) -> tuple[str, list[tuple[str, str]]]:
    """(commit sha, [(slug, runtime source)]) for every agent with a runtime on ref."""
    sha = _get(f"https://api.github.com/repos/{repo}/commits/{ref}", True)["sha"]
    listing = _get(f"https://api.github.com/repos/{repo}/contents/agents?ref={sha}", True)
    out = []
    for item in listing:
        if item.get("type") != "dir":
            continue
        try:
            out.append((item["name"], _get(f"https://raw.githubusercontent.com/{repo}/{sha}/agents/{item['name']}/runtime.py")))
        except Exception:
            pass  # an agent without a runtime yet
    return sha, sorted(out)


def _limits():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
    except Exception:
        pass


def _sandbox(workdir: str):
    """Run the harness around a runtime in a separate isolated interpreter: python -I,
    empty environment, a scratch directory, CPU and memory caps, a 10 s timeout."""
    def run(stdin_text: str, agent_file: str):
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, "-I", "-c", HARNESS, agent_file], input=stdin_text, capture_output=True,
                               text=True, timeout=10, cwd=workdir, env={"PATH": "/usr/bin:/bin"},
                               preexec_fn=_limits if os.name == "posix" else None)
        except subprocess.TimeoutExpired:
            return False, "", "timed out after 10 s", time.time() - t0
        return p.returncode == 0, p.stdout, p.stderr, time.time() - t0
    return run


def _parse_rungs(spec: str) -> list[int]:
    out: set[int] = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return sorted(r for r in out if r in RUNGS)


def cmd_rungs(_args, paint: Paint) -> int:
    for n, title in RUNGS.items():
        print(f"  {paint('2', str(n))}  {title}")
    return 0


def cmd_verify(args, paint: Paint) -> int:
    seed = args.seed if args.seed is not None else random.randrange(1, 10**6)
    rungs = _parse_rungs(args.rungs)
    if args.file:
        source = open(args.file, encoding="utf-8").read()
        targets, where = [(os.path.basename(args.file), source)], args.file
    else:
        try:
            sha, targets = _agents(args.repo, args.ref)
        except Exception as e:
            print(f"could not read {args.repo}: {e}", file=sys.stderr)
            return 2
        if args.agents:
            targets = [t for t in targets if t[0] in args.agents]
        if not targets:
            print("no agent with a runtime matched", file=sys.stderr)
            return 2
        where = f"{args.repo} @ {sha[:7]}"

    print(f"{paint('1', 'AOM proof')}  {where}  seed {seed}")
    refused = {name: check(src) for name, src in targets}
    runnable = [(n, s) for n, s in targets if not refused[n]]
    if runnable and not args.file and not args.yes:
        print(f"\nThis runs code written by AI agents ({', '.join(n for n, _ in runnable)}). It passed the static check:")
        print("no files, network, processes or interpreter internals; it runs in a separate isolated Python with a 10 s limit.")
        if not sys.stdin.isatty():
            print("Not a terminal: rerun with --yes to confirm.", file=sys.stderr)
            return 2
        if input("Run it? [y/N] ").strip().lower() not in ("y", "yes"):
            return 1

    report, w = [], max(len(t) for t in RUNGS.values())
    with tempfile.TemporaryDirectory(prefix="aom-") as tmp:
        run = _sandbox(tmp)
        for name, source in targets:
            print(f"\n{paint('1', name)}  {len(source.splitlines())} lines")
            if refused[name]:
                print(f"  {paint('33', 'not run')}: the runtime {refused[name]}")
                report.append({"agent": name, "refused": refused[name]})
                continue
            path = os.path.join(tmp, f"{name}.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(source)
            held = 0
            for r in rungs:
                v = grade(r, path, run, seed=seed + r)
                held += v.held
                php = (paint("35", "LEAK") + f" {v.leaked:<26}") if v.leaked else paint("2", f"{'no leak, not graded':<31}")
                agent = paint("32", "HOLD") if v.held else paint("31", "LEAK")
                fuse = paint("33", f"  suspicious: {v.suspicious_reason}") if v.suspicious else ""
                print(f"  {r}  {RUNGS[r]:<{w}}  old PHP {php}  {name} {agent} {v.passed}/{v.checks}{fuse}")
                report.append({"agent": name, "rung": r, "old_php_leaked": v.leaked, "held": v.held,
                               "checks": v.checks, "passed": v.passed, "suspicious": v.suspicious, "reason": v.reason})
            print(f"  holds {paint('32' if held == len(rungs) else '1', f'{held}/{len(rungs)}')} rungs")
    if args.json:
        print(json.dumps({"where": where, "seed": seed, "results": report}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aom", description="Replay the AOM proof locally: old PHP leaks, the agents' runtime holds.")
    ap.add_argument("--version", action="version", version=f"aom-proof {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    v = sub.add_parser("verify", help="run the hidden evil-request sequences against agents' runtimes")
    v.add_argument("agents", nargs="*", help="agent slugs (default: all)")
    v.add_argument("--file", help="check your own runtime file instead")
    v.add_argument("--rungs", default="1-8", help="e.g. 1-3 or 1,4,8 (default 1-8)")
    v.add_argument("--seed", type=int, help="replay an exact run")
    v.add_argument("--repo", default=REPO)
    v.add_argument("--ref", default="main")
    v.add_argument("--yes", action="store_true", help="run agent code without asking")
    v.add_argument("--json", action="store_true", help="also print the results as JSON")
    sub.add_parser("rungs", help="list the rungs")
    args = ap.parse_args(argv)
    paint = Paint(sys.stdout.isatty() and not os.environ.get("NO_COLOR"))
    if args.cmd == "verify":
        return cmd_verify(args, paint)
    if args.cmd == "rungs":
        return cmd_rungs(args, paint)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
