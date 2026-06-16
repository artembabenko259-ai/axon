# AXON PC roadmap (in progress)

Features being added incrementally. Orchestrator / MultiTask comes later.

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

## Next

- Wire plugins into REPL `/help`
- Tray icon + `axon serve` as Windows service
- VS Code / Cursor extension (overlay)
- Full TUI parity with REPL (bridge, slash commands)
- Zenith: notification + export UI

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
