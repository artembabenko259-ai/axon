# AXON CLI

Agentic terminal REPL with OpenRouter tool-calling, markdown skills, plan mode, sub-agents, git helpers, and a Zenith web control panel.

**Version:** 1.0.0

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
# Set OPENROUTER_API_KEY in .env or via http://localhost:3000/config

axon          # interactive REPL (same as axon repl)
python cli.py # equivalent
python main.py # backward-compatible
```

## CLI commands

| Command | Description |
|---------|-------------|
| `axon` / `axon repl` | Interactive REPL with WebSocket bridge |
| `axon -p "task"` | Headless single prompt (CI/scripts) |
| `axon doctor` | Environment checks |
| `axon version` | Print version |
| `axon update` | Check runaxon.xyz for updates |
| `axon doctor --check-updates` | Doctor + update check |
| `axon web --open` | Dashboard and open browser |
| `axon tui` | Fullscreen terminal UI |
| `axon export [id]` | Export session to Markdown |
| `axon queue add "…"` | Queue background task |
| `axon serve` | Run background queue |
| `axon watch [dir]` | Run AXON when files change |
| `axon schedule` | Daily scheduled headless tasks |

### Headless

```bash
axon -p "summarize README.md" --cwd ./project
echo "task" | axon -p --json
```

## Slash commands (REPL)

| Command | Description |
|---------|-------------|
| `/help` | List commands |
| `/exit` | Quit |
| `/clear` | Clear context |
| `/model <name>` | Switch model |
| `/cost` `/usage` | Session tokens and cost |
| `/compact` | Summarize old context |
| `/plan <desc>` | Plan mode |
| `execute` / `go` / `run` | Execute active plan |
| `/image <path>` | Load image for vision models |
| `/create-skill` `/gen-skill` | Create markdown skills |
| `/create-agent` `/delegate` | Sub-agents |
| `/review` `/commit` `/undo` | Git workflows |
| `/docs` | Generate live docs |
| `/system` | Session/global system prompts |
| `/sessions` `/resume` `/save` | Session persistence |
| `/export` | Export chat to Markdown |

Chain commands with `&`: `/clear & /plan refactor auth`

## Tools

Built-in agent tools: `read_file`, `write_file`, `execute_shell`, `web_search`, `list_dir`, `search_code`, `glob_files`, `apply_patch`, plus plan tools and markdown skills.

## Web dashboard

```bash
axon web
# or: cd zenith-web && npm install && npm run dev
```

Open http://localhost:3000 — chat, dashboard, config, runtime policy (autonomy, bridge token).

Bridge: `ws://127.0.0.1:8765` (localhost only).

## Project layout

```
CLI/
├── cli.py              # Unified entrypoint
├── main.py             # Backward-compatible shim
├── ui/repl.py          # Interactive REPL
├── llm_client.py       # Agent loop + OpenRouter
├── bridge.py           # WebSocket hub
├── runtime_policy.py   # Autonomy & security
├── skills/             # Built-in tools
├── zenith-web/         # Next.js control panel
└── .axon/skills/       # User markdown skills
```

## Configuration

- `config.json` — API key, model (also editable in web UI)
- `%APPDATA%\AXON\runtime_policy.json` — autonomy, web control, bridge token
- `%APPDATA%\AXON\system_prompt.md` — global system prompt
- `.axon/memory.md` — project memory

## Build (Windows)

```bash
build.bat
```

See [INSTALL.md](INSTALL.md) for end-user setup.

Produces standalone `axon.exe` via PyInstaller + Inno Setup.

## Legacy

Legacy `controller.py` / `commands.py` stacks were removed — use `axon` / `ui/repl.py`.
