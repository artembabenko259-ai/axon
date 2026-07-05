window.AxonFallbackEN = {
  "meta": {
    "title": "AXON Documentation",
    "subtitle": "Project Bible v1.0",
    "footer": "AXON Release Candidate 1.0 — Local documentation portal"
  },
  "nav": {
    "intro": "Introduction",
    "commands": "Commands",
    "skills": "Skills System",
    "capabilities": "Capabilities"
  },
  "intro": {
    "title": "Introduction to AXON",
    "lead": "AXON is a stream-native AI coding agent for your terminal. It combines an OpenRouter-powered LLM, native file/shell tools, dynamic Skills, and a Zenith web dashboard — all orchestrated through a fast async CLI built on prompt_toolkit.",
    "sections": [
      {
        "id": "what-is-axon",
        "title": "What is AXON?",
        "paragraphs": [
          "AXON is not a chat wrapper around an API. It is a <strong>local agent runtime</strong> that lives in your project directory, understands your filesystem, respects your approvals, and extends itself through markdown-based Skills stored in <code>.axon/skills/</code>.",
          "The name reflects its purpose: an <strong>autonomous execution node</strong> — you describe intent, AXON plans (optionally), reads your code, writes files (with backup), runs shell commands (with permission), searches the web for fresh facts, and speaks back through Rich-formatted terminal output or the Zenith web UI via WebSocket bridge.",
          "<strong>Why stream architecture?</strong> Traditional blocking CLIs freeze while the model thinks. AXON uses <code>safe_async_print</code> and an async agent loop so tokens stream in real time, tool results render as panels, and Windows ANSI bleed is prevented — critical for developers on PowerShell who need a polished experience.",
          "<strong>Why OpenRouter?</strong> AXON is model-agnostic. Switch models with <code>/model</code> without reinstalling. Use Claude for reasoning, Llama for speed, or vision models for <code>/image</code> — your API key, your choice.",
          "AXON also ships with <strong>Project Memory</strong> (<code>.axon/memory.md</code>), invisible context injected into every LLM call; <strong>Time Machine</strong> backups before file overwrites with <code>/undo</code>; and <strong>Git intelligence</strong> via <code>/review</code> and <code>/commit</code>."
        ]
      },
      {
        "id": "architecture",
        "title": "Architecture Overview",
        "paragraphs": [
          "Understanding AXON's layers helps you debug issues and extend the system confidently."
        ],
        "list": [
          "<strong>main.py</strong> — Entry point. Owns the prompt session, slash commands, tool approval UI, and WebSocket bridge lifecycle.",
          "<strong>llm_client.py</strong> — OpenRouter client. Builds system prompts (base + memory + skills), runs the agent tool loop, handles plan/execute modes.",
          "<strong>skills/tools.py</strong> — Native tools: read_file, write_file, execute_shell, web_search. Approval gates on destructive actions.",
          "<strong>skills_manager.py</strong> — Loads SKILL.md files, parses YAML frontmatter, executes inline <code>!`command`</code> injections.",
          "<strong>bridge.py</strong> — WebSocket server on 127.0.0.1:8765 syncing chat with Zenith web dashboard.",
          "<strong>.axon/</strong> — Project-local data: skills, memory, backups, generated docs."
        ],
        "code": [
          {
            "lang": "text",
            "label": "Directory layout",
            "source": "your-project/\n├── main.py              # CLI entry\n├── llm_client.py        # Agent brain\n├── skills/\n│   ├── tools.py         # Native tools\n│   └── tasks.py         # Plan mode tools\n├── .axon/\n│   ├── skills/          # Your custom skills\n│   ├── memory.md        # Project context (optional)\n│   ├── backups/         # Time Machine snapshots\n│   └── docs/            # Auto-generated AST docs\n└── zenith-web/          # Next.js dashboard"
          }
        ]
      },
      {
        "id": "installation",
        "title": "Installation",
        "paragraphs": [
          "AXON requires Python 3.11+, an OpenRouter API key, and Git (optional, for /review and /commit)."
        ],
        "code": [
          {
            "lang": "powershell",
            "label": "Winget (recommended on Windows)",
            "source": "# Install Python if needed\nwinget install Python.Python.3.11\n\n# Clone or download AXON\ngit clone https://github.com/your-org/axon.git\ncd axon\n\n# Create virtual environment\npython -m venv venv\n.\\venv\\Scripts\\Activate.ps1\n\n# Install dependencies\npip install -r requirements.txt\n\n# Configure API key\ncopy .env.example .env\n# Edit .env: OPENROUTER_API_KEY=sk-or-..."
          },
          {
            "lang": "bash",
            "label": "Manual installation",
            "source": "git clone https://github.com/your-org/axon.git\ncd axon\npython3 -m venv venv\nsource venv/bin/activate\npip install -r requirements.txt\ncp .env.example .env\n# Set OPENROUTER_API_KEY in .env"
          }
        ],
        "callout": {
          "type": "warning",
          "text": "<strong>Windows note:</strong> AXON runs <code>colorama.just_fix_windows_console()</code> and uses <code>safe_async_print</code> to prevent ANSI escape codes from corrupting the prompt_toolkit input area. Always launch from a modern terminal (Windows Terminal recommended)."
        }
      },
      {
        "id": "quick-start",
        "title": "Quick Start",
        "paragraphs": [
          "After installation, navigate to any project directory and launch AXON. The agent uses your <strong>current working directory</strong> as its workspace — all file tools are relative to cwd."
        ],
        "code": [
          {
            "lang": "bash",
            "label": "Launch AXON",
            "source": "cd C:\\Projects\\my-app\npython path\\to\\axon\\main.py"
          },
          {
            "lang": "text",
            "label": "First session example",
            "source": "❯ You\nWhat files are in this project?\n\n✦ AXON\nI'll scan the project root...\n[Tool: Read] listing directory\n\nThe project contains main.py, config.json, and a zenith-web/ folder..."
          }
        ],
        "list": [
          "Type naturally — AXON will use read_file when it needs source code.",
          "Use <code>@filename</code> to attach file content to your message without the agent searching.",
          "Type <code>/plan refactor the auth module</code> to break work into steps before execution.",
          "Type <code>/help</code> anytime for the full command list."
        ]
      },
      {
        "id": "zenith-dashboard",
        "title": "Zenith Web Dashboard",
        "paragraphs": [
          "When AXON starts, it launches a WebSocket bridge on <code>127.0.0.1:8765</code>. The Zenith dashboard (<code>zenith-web/</code>) connects to this bridge for remote chat, model switching, token/cost stats, and live log streaming.",
          "<strong>Why both terminal and web?</strong> Terminal is fastest for keyboard-driven dev workflows. Web is ideal for presentations, pair sessions on a second monitor, or when you want the glass-morphism dashboard with the Agent Orb status indicator.",
          "Start the web UI separately: <code>cd zenith-web && npm run dev</code> — then open <code>http://localhost:3000</code>. Messages sync bidirectionally with the CLI."
        ]
      }
    ],
    "tryTerminal": {
      "title": "Try AXON",
      "initial": "$ python main.py\n\n    █████╗ ██╗  ██╗ ██████╗ ███╗   ██╗\n   ██╔══██╗╚██╗██╔╝██╔═══██╗████╗  ██║\n   ███████║ ╚███╔╝ ██║   ██║██╔██╗ ██║\n   ██╔══██║ ██╔██╗ ██║   ██║██║╚██╗██║\n   ██║  ██║██╔╝ ██╗╚██████╔╝██║ ╚████║\n   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝\n\nVersion: 1.0.0 │ Model: anthropic/claude-3.5-sonnet │ Status: READY\nType /help for commands • /exit to quit\n",
      "placeholder": "/help",
      "button": "Run command",
      "scenarios": {
        "/help": "AXON Commands\n  /help       List available slash commands\n  /exit       Exit AXON\n  /clear      Clear chat context\n  /plan       Plan Mode — break work into steps\n  /docs       Generate project documentation\n  /commit     AI-generated git commit\n  ...",
        "/plan refactor auth": "📋 Plan Mode activated\n\nGoal: refactor auth\n\n[1] ○ Audit current auth module structure\n[2] ○ Extract session logic into service\n[3] ○ Add tests for login flow\n[4] ○ Update imports across codebase\n\nType execute to begin.",
        "/cost": "Cost: $0.0042 · Tokens: 12847",
        "*": "AXON: Try /help, /plan refactor auth, or /cost"
      }
    }
  },
  "commands": {
    "title": "Slash Commands Reference",
    "lead": "Slash commands are intercepted locally by main.py — they never reach the LLM unless the command explicitly triggers one (e.g. /review, /commit). This keeps operations fast, deterministic, and free of token cost.",
    "reference": {
      "title": "Complete Command Table",
      "paragraphs": [
        "Every command below is registered in <code>ui/completer.py</code> and available via Tab completion. Arguments shown in angle brackets are required; square brackets are optional."
      ],
      "headers": {
        "command": "Command",
        "description": "What it does",
        "example": "Example"
      },
      "rows": [
        { "command": "/help", "description": "Print all slash commands with short descriptions", "example": "/help" },
        { "command": "/exit", "description": "Gracefully shutdown AXON and the WebSocket bridge", "example": "/exit" },
        { "command": "/clear", "description": "Reset conversation history while keeping system prompt, skills, and memory", "example": "/clear" },
        { "command": "/cost", "description": "Show session token count and estimated API cost", "example": "/cost" },
        { "command": "/usage", "description": "Alias for /cost", "example": "/usage" },
        { "command": "/compact", "description": "Summarize long context (placeholder — coming soon)", "example": "/compact" },
        { "command": "/model", "description": "Switch OpenRouter model; no args shows current model", "example": "/model anthropic/claude-3.5-sonnet" },
        { "command": "/plan", "description": "Plan Mode — agent creates 3-5 steps using create_plan tool only", "example": "/plan add dark mode toggle" },
        { "command": "/image", "description": "Load an image into vision context with optional prompt", "example": "/image screenshot.png describe UI bugs" },
        { "command": "/create-skill", "description": "Interactive wizard to scaffold a new SKILL.md", "example": "/create-skill" },
        { "command": "/review", "description": "Send git diff to LLM for code review", "example": "/review" },
        { "command": "/undo", "description": "Restore last file overwritten by write_file from backup", "example": "/undo" },
        { "command": "/commit", "description": "AI Conventional Commit message with y/n confirmation", "example": "/commit" },
        { "command": "/docs", "description": "Regenerate AST docs and serve portal at localhost:8000", "example": "/docs" }
      ]
    },
    "examples": [
      {
        "title": "/help — Discover commands",
        "input": "/help",
        "output": "AXON Commands\n  /help        List available slash commands\n  /exit        Exit AXON\n  /clear       Clear chat context (keeps system prompt)\n  /cost        Show session cost and token usage\n  /model       Switch model — e.g. /model anthropic/claude-3.5-sonnet\n  /plan        Plan Mode — /plan <description>\n  /docs        Generate and serve interactive project docs\n  ..."
      },
      {
        "title": "/plan + execute — Structured work",
        "input": "/plan add user authentication with JWT",
        "output": "📋 Plan created\n\n[1] ○ Design auth schema and token storage\n[2] ○ Implement login/register endpoints\n[3] ○ Add middleware and protected routes\n[4] ○ Write integration tests\n\nType execute, go, or run to start."
      },
      {
        "title": "/commit — Autonomous git commit",
        "input": "/commit",
        "output": "📝 Generating commit message...\n\n[?] Commit with message: \"feat: add JWT authentication middleware\"? (y/n)\ny\n[✓] [master abc1234] feat: add JWT authentication middleware\n 2 files changed, 87 insertions(+)"
      },
      {
        "title": "/undo — Time Machine restore",
        "input": "/undo",
        "output": "[✓] File config.json restored to previous state."
      }
    ],
    "sections": [
      {
        "id": "plan-mode",
        "title": "Plan Mode Deep Dive",
        "paragraphs": [
          "<strong>Why Plan Mode exists:</strong> Complex tasks fail when agents jump straight to write_file. Plan Mode forces the LLM to decompose work into 3-5 logical steps using only the <code>create_plan</code> tool — no file I/O, no shell.",
          "After planning, you review the TODO board printed in the terminal. Type <code>execute</code>, <code>go</code>, or <code>run</code> to enter Execute Mode where AXON works step-by-step, calling <code>complete_task</code> as it finishes each item.",
          "Plan state lives in <code>task_manager.py</code> and clears on <code>/clear</code>."
        ],
        "code": [
          {
            "lang": "text",
            "label": "Plan → Execute flow",
            "source": "❯ /plan migrate database to PostgreSQL\n\n✦ AXON creates plan...\n[Tool: Plan] create_plan\n\n📋 Migration Plan\n[1] ○ Export SQLite schema\n[2] ○ Create PostgreSQL tables\n[3] ○ Write data migration script\n[4] ○ Update connection strings\n\n❯ execute\n\n✦ AXON begins step 1..."
          }
        ]
      },
      {
        "id": "model-switching",
        "title": "Model Switching",
        "paragraphs": [
          "Models are persisted in <code>config.json</code> via <code>config_store.py</code>. Switching mid-session does not clear chat history.",
          "Use vision-capable models (e.g. GPT-4o, Claude 3.5 Sonnet) before <code>/image</code>. The LLM client encodes images as base64 data URLs in the message payload."
        ]
      },
      {
        "id": "file-mentions",
        "title": "@ File Mentions",
        "paragraphs": [
          "Type <code>@path/to/file.py</code> in your message to attach file contents. Directories attach a depth-2 tree listing. This is processed by <code>ui/file_context.py</code> before the message reaches the LLM.",
          "<strong>Why use @ instead of asking?</strong> Precision and speed — you control exactly what context enters the window, avoiding wasted tokens on wrong files."
        ],
        "code": [
          {
            "lang": "text",
            "label": "@ mention example",
            "source": "❯ Explain the bug in @src/auth/login.ts\n  📎 login.ts\n  [cyan]context[/] attached file data sent to AXON"
          }
        ]
      }
    ],
    "tryTerminal": {
      "title": "Try Slash Commands",
      "placeholder": "/plan add caching layer",
      "button": "Send",
      "scenarios": {
        "/plan add caching layer": "📋 Plan Mode\n\n[1] ○ Identify cacheable API responses\n[2] ○ Choose cache backend (Redis/in-memory)\n[3] ○ Implement cache middleware\n[4] ○ Add cache invalidation on writes\n\nType execute to begin.",
        "/model": "Current model: anthropic/claude-3.5-sonnet",
        "/clear": "[✓] Context cleared.",
        "/docs": "[✓] Docs available at http://localhost:8000",
        "*": "Try: /plan add caching layer, /model, /clear, /docs"
      }
    }
  },
  "skills": {
    "title": "Skills System",
    "lead": "Skills are AXON's plugin architecture — markdown instruction sets that become LLM-callable tools. Inspired by Claude Code's SKILL.md format, they let you package domain expertise, live shell context, and restricted tool access into reusable modules.",
    "sections": [
      {
        "id": "why-skills",
        "title": "Why Skills?",
        "paragraphs": [
          "Native tools (read, write, shell, search) are generic. Skills add <strong>opinionated workflows</strong>: a git-status skill knows to summarize branches and commits; a deploy skill knows your staging URL and health-check command.",
          "Skills live in your repo under <code>.axon/skills/</code> — they travel with the project, are version-controlled, and reload automatically when you send a message.",
          "<strong>Why markdown?</strong> Non-developers can author skills. YAML frontmatter configures tool exposure; the body is natural-language instructions the LLM follows when invoked."
        ]
      },
      {
        "id": "layout",
        "title": "Directory Layout",
        "paragraphs": [
          "Each skill is a folder with a <code>SKILL.md</code> file. Supporting files (scripts, templates, sample data) can live alongside it."
        ],
        "code": [
          {
            "lang": "text",
            "label": "Skill folder structure",
            "source": ".axon/skills/\n├── git-status/\n│   └── SKILL.md\n├── deploy-staging/\n│   ├── SKILL.md\n│   └── healthcheck.sh\n└── api-tester/\n    ├── SKILL.md\n    └── sample-payload.json"
          }
        ]
      },
      {
        "id": "frontmatter",
        "title": "YAML Frontmatter",
        "paragraphs": [
          "Frontmatter is parsed by <code>skills_manager.py</code> and controls how the skill appears to the LLM."
        ],
        "code": [
          {
            "lang": "markdown",
            "label": "SKILL.md frontmatter",
            "source": "---\nname: git-status\ndescription: Inspect git repository status and summarize recent activity\ndisable-model-invocation: false\nallowed-tools: execute_shell, read_file\n---"
          }
        ],
        "list": [
          "<strong>name</strong> — Tool name exposed to the LLM (defaults to folder name). Sanitized to alphanumeric/underscore.",
          "<strong>description</strong> — Shown in the tool schema. Write this for the model, not humans — be specific about when to invoke.",
          "<strong>disable-model-invocation</strong> — If <code>true</code>, skill is hidden from LLM tools (manual/slash trigger only).",
          "<strong>allowed-tools</strong> — Comma-separated list restricting which native tools the skill may use during invocation."
        ]
      },
      {
        "id": "inline-shell",
        "title": "Inline Shell Injection (!`command`)",
        "paragraphs": [
          "The killer feature of AXON Skills: before the skill body is sent to the LLM, every <code>!`command`</code> placeholder is executed locally and replaced with stdout/stderr output.",
          "<strong>Why?</strong> The model gets <em>live</em> project state without burning tool-call rounds. Branch name, last commits, test results — injected instantly.",
          "Commands run with a 30-second timeout. Output is capped at 16KB. Failed commands inject an error string so the model can adapt."
        ],
        "code": [
          {
            "lang": "markdown",
            "label": "Inline shell example",
            "source": "## Live context (auto-injected)\n\nBranch:\n!`git branch --show-current`\n\nLast 3 commits:\n!`git log -3 --oneline`\n\n## Instructions\n\n1. Summarize staged and unstaged changes.\n2. Mention the branch from context above."
          }
        ],
        "callout": {
          "type": "tip",
          "text": "Use platform-aware fallbacks in shell commands: <code>!`git branch --show-current 2>nul || git branch --show-current`</code> works on both Windows and Unix."
        }
      },
      {
        "id": "create-skill",
        "title": "Creating Skills",
        "paragraphs": [
          "Run <code>/create-skill</code> in AXON for an interactive wizard, or scaffold manually:"
        ],
        "code": [
          {
            "lang": "markdown",
            "label": "Complete SKILL.md example",
            "source": "---\nname: run-tests\ndescription: Execute project test suite and interpret failures\ndisable-model-invocation: false\nallowed-tools: execute_shell, read_file\n---\n\n# Test Runner Skill\n\n## Environment\n\nPython version:\n!`python --version`\n\n## Instructions\n\n1. Run `pytest -v` via execute_shell.\n2. If failures occur, read the failing test file.\n3. Summarize root cause and suggest fixes.\n4. Never modify source files without explicit user request."
          }
        ]
      },
      {
        "id": "supporting-files",
        "title": "Supporting Files",
        "paragraphs": [
          "Skills can reference sibling files in instructions: <em>\"Read sample-payload.json for the expected API shape\"</em>. The LLM uses read_file to load them when invoked.",
          "Keep supporting files small and focused. Large assets belong outside the skill folder."
        ]
      },
      {
        "id": "reload",
        "title": "Hot Reload",
        "paragraphs": [
          "Skills reload on every message via <code>llm_manager.reload_skills()</code>. Edit a SKILL.md while AXON is running — changes apply on the next turn without restart.",
          "The system prompt appends a skills summary block listing all available skill tools and their descriptions."
        ]
      }
    ],
    "tryTerminal": {
      "title": "Simulate Skill Invocation",
      "placeholder": "invoke git-status",
      "button": "Simulate",
      "scenarios": {
        "invoke git-status": "✦ AXON invokes skill: git-status\n\n[Injected context]\nBranch: feature/auth-refactor\n\nLast 3 commits:\nabc1234 feat: add JWT middleware\ndef5678 fix: token expiry check\n\n✦ AXON\nYou're on feature/auth-refactor with 2 staged files\nand 1 untracked config. Recent work focuses on JWT...",
        "*": "Type: invoke git-status"
      }
    }
  },
  "capabilities": {
    "title": "Capabilities",
    "lead": "Beyond slash commands and skills, AXON ships integrated subsystems for memory, search, vision, git, and safe file writes. This page explains each capability in depth — the problem it solves, how it works internally, and how to use it effectively.",
    "sections": [
      {
        "id": "project-memory",
        "title": "Project Memory (.axon/memory.md)",
        "paragraphs": [
          "<strong>Problem:</strong> Every new session starts cold. You re-explain architecture, naming conventions, and \"don't touch legacy_module.py\" — wasting tokens and risking mistakes.",
          "<strong>Solution:</strong> Create <code>.axon/memory.md</code> in your project root. AXON reads it on every message and injects it invisibly into the system prompt as <code>Project Context:</code>. It is never printed to the terminal.",
          "<strong>Why invisible?</strong> Project memory is for the model, not for cluttering your chat. You maintain it like a .cursorrules or AGENTS.md file."
        ],
        "code": [
          {
            "lang": "markdown",
            "label": ".axon/memory.md example",
            "source": "# Project Context\n\n- Stack: Python 3.11, FastAPI, PostgreSQL\n- Auth: JWT in HttpOnly cookies — never localStorage\n- Tests: pytest, run with `pytest -v`\n- Do NOT modify files in legacy/ — scheduled for removal Q3\n- API base URL staging: https://staging.example.com"
          }
        ],
        "callout": {
          "type": "tip",
          "text": "Memory reloads via <code>refresh_system_prompt()</code> on every message. Edit memory.md anytime — no restart needed."
        }
      },
      {
        "id": "web-search",
        "title": "Web Search",
        "paragraphs": [
          "<strong>Problem:</strong> LLMs have knowledge cutoffs. Library APIs change, CVEs publish, conference talks happen yesterday.",
          "<strong>Solution:</strong> The <code>web_search</code> native tool queries DuckDuckGo and returns the top 5 results with titles, URLs, and snippets. The agent decides when to search — typically for current events, fresh docs, or verifying facts.",
          "Implemented in <code>skills/tools.py</code> using <code>duckduckgo_search.DDGS</code>. No API key required.",
          "<strong>Why DuckDuckGo?</strong> Zero-config, privacy-respecting, sufficient for developer lookups. Results are formatted as plain text for the LLM context window."
        ],
        "code": [
          {
            "lang": "text",
            "label": "Example agent search",
            "source": "❯ What's the latest stable version of FastAPI?\n\n✦ AXON\n[Tool: Search] web_search(\"FastAPI latest stable version 2025\")\n\nFastAPI 0.115.x is the current stable release..."
          }
        ]
      },
      {
        "id": "vision",
        "title": "Vision (/image)",
        "paragraphs": [
          "<strong>Problem:</strong> Screenshots, mockups, and diagrams carry information text cannot capture.",
          "<strong>Solution:</strong> <code>/image &lt;path&gt; [prompt]</code> loads an image into the conversation as a base64 data URL. The LLM client detects media type from extension and appends a multimodal user message.",
          "Use vision-capable models. Optional prompt defaults to \"Analyze this image.\"",
          "Supported formats: PNG, JPEG, GIF, WebP."
        ],
        "code": [
          {
            "lang": "bash",
            "label": "Vision examples",
            "source": "/image design/mockup.png describe layout issues\n/image screenshots/bug.png what error is shown?\n/image"
          }
        ]
      },
      {
        "id": "git-integration",
        "title": "Git Integration",
        "paragraphs": [
          "AXON integrates git at two levels: <strong>review</strong> and <strong>commit</strong>.",
          "<strong>/review</strong> — Collects <code>git status</code> and <code>git diff</code>, sends to the LLM with a review-focused prompt. Ideal before opening a PR.",
          "<strong>/commit</strong> — Collects changes, asks the LLM for a single Conventional Commit message (no explanation), shows y/n confirmation via <code>run_in_terminal</code>, then runs <code>git commit -am</code>.",
          "<strong>Why confirm commits?</strong> Autonomous commits are powerful and dangerous. The y/n gate keeps you in control of git history.",
          "Git skills complement this: a git-status skill injects live branch/commit context via inline shell."
        ],
        "code": [
          {
            "lang": "text",
            "label": "/review flow",
            "source": "❯ /review\n\n🔍 Reviewing git changes...\n\n✦ AXON\n## Summary\n3 files changed in auth module.\n\n## Issues Found\n1. Missing null check in validate_token()...\n2. Hardcoded secret in test fixture — use env var..."
          }
        ]
      },
      {
        "id": "time-machine",
        "title": "Time Machine (Safe Write & /undo)",
        "paragraphs": [
          "<strong>Problem:</strong> Agents overwrite files. One bad write_file and your carefully crafted config is gone.",
          "<strong>Solution:</strong> Before <code>write_file</code> overwrites an existing file, <code>backup_manager.py</code> saves a copy to <code>.axon/backups/&lt;filename&gt;_&lt;timestamp&gt;.bak</code>. Global state tracks the last backup.",
          "<code>/undo</code> restores the most recent backup and prints confirmation. New files (no prior content) are not backed up.",
          "<strong>Why only last file?</strong> Simplicity for RC 1.0. The undo stack is single-depth — enough for \"oops, revert that write\" moments during agent sessions."
        ],
        "code": [
          {
            "lang": "text",
            "label": "Backup path example",
            "source": ".axon/backups/\n├── config.json_20260615_143022.bak\n└── main.py_20260615_143105.bak"
          }
        ]
      },
      {
        "id": "tool-approval",
        "title": "Tool Approval System",
        "paragraphs": [
          "Destructive tools — <code>write_file</code> and <code>execute_shell</code> — require user approval before execution.",
          "When the agent calls these tools, AXON pauses the loop and shows a Rich permission menu via <code>run_in_terminal</code>:",
          "1. Allow once — approve this invocation only",
          "2. Allow for session — whitelist the tool (or tool:detail prefix) until exit",
          "3. Deny — skip tool, agent receives denial message",
          "<strong>Why?</strong> Trust but verify. Read and search are safe; writes and shell can change your system."
        ]
      },
      {
        "id": "live-docs",
        "title": "Live Docs (/docs)",
        "paragraphs": [
          "<code>/docs</code> runs <code>scripts/docs_gen.py</code> which AST-parses Python files, indexes the project tree, writes <code>docs.json</code>, and serves documentation at <code>http://localhost:8000</code>.",
          "This portal (docs_site/) is the human-readable Bible. The auto-generated section below pulls live symbol data from docs.json.",
          "Run <code>/docs</code> after significant code changes to refresh the AST index."
        ]
      },
      {
        "id": "bridge",
        "title": "WebSocket Bridge",
        "paragraphs": [
          "<code>bridge.py</code> exposes AXON on <code>ws://127.0.0.1:8765</code>. The Zenith dashboard subscribes for chat messages, model changes, token stats, and log streaming.",
          "If port 8765 is in use, AXON starts anyway with a warning — terminal mode remains fully functional.",
          "Web-originated messages render with a 🌐 badge; terminal messages sync to the dashboard in real time."
        ]
      }
    ]
  },
  "autoDocs": {
    "title": "Auto-Generated Project Index",
    "paragraphs": [
      "The section below is populated from <code>data/docs.json</code>, produced by <code>scripts/docs_gen.py</code>. It reflects the current workspace — classes, functions, and file roles extracted via Python AST.",
      "Run <code>/docs</code> in AXON to regenerate. Click a module card to view signatures and docstrings."
    ],
    "unavailable": "No docs.json found. Run /docs in AXON or: python scripts/docs_gen.py"
  }
}
;