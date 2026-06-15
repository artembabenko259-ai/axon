# AXON CLI

A modular terminal REPL with minimalist split-pane UI, AI chat via OpenRouter, streaming Markdown output, and a pluggable Skills system for function calling.

**Version:** 1.0.0

## UI

- **AXON branding** — pyfiglet ASCII logo with subtle gradient on startup
- **Sticky layout** — logo and status line fixed at top, `❯` prompt pinned at bottom
- **Split-pane** — scrollable chat between header and input
- **Status line** — `Version | Model | Status` updates live in the header
- **Themeable** — swap `CLITheme` in `ui/theme.py` without touching core logic

```
CLI/
├── main.py
├── bridge.py           # WebSocket bridge (CLI ↔ web dashboard)
├── controller.py       # REPL loop + layout orchestration
├── commands.py
├── llm_client.py
├── zenith-web/         # Next.js web control panel (package name: axon-web)
├── ui/
│   ├── theme.py        # CLITheme palette (swap to reskin)
│   ├── renderer.py     # UIRenderer split-pane layout
│   └── protocol.py     # UIOutput protocol
└── skills/
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set your OPENROUTER_API_KEY
```

## Usage

```bash
python main.py
```

AXON runs a simple terminal REPL: type a message, get an AI response, and see token usage for cost tracking.

Optional commands: `/help`, `/model <name>`, `/exit`

## Advanced UI mode

The `controller.py` module provides the full split-pane Rich UI (optional, not used by default `main.py`).

## Commands

| Command | Description |
|---------|-------------|
| `/help` | List available commands |
| `/model <name>` | Switch the active AI model |
| `/clear` | Clear the chat pane |
| `/skills` | List loaded skills |
| `/exit` | Exit the REPL |

Any input that does not start with `/` is sent to the AI as a chat message.

## Default Model

`meta-llama/llama-3.1-8b-instruct` (change with `/model <name>`).

## Skills

Built-in skills:

- **system_info** — Returns OS, machine, Python version, and local time.
- **file_read** — Reads a file by path (max 64 KB).

Skills are exposed to the LLM via OpenAI function-calling format and executed automatically during chat.

## Web Dashboard

```bash
cd zenith-web
npm install
npm run dev
```

The CLI starts a WebSocket bridge on `ws://127.0.0.1:8765` for real-time chat sync with the web panel.
