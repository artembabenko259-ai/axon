# AXON PC roadmap (in progress)

## Done in this wave

| Feature | How to use |
|---------|------------|
| Sound alerts | Auto on approve + when agent finishes (disable in `runtime_policy.json`) |
| Export session | `/export` or `axon export [session_id]` |
| TUI | `axon tui` |
| Ollama | `config.json`: `"provider": "ollama"`, `"model": "llama3.2"` |
| Background queue | `axon queue add "task"` + `axon serve` |
| Watch folder | `axon watch .` |
| Scheduled tasks | `axon schedule add "git pull" --hour 9 --minute 0` |
| Plugins skeleton | `.axon/plugins/*.py` with `register()` |
| **Orchestrator** | `/multitask <goal>` — parallel sub-agents (see below) |

## Orchestrator / MultiTask

```text
/multitask review auth module, write tests, update README
/multitask --agents reviewer,axon audit security and summarize findings
```

1. AXON decomposes the goal into 2–5 subtasks (LLM JSON plan).
2. Each subtask runs in an isolated worker (`spawn_worker`) — main chat history stays clean.
3. Subtasks use `.axon/agents/<name>` when assigned, otherwise the main AXON agent.
4. A final synthesis merges outputs into one summary panel.

**Parallel mode:** set `"allow_parallel_agents": true` in `runtime_policy.json` (max 3 at once).  
When `false`, subtasks run sequentially (safer for approval prompts).

## Next (see DAY_PLAN.md for full day schedule)

Wave 2 in progress — execute `DAY_PLAN.md` phases A→G.

- [ ] Phase A: `axon multitask` CLI + `/config`
- [ ] Phase B: Plugins in REPL
- [ ] Phase C: Auto-save on exit
- [ ] Phase D: TUI parity
- [ ] Phase E: Tray + serve
- [ ] Phase F: Zenith orchestrator panel
- [ ] Phase G: VS Code / Cursor MVP

## Ollama setup

```json
{
  "provider": "ollama",
  "model": "llama3.2",
  "ollama_base_url": "http://127.0.0.1:11434/v1"
}
```

Run `ollama serve` locally, then `axon doctor`.

## Scheduled tasks on Windows

Task Scheduler → daily trigger → program: `axon` → arguments: `schedule run`
