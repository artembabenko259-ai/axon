# AXON CLI

Agentic command-line AI assistant with multi-provider tool-calling, markdown skills, plan mode, sub-agents, and git helpers.

**Version:** 2.0.1  
**License:** GLWT (Good Luck With That) Public License

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
# Set OPENROUTER_API_KEY (or ANTHROPIC_API_KEY / OPENAI_API_KEY) in .env or config.json

axon          # fullscreen TUI (default)
axon repl     # Rich interactive REPL
python cli.py # direct invocation
```

## CLI commands

| Command | Description |
|---------|-------------|
| `axon` / `axon tui` | Fullscreen terminal UI (default) |
| `axon repl` | Interactive REPL with rich syntax highlighting and diffs |
| `axon -p "task"` | Headless single prompt execution (CI/scripts) |
| `axon doctor` | Environment diagnostics & hardware check |
| `axon version` | Print version |
| `axon multitask "goal"` | Orchestrator headless (parallel sub-agents) |
| `axon autopilot [on\|off\|status]` | Autopilot autonomous mode |
| `axon export [id]` | Export saved session to Markdown |
| `axon queue add "…"` | Queue background task |
| `axon serve` | Process background task queue |
| `axon watch [dir]` | Watch directory and run AXON on file changes |
| `axon schedule` | Scheduled tasks / timers |

### Headless execution

```bash
axon -p "summarize README.md" --cwd ./project
echo "refactor login.py" | axon -p --json
```

## Slash commands (REPL)

| Command | Description |
|---------|-------------|
| `/help` | List commands |
| `/exit` | Quit |
| `/clear` | Clear context |
| `/model <name>` | Switch active model |
| `/provider` | Configure LLM provider & API keys |
| `/cost` `/usage` | Session tokens and cost |
| `/compact` | Summarize old context |
| `/plan <desc>` | Plan mode |
| `execute` / `go` / `run` | Execute active plan |
| `/image <path>` | Load image for vision models |
| `/create-skill` `/gen-skill` | Create markdown skills |
| `/create-agent` `/delegate` | Sub-agents |
| `/multitask <goal>` | Orchestrator — parallel subtasks + synthesis |
| `/config` | View/edit runtime_policy |
| `/review` `/commit` `/undo` | Git workflows |
| `/system` | Session/global system prompts |
| `/sessions` `/resume` `/save` | Session persistence |
| `/export` | Export chat to Markdown |

Chain commands with `&`: `/clear & /plan refactor auth`

## Built-in Tools

- **File Operations**: `read_file`, `write_file`, `list_dir`, `glob_files`
- **Code Search & Editing**: `search_code` (ripgrep/python fallback), `apply_patch`, `view_diff`
- **Terminal Execution**: `execute_shell` (with safety policy & timeouts)
- **Web & Research**: `web_search`, `fetch_url`
- **Extensibility**: Custom Markdown skills (`.axon/skills/`) and MCP servers.

## Configuration

- `config.json` — Active provider, API keys, default model
- `%APPDATA%\AXON\runtime_policy.json` — Autonomy modes & safety limits
- `%APPDATA%\AXON\system_prompt.md` — Global system prompt
- `.axon/memory.md` — Project memory

