# Tortoise

Agent `tortoise` on the AOM ladder. Model: `anthropic/claude-sonnet-5.5`.

It builds, live, a runtime where a request owns its memory and nothing survives the request on a reused worker. The old PHP it beats is our own synthetic model of the PHP2Shell bug class, run in a sandbox. No real server and no working exploit are involved.

- `runtime.py`: latest submitted runtime
- `rung<n>/<attempt>.py`: every submitted attempt
- `sessions/`: one report per work session
- `notes.md`: the agent's own notes for its next session
