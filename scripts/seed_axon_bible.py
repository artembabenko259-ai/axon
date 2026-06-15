#!/usr/bin/env python3
"""
Seed .axon/docs/content/{en,ru,ua}/ with 15 chapter JSON files (150 pages total).
Merge integration is separate — run scripts/merge_docs_content.py after seeding.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = ROOT / ".axon" / "docs" / "content"
LANGS = ("en", "ru", "ua")

# ---------------------------------------------------------------------------
# Chapter definitions: filename stem, section id/title/lead, 10 subsection topics
# ---------------------------------------------------------------------------

CHAPTERS: list[dict] = [
    {
        "file": "01_introduction",
        "section": {
            "id": "introduction",
            "title": "Introduction",
            "lead": "What AXON is, how to install it, and how the pieces fit together.",
        },
        "topics": [
            ("what-is-axon", "What is AXON?", "core agent"),
            ("install", "Installation", "setup"),
            ("quick-start", "Quick Start", "first run"),
            ("architecture", "Architecture Overview", "system design"),
            ("zenith", "Zenith Dashboard", "web UI"),
            ("bridge", "WebSocket Bridge", "bridge.py"),
            ("memory-overview", "Memory Overview", "memory.md"),
            ("tools-overview", "Tools Overview", "tooling"),
            ("eli5-glossary", "ELI5 Glossary", "terms"),
            ("first-session", "Your First Session", "walkthrough"),
        ],
        "examples": False,
        "sandbox_chapters": True,
    },
    {
        "file": "02_skills_masterclass",
        "section": {
            "id": "skills-masterclass",
            "title": "Skills Masterclass",
            "lead": "YAML recipes, plumbing pipes, anatomy, and anti-patterns.",
        },
        "topics": [
            ("yaml-recipe", "YAML Frontmatter — The Recipe Card", "yaml"),
            ("plumbing", "The ! Command — Plumbing System", "plumbing"),
            ("before-after", "Before / After Skills", "comparison"),
            ("create-skill", "/create-skill Wizard", "create skill"),
            ("inline-shell", "Inline Shell Injection", "inline shell"),
            ("allowed-tools", "allowed-tools Field", "tool allowlist"),
            ("hot-reload", "Hot Reload", "reload"),
            ("skill-anatomy", "Skill Anatomy", "structure"),
            ("anti-patterns", "Skill Anti-Patterns", "mistakes"),
            ("master-checklist", "Master Checklist", "checklist"),
        ],
        "examples": True,
        "sandbox_chapters": True,
    },
    {
        "file": "03_skills_examples",
        "section": {
            "id": "skills-examples",
            "title": "Skills Examples",
            "lead": "Ten complex multi-step skill walkthroughs you can copy and adapt.",
        },
        "topics": [
            ("web-research-writer", "Web Research Writer", "web research"),
            ("deploy-staging", "Deploy Staging Pipeline", "deploy"),
            ("test-fixer", "Test Failure Auto-Diagnosis", "pytest"),
            ("git-release-notes", "Git Release Notes Generator", "git release"),
            ("dependency-audit", "Dependency Audit Skill", "security audit"),
            ("api-scaffold", "REST API Scaffold", "scaffolding"),
            ("db-migration-helper", "Database Migration Helper", "migrations"),
            ("code-review-pack", "Code Review Pack", "review"),
            ("incident-runbook", "Incident Runbook Executor", "incident"),
            ("docs-sync", "Docs Sync Skill", "documentation"),
        ],
        "examples": True,
        "sandbox_chapters": False,
    },
    {
        "file": "04_agents_orchestration",
        "section": {
            "id": "agents-orchestration",
            "title": "Agents & Orchestration",
            "lead": "Sub-agents, delegation, system prompts, and when to specialize.",
        },
        "topics": [
            ("sub-agents-theory", "Sub-Agents Theory", "theory"),
            ("create-agent", "/create-agent", "scaffold"),
            ("delegate", "/delegate Command", "delegate"),
            ("system-prompt-md", "system_prompt.md", "prompt file"),
            ("agent-folders", "Agent Folder Layout", "folders"),
            ("when-to-delegate", "When to Delegate", "decision"),
            ("agent-naming", "Agent Naming Conventions", "naming"),
            ("delegate-limits", "Delegation Limits", "limits"),
            ("agent-isolation", "Agent Context Isolation", "isolation"),
            ("testing-agents", "Testing Your Agents", "testing"),
        ],
        "examples": True,
        "sandbox_chapters": True,
    },
    {
        "file": "05_chained_agents",
        "section": {
            "id": "chained-agents",
            "title": "Chained Agents & Commands",
            "lead": "Multi-command chains, pipelines, and failure recovery.",
        },
        "topics": [
            ("multi-command-amp", "Multi-Command Chains (&)", "ampersand"),
            ("chain-plan-delegate", "Chain: Plan + Delegate", "plan delegate"),
            ("reviewer-fixer-chain", "Reviewer + Fixer Chain", "review fix"),
            ("three-agent-pipeline", "Three-Agent Pipeline", "pipeline"),
            ("chain-failure-modes", "Chain Failure Modes", "failures"),
            ("quoting-ampersand", "Quoting & in Arguments", "quoting"),
            ("chain-error-handling", "Chain Error Handling", "errors"),
            ("chain-with-skills", "Chains with Skills", "skills chain"),
            ("chain-logging", "Chain Progress Logging", "logging"),
            ("chain-best-practices", "Chain Best Practices", "best practices"),
        ],
        "examples": True,
        "sandbox_chapters": True,
    },
    {
        "file": "06_advanced_commands",
        "section": {
            "id": "advanced-commands",
            "title": "Advanced Commands",
            "lead": "Every slash command in depth — plan, execute, git, docs, and more.",
        },
        "topics": [
            ("cmd-plan", "/plan", "plan"),
            ("cmd-execute", "/execute", "execute"),
            ("cmd-commit", "/commit", "commit"),
            ("cmd-review", "/review", "review"),
            ("cmd-undo", "/undo", "undo"),
            ("cmd-docs", "/docs", "docs"),
            ("cmd-image", "/image", "image"),
            ("cmd-model", "/model", "model"),
            ("cmd-clear", "/clear", "clear"),
            ("cmd-cost", "/cost", "cost"),
        ],
        "examples": True,
        "sandbox_chapters": True,
    },
    {
        "file": "07_plan_execute",
        "section": {
            "id": "plan-execute",
            "title": "Plan & Execute Mode",
            "lead": "Deep dive into task_manager, create_plan, and execution flow.",
        },
        "topics": [
            ("plan-mode-deep", "Plan Mode Deep Dive", "plan mode"),
            ("execute-mode", "Execute Mode", "execute mode"),
            ("task-manager", "task_manager.py", "task manager"),
            ("create-plan-tool", "create_plan Tool", "create_plan"),
            ("complete-task", "complete_task Tool", "complete_task"),
            ("plan-failures", "Plan Failure Modes", "plan failures"),
            ("plan-vs-execute", "Plan vs Execute Comparison", "comparison"),
            ("cancel-plan", "Canceling a Plan", "cancel"),
            ("multi-plan", "Multiple Plans in Session", "multi plan"),
            ("plan-with-delegate", "Plan + Delegate Combo", "combo"),
        ],
        "examples": True,
        "sandbox_chapters": True,
    },
    {
        "file": "08_git",
        "section": {
            "id": "git-workflows",
            "title": "Git Workflows",
            "lead": "Review, commit, conventional commits, skills, and pre-commit hooks.",
        },
        "topics": [
            ("git-review", "/review for Git", "review"),
            ("git-commit", "/commit AI Commits", "commit"),
            ("conventional-commits", "Conventional Commits", "conventional"),
            ("git-skills", "Git Skills", "git skills"),
            ("pre-commit-workflow", "Pre-Commit Workflow", "pre-commit"),
            ("git-status-skill", "git-status Skill", "status skill"),
            ("branch-workflow", "Branch Workflow", "branches"),
            ("merge-conflicts", "Merge Conflict Helper", "conflicts"),
            ("gitignore-tips", ".gitignore Tips", "gitignore"),
            ("git-undo", "Git + /undo Integration", "undo"),
        ],
        "examples": True,
        "sandbox_chapters": False,
    },
    {
        "file": "09_memory_context",
        "section": {
            "id": "memory-context",
            "title": "Memory & Context",
            "lead": "memory.md, @ mentions, file context, and context window management.",
        },
        "topics": [
            ("memory-md", "memory.md", "memory"),
            ("at-mentions", "@ File Mentions", "mentions"),
            ("file-context", "File Context Injection", "files"),
            ("context-window", "Context Window Budget", "window"),
            ("context-injection", "Injection Order", "injection"),
            ("context-pruning", "Context Pruning", "pruning"),
            ("at-syntax", "@ Syntax Variants", "syntax"),
            ("context-priority", "Context Priority", "priority"),
            ("token-budget", "Token Budget Tips", "tokens"),
            ("context-debugging", "Debugging Context", "debug"),
        ],
        "examples": False,
        "sandbox_chapters": False,
    },
    {
        "file": "10_web_vision",
        "section": {
            "id": "web-vision",
            "title": "Web & Vision",
            "lead": "web_search, DuckDuckGo, /image, vision models, and multimodal flows.",
        },
        "topics": [
            ("web-search", "web_search Tool", "web search"),
            ("duckduckgo", "DuckDuckGo Integration", "ddg"),
            ("slash-image", "/image Command", "image cmd"),
            ("vision-models", "Vision Models", "vision"),
            ("multimodal", "Multimodal Workflows", "multimodal"),
            ("image-analysis", "Image Analysis Workflow", "analysis"),
            ("screenshot-tools", "Screenshot Tools", "screenshot"),
            ("pdf-vision", "PDF & Document Vision", "pdf"),
            ("vision-limits", "Vision Limits", "limits"),
            ("web-fetch", "Web Fetch Patterns", "fetch"),
        ],
        "examples": True,
        "sandbox_chapters": True,
    },
    {
        "file": "11_tool_approval",
        "section": {
            "id": "tool-approval",
            "title": "Tool Approval & Security",
            "lead": "Write approval, shell approval, session allow, deny flow, and security.",
        },
        "topics": [
            ("write-approval", "write_file Approval", "write"),
            ("shell-approval", "execute_shell Approval", "shell"),
            ("session-allow", "Session Allow List", "allow"),
            ("deny-flow", "Deny Flow", "deny"),
            ("security-overview", "Security Overview", "security"),
            ("approval-ui", "Approval UI in Terminal", "UI"),
            ("yn-shortcuts", "y/n Shortcuts", "shortcuts"),
            ("allowlist-patterns", "Allowlist Patterns", "allowlist"),
            ("audit-log", "Audit Trail", "audit"),
            ("permission-escalation", "Permission Escalation", "escalation"),
        ],
        "examples": False,
        "sandbox_chapters": True,
    },
    {
        "file": "12_zenith_dashboard",
        "section": {
            "id": "zenith-dashboard",
            "title": "Zenith Dashboard",
            "lead": "WebSocket sync, chat, model selector, docs portal, and themes.",
        },
        "topics": [
            ("websocket", "WebSocket Connection", "websocket"),
            ("chat-sync", "Chat Sync", "chat"),
            ("model-selector", "Model Selector", "model"),
            ("docs-portal", "Docs Portal", "docs"),
            ("themes", "Themes & Styling", "themes"),
            ("sidebar-nav", "Sidebar Navigation", "sidebar"),
            ("session-history", "Session History", "history"),
            ("streaming-display", "Streaming Display", "streaming"),
            ("mobile-layout", "Mobile Layout", "mobile"),
            ("dark-mode", "Dark Mode Config", "dark mode"),
        ],
        "examples": False,
        "sandbox_chapters": False,
    },
    {
        "file": "13_troubleshooting",
        "section": {
            "id": "troubleshooting",
            "title": "Troubleshooting",
            "lead": "ANSI on Windows, port 8765, API keys, model errors, and bridge reconnect.",
        },
        "topics": [
            ("ansi-windows", "ANSI on Windows", "ansi"),
            ("port-8765", "Port 8765 Conflicts", "port"),
            ("api-key", "API Key Issues", "api key"),
            ("model-errors", "Model Errors", "model errors"),
            ("bridge-reconnect", "Bridge Reconnect", "reconnect"),
            ("venv-issues", "Virtual Environment Issues", "venv"),
            ("encoding-errors", "Encoding Errors", "encoding"),
            ("timeout-errors", "Timeout Errors", "timeout"),
            ("skill-not-found", "Skill Not Found", "skill missing"),
            ("bridge-firewall", "Firewall & Bridge", "firewall"),
        ],
        "examples": False,
        "sandbox_chapters": False,
    },
    {
        "file": "14_multi_agent_advanced",
        "section": {
            "id": "multi-agent-advanced",
            "title": "Multi-Agent Advanced",
            "lead": "Specialist agents, chained workflows, and orchestration patterns.",
        },
        "topics": [
            ("specialist-examples", "Specialist Agent Examples", "specialists"),
            ("chained-workflows", "Chained Workflows Config", "workflows"),
            ("orchestration-patterns", "Orchestration Patterns", "patterns"),
            ("planner-executor-reviewer", "Planner + Executor + Reviewer", "PER"),
            ("fan-out-pattern", "Fan-Out Pattern", "fan out"),
            ("agent-handoff", "Agent Handoff Files", "handoff"),
            ("cost-per-agent", "Cost Per Agent", "cost"),
            ("agent-registry", "Agent Registry", "registry"),
            ("parallel-delegates", "Parallel Delegation", "parallel"),
            ("orchestration-checklist", "Orchestration Checklist", "checklist"),
        ],
        "examples": True,
        "sandbox_chapters": False,
    },
    {
        "file": "15_reference_appendix",
        "section": {
            "id": "reference-appendix",
            "title": "Reference Appendix",
            "lead": "Command table, tool schema, file layout, env vars, and glossary.",
        },
        "topics": [
            ("command-table", "Slash Command Table", "commands"),
            ("tool-schema", "Tool Schema Reference", "tools"),
            ("file-layout", "Project File Layout", "layout"),
            ("env-vars", "Environment Variables", "env"),
            ("glossary", "Glossary", "glossary"),
            ("skill-schema", "Skill YAML Schema", "skill schema"),
            ("agent-schema", "Agent Folder Schema", "agent schema"),
            ("config-json", "config.json Keys", "config"),
            ("port-reference", "Port Reference", "ports"),
            ("version-history", "Version History Notes", "version"),
        ],
        "examples": True,
        "sandbox_chapters": False,
    },
]


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------


def _para(*blocks: str) -> str:
    return "\n\n".join(blocks)


def _theoretical_en(topic_title: str, focus: str, chapter_title: str) -> str:
    return _para(
        f"## Why {topic_title} matters\n\n"
        f"In any AI-assisted development workflow, **{focus}** is not a nice-to-have — "
        f"it is the difference between a toy demo and a tool you trust on real code. "
        f"AXON treats this topic as first-class because developers repeat the same "
        f"questions every session until the system encodes the answer once.",
        f"### Design principles\n\n"
        f"The {chapter_title} chapter exists because AXON is **local-first**: your files, "
        f"your terminal, your approval gates. That architecture pushes complexity to "
        f"explicit, inspectable mechanisms rather than hidden platform magic. "
        f"Understanding {focus} lets you predict what AXON will do before it does it.",
        f"### Mental model\n\n"
        f"Think of {focus} as a contract between you and the agent loop in `main.py` → "
        f"`llm_client.py`. The contract defines inputs (your message, memory, skills), "
        f"outputs (tool calls, streaming text), and failure boundaries (approval, timeout, "
        f"token limits). When the contract is clear, debugging becomes mechanical instead "
        f"of mystical.",
        f"### Further reading in this bible\n\n"
        f"Cross-link mentally to adjacent pages in this chapter and to the Reference "
        f"Appendix (Chapter 15) for tables and schemas. The goal is cumulative knowledge: "
        f"each page should make the next page faster to absorb.",
    )


def _markdown_en(topic_title: str, focus: str, chapter_file: str) -> str:
    cmd_hint = ""
    if chapter_file.startswith("06_") or "cmd-" in topic_title.lower():
        cmd_hint = (
            "\n\n### Invocation\n\n"
            "Type the slash command at the AXON prompt. Commands are handled locally in "
            "`main.py` via `command_parser.py` — they do not consume LLM tokens unless "
            "the command itself starts an agent turn."
        )
    return _para(
        f"## Practical deep-dive: {topic_title}\n\n"
        f"This section walks through **{focus}** the way you would explain it to a "
        f"teammate pairing on AXON for the first time. We cover the happy path, the "
        f"files involved, and the observability hooks you can use to verify behavior.",
        f"### Step-by-step workflow\n\n"
        f"1. **Prepare context** — ensure `.env` has `OPENROUTER_API_KEY`, project memory "
        f"in `.axon/memory.md` mentions any conventions for {focus}.\n"
        f"2. **Invoke** — use the CLI prompt or Zenith dashboard; both route through "
        f"the same bridge when connected.\n"
        f"3. **Observe** — watch terminal output for tool calls, approval prompts, and "
        f"chain progress markers (`⛓` for multi-command).\n"
        f"4. **Verify** — check filesystem changes, git status, or Zenith chat history.\n"
        f"5. **Iterate** — capture repeatable flows as skills under `.axon/skills/`.",
        f"### Key source files\n\n"
        f"| File | Role |\n|------|------|\n"
        f"| `main.py` | CLI loop, slash routing, approval UI |\n"
        f"| `llm_client.py` | OpenRouter agent loop, tool execution |\n"
        f"| `bridge.py` | WebSocket sync to Zenith (port 8765) |\n"
        f"| `skills_manager.py` | Skills + memory loading |\n"
        f"| `task_manager.py` | Plan/execute state |",
        f"### Tips for power users\n\n"
        f"- Combine with `&` chains when {focus} is one step in a longer pipeline.\n"
        f"- Prefer skills over repeating long natural-language instructions.\n"
        f"- Use `/cost` periodically during heavy sessions to track spend."
        + cmd_hint,
    )


def _theoretical_short(lang: str, topic_title: str, focus: str) -> str:
    if lang == "ru":
        return _para(
            f"## Зачем нужен раздел «{topic_title}»\n\n"
            f"**{focus}** — ключевая часть AXON: локальный агент, ваши файлы, явные "
            f"разрешения на опасные действия.",
            f"Понимание этой темы помогает предсказывать поведение `main.py` и "
            f"`llm_client.py` до запуска команды.",
        )
    return _para(
        f"## Навіщо розділ «{topic_title}»\n\n"
        f"**{focus}** — ключова частина AXON: локальний агент, ваші файли, явні "
        f"дозволи на небезпечні дії.",
        f"Розуміння теми допомагає передбачити поведінку `main.py` та "
        f"`llm_client.py` до запуску команди.",
    )


def _markdown_short(lang: str, topic_title: str, focus: str) -> str:
    if lang == "ru":
        return _para(
            f"## Практика: {topic_title}\n\n"
            f"1. Проверьте `.env` и `.axon/memory.md`.\n"
            f"2. Вызовите функцию через CLI или Zenith.\n"
            f"3. Следите за одобрениями и выводом инструментов.\n"
            f"4. Закрепите повторяемый сценарий в skill.",
            f"Основные файлы: `main.py`, `llm_client.py`, `bridge.py`, "
            f"`skills_manager.py`, `task_manager.py`.",
        )
    return _para(
        f"## Практика: {topic_title}\n\n"
        f"1. Перевірте `.env` та `.axon/memory.md`.\n"
        f"2. Викличте через CLI або Zenith.\n"
        f"3. Слідкуйте за схваленнями та виводом інструментів.\n"
        f"4. Закріпіть сценарій у skill.",
        f"Файли: `main.py`, `llm_client.py`, `bridge.py`, "
        f"`skills_manager.py`, `task_manager.py`.",
    )


def _eli5_en(topic_title: str, focus: str) -> str:
    return (
        f"Imagine {topic_title} is like a labeled drawer in your workshop toolbox. "
        f"The label says **{focus}** — so when you need that job done, you open exactly "
        f"this drawer instead of dumping every tool on the floor. AXON does the same: "
        f"it keeps this idea in a predictable place so you and the AI never guess."
    )


def _eli5_short(lang: str, topic_title: str) -> str:
    if lang == "ru":
        return (
            f"«{topic_title}» — как подписанный ящик в мастерской: открываешь нужный, "
            f"а не весь инструмент сразу. AXON хранит это предсказуемо."
        )
    return (
        f"«{topic_title}» — як підписана шухляда в майстерні: відкриваєш потрібну, "
        f"а не весь інструмент одразу. AXON зберігає це передбачувано."
    )


def _examples_en(sub_id: str, topic_title: str, focus: str) -> list[dict]:
    return [
        {
            "title": f"Minimal: {topic_title}",
            "markdown": _para(
                f"```text\n# Smallest useful invocation for {focus}\n"
                f"User: demonstrate {sub_id}\n```",
                f"Expected: AXON explains steps, uses read-only tools first, asks "
                f"before writes.",
            ),
        },
        {
            "title": f"With skill: {sub_id}-helper",
            "markdown": _para(
                f"```markdown\n---\nname: {sub_id}-helper\n"
                f"description: Automate {focus}\n"
                f"allowed-tools: read_file, execute_shell\n---\n\n"
                f"Run context:\n!`git status -sb`\n```",
                "Skill injects live git context before LLM instructions execute.",
            ),
        },
        {
            "title": f"Chained: plan then {sub_id}",
            "markdown": (
                f"```text\n/plan 'Improve {focus}' & /delegate reviewer Audit changes\n```\n\n"
                f"Chain runs plan first, then delegates review to specialist agent."
            ),
        },
        {
            "title": f"Failure recovery: {topic_title}",
            "markdown": _para(
                "If approval denied, AXON stops the tool call and reports which step failed.",
                "Re-run with narrower scope or pre-approve session for read-only shell.",
            ),
        },
        {
            "title": f"Zenith parity: {topic_title}",
            "markdown": (
                "Same prompt typed in Zenith web chat routes through `bridge.py` to "
                "identical handler in `main.py` — terminal and web stay in sync."
            ),
        },
    ]


def _failure_mode_en(topic_title: str, focus: str) -> dict:
    return {
        "title": f"When {topic_title} goes wrong",
        "markdown": _para(
            f"### Symptom\n\n"
            f"AXON hangs, returns empty output, or loops on {focus} without completing.",
            f"### Common causes\n\n"
            f"1. **Missing API key** — `OPENROUTER_API_KEY` not loaded from `.env`.\n"
            f"2. **Approval deadlock** — write/shell waiting for `y` but prompt scrolled away.\n"
            f"3. **Context overflow** — too many @ files attached; model truncates silently.\n"
            f"4. **Bridge desync** — Zenith connected but CLI restarted; refresh browser.\n"
            f"5. **Skill typo** — YAML `name` does not match folder or has invalid tools.",
            f"### Fix checklist\n\n"
            f"- Run `/clear` to reset conversation, keep memory.md.\n"
            f"- Check `python main.py` logs for stack traces.\n"
            f"- Verify port 8765 free: `netstat -an | findstr 8765` (Windows).\n"
            f"- Re-run with `/model` set to a stable default.\n"
            f"- Narrow task scope and retry one tool at a time.",
        ),
    }


def _failure_mode_short(lang: str, topic_title: str) -> dict:
    title = f"Ошибки: {topic_title}" if lang == "ru" else f"Помилки: {topic_title}"
    if lang == "ru":
        md = _para(
            "### Симптом\n\nПустой ответ, зависание или цикл.",
            "### Решение\n\n"
            "Проверьте `.env`, одобрения, `/clear`, порт 8765, имя skill.",
        )
    else:
        md = _para(
            "### Симптом\n\nПорожня відповідь, зависання або цикл.",
            "### Рішення\n\n"
            "Перевірте `.env`, схвалення, `/clear`, порт 8765, ім'я skill.",
        )
    return {"title": title, "markdown": md}


def _animation(sub_id: str, topic_title: str) -> dict:
    return {
        "id": f"anim-{sub_id}",
        "title": f"[ANIMATION: {topic_title}]",
        "description": (
            f"[ANIMATION: Hero panel for '{topic_title}' — left column shows ELI5 iconography, "
            f"center timeline steps light up sequentially, right column displays live code "
            f"snippets fading in. Cyan pulse on active step. Loop on scroll into view. "
            f"Sub-id: {sub_id}]"
        ),
        "trigger": "on-scroll-into-view",
    }


def _animations_array(sub_id: str, topic_title: str) -> list[dict]:
    return [
        _animation(sub_id, topic_title),
        {
            "id": f"anim-{sub_id}-flow",
            "title": f"[ANIMATION: Data flow — {topic_title}]",
            "description": (
                f"[ANIMATION: SVG diagram — User → main.py → llm_client → tools → "
                f"approval gate → response. Highlight path for {sub_id}. "
                f"Dots animate along edges for 2.5s loop.]"
            ),
            "trigger": "on-hover",
        },
    ]


def _steps_table(topic_title: str) -> dict:
    return {
        "title": f"{topic_title} — step trace",
        "headers": {"step": "Step", "what": "What happens", "who": "Who does it"},
        "rows": [
            {"step": "1", "what": f"User invokes {topic_title}", "who": "You"},
            {"step": "2", "what": "Parser routes to handler or LLM", "who": "command_parser.py"},
            {"step": "3", "what": "Tools/memory/skills assembled", "who": "llm_client.py"},
            {"step": "4", "what": "Destructive calls pause for approval", "who": "main.py"},
            {"step": "5", "what": "Result streams to terminal + Zenith", "who": "bridge.py"},
        ],
    }


def _sandbox(sub_id: str, topic_title: str) -> dict:
    key = f"/{sub_id.replace('cmd-', '')}" if sub_id.startswith("cmd-") else sub_id
    return {
        "title": f"Try: {topic_title}",
        "placeholder": key if key.startswith("/") else f"demo {sub_id}",
        "initial": "$ axon\nAXON v1.0.0 — Ready\nType /help for commands\n",
        "scenarios": {
            key if key.startswith("/") else f"demo {sub_id}": (
                f"✦ AXON\nDemonstrating {topic_title}...\n[Tool trace visible]\nDone."
            ),
            "/help": "AXON Commands — /plan /execute /delegate /create-skill ...",
            "*": f"Try: {key} or ask about {topic_title}",
        },
    }


def _build_subsection(
    lang: str,
    sub_id: str,
    topic_title: str,
    focus: str,
    chapter: dict,
    chapter_idx: int,
    sub_idx: int,
) -> dict:
    chapter_file = chapter["file"]
    chapter_title = chapter["section"]["title"]
    use_examples = chapter.get("examples", False)
    use_sandbox = chapter.get("sandbox_chapters", False) and (
        sub_idx < 3 or sub_id.startswith("cmd-")
    )

    if lang == "en":
        sub: dict = {
            "id": sub_id,
            "title": topic_title,
            "eli5": _eli5_en(topic_title, focus),
            "theoreticalFoundation": _theoretical_en(topic_title, focus, chapter_title),
            "markdown": _markdown_en(topic_title, focus, chapter_file),
            "failureMode": _failure_mode_en(topic_title, focus),
            "animations": _animations_array(sub_id, topic_title),
        }
        if use_examples:
            sub["examples"] = _examples_en(sub_id, topic_title, focus)
        if sub_idx % 2 == 0 or chapter_idx in (0, 5, 6):
            sub["stepsTable"] = _steps_table(topic_title)
        if use_sandbox:
            sub["sandbox"] = _sandbox(sub_id, topic_title)
        if sub_id == "before-after":
            sub["beforeAfter"] = {
                "before": {
                    "title": "Without structured skills",
                    "content": "Repeated instructions each session.\nInconsistent tool use.\nHigh token waste.",
                },
                "after": {
                    "title": "With AXON skills",
                    "content": "One SKILL.md invocation.\nPlumbing injects live data.\nPredictable output every time.",
                },
            }
    else:
        sub = {
            "id": sub_id,
            "title": topic_title,
            "eli5": _eli5_short(lang, topic_title),
            "theoreticalFoundation": _theoretical_short(lang, topic_title, focus),
            "markdown": _markdown_short(lang, topic_title, focus),
            "failureMode": _failure_mode_short(lang, topic_title),
            "animation": _animation(sub_id, topic_title),
        }
        if use_examples:
            sub["examples"] = [
                {"title": f"Пример: {topic_title}", "markdown": f"Минимальный сценарий для **{focus}**."}
                if lang == "ru"
                else {"title": f"Приклад: {topic_title}", "markdown": f"Мінімальний сценарій для **{focus}**."}
            ]

    return sub


def _build_chapter(lang: str, chapter: dict, chapter_num: int) -> dict:
    section = dict(chapter["section"])
    section["chapter"] = chapter_num
    section["subsections"] = [
        _build_subsection(
            lang,
            sub_id,
            title,
            focus,
            chapter,
            chapter_num - 1,
            idx,
        )
        for idx, (sub_id, title, focus) in enumerate(chapter["topics"])
    ]

    doc: dict = {"sections": [section]}

    if chapter_num == 1:
        if lang == "en":
            doc["meta"] = {
                "title": "AXON Knowledge Base",
                "lead": "The Ultimate Manual — Project Bible, ELI5 + deep dives.",
                "bookSubtitle": "Project Bible · Manual Mode · ELI5 Edition",
            }
        elif lang == "ru":
            doc["meta"] = {
                "title": "База знаний AXON",
                "lead": "Полное руководство — краткая русская версия.",
                "bookSubtitle": "Project Bible · RU",
            }
        else:
            doc["meta"] = {
                "title": "База знань AXON",
                "lead": "Повний посібник — стисла українська версія.",
                "bookSubtitle": "Project Bible · UA",
            }

    return doc


def seed_all() -> dict:
    stats: dict = {"files": [], "subsection_count": 0, "by_lang": {}}

    for lang in LANGS:
        lang_dir = CONTENT_ROOT / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        lang_count = 0

        for num, chapter in enumerate(CHAPTERS, start=1):
            doc = _build_chapter(lang, chapter, num)
            out_path = lang_dir / f"{chapter['file']}.json"
            out_path.write_text(
                json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            subs = len(doc["sections"][0]["subsections"])
            lang_count += subs
            stats["files"].append(str(out_path.relative_to(ROOT)))
            stats["subsection_count"] += subs

        stats["by_lang"][lang] = {"chapters": len(CHAPTERS), "subsections": lang_count}

    return stats


def main() -> None:
    stats = seed_all()
    print("AXON Bible seed complete.")
    print(f"  Chapter files per lang: {len(CHAPTERS)}")
    print(f"  Languages: {', '.join(LANGS)}")
    print(f"  Total files written: {len(stats['files'])}")
    print(f"  Subsections per lang: {stats['by_lang']['en']['subsections']}")
    print(f"  Grand total subsection records: {stats['subsection_count']}")
    print(f"  Output root: {CONTENT_ROOT}")
    print("\nFiles created:")
    for f in stats["files"]:
        print(f"  {f}")
    print("\nNext step (separate): python scripts/merge_docs_content.py")


if __name__ == "__main__":
    main()
