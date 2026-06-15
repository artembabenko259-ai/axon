#!/usr/bin/env python3
"""
Generate chapter 16: Ultra Deep Dive — Skills, Commands & Content (20 pages).
Run: python scripts/generate_deep_dive_module.py
Then: python scripts/merge_docs_content.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_EN = ROOT / ".axon" / "docs" / "content" / "en" / "16_ultra_deep_dive_skills_commands.json"

EXPAND = """

### Deep Internal (recursive)

**main.py** receives input in `handle_single_input` or `chat_loop`. No background thread — asyncio single-threaded event loop. **Storage:** none on disk for routing decision; `stripped` string in stack frame only.

**llm_client.py** `messages` list is the sole conversation memory. Each `append` adds dicts. OpenRouter receives full list every `_agent_loop` iteration. Token growth is O(turns × context).

**Filesystem:** skills read at invoke time from path in `Skill.path`; mtime not cached — edit SKILL.md mid-session, next invoke sees new content after `reload_skills()` on next user message.

### Design comparison (expanded)

Claude Code popularized SKILL.md; AXON adopts same author format but couples to **local approval** and **inline shell without approval** — a deliberate tension. Authors must treat `!`cmd`` as pre-approved automation. Document this in every team skill README.

### Builder note

To reimplement: start with `invoke_skill` returning a string before wiring OpenRouter. Unit test `inject_shell_context` with fake subprocess. Only then add tool schema registration.
"""


def page(
    pid: str,
    title: str,
    eli5: str,
    theory: str,
    practical: str,
    failure: str,
    *,
    examples: list[dict] | None = None,
    animations: list[dict] | None = None,
    steps: dict | None = None,
    sandbox: dict | None = None,
) -> dict:
    p: dict = {
        "id": pid,
        "title": title,
        "eli5": eli5,
        "theoreticalFoundation": theory,
        "markdown": practical,
        "failureMode": {"title": f"When {title} breaks", "markdown": failure},
        "animations": animations
        or [
            {
                "id": f"anim-{pid}",
                "title": f"[ANIMATION: {title}]",
                "description": (
                    f"[ANIMATION: Scroll-triggered diagram for '{title}' — "
                    "state nodes pulse cyan, error branches flash red, "
                    "approval gate pauses timeline until user clicks Allow]"
                ),
                "trigger": "on-scroll-into-view",
            }
        ],
    }
    if examples:
        p["examples"] = examples
    if steps:
        p["stepsTable"] = steps
    if sandbox:
        p["sandbox"] = sandbox
    # Ultra-detail expansion on practical section
    if p.get("markdown"):
        p["markdown"] = p["markdown"] + EXPAND
    return p


PAGES = [
    page(
        "dd-module-map",
        "Deep Dive Module — Skills, Commands & Content Map",
        "This module is the X-ray of AXON. While other chapters teach what to type, these 20 pages show the skeleton: which file reads your keystroke, where the prompt is built, and where data is stored on disk.",
        """## Why a separate Deep Dive module exists

AXON is not a thin wrapper around an API. It is a **stateful agent runtime** with:
- An in-memory conversation (`LLMManager.messages`)
- Filesystem-backed skills (`.axon/skills/*/SKILL.md`)
- Filesystem-backed agents (`.axon/agents/*/system_prompt.md`)
- Ephemeral plan state (`task_manager.py`)
- Session-scoped approval cache (`approved_session_tools` in `skills/tools.py`)

Other AI CLIs hide this. AXON exposes it because **predictability beats magic** when you are debugging a runaway `write_file` at 2am.

### Comparison to other systems

| System | Skills | Slash commands | Local approval |
|--------|--------|----------------|----------------|
| AXON | SKILL.md + `!`shell`` | `main.py` intercept | Yes, write/shell |
| Claude Code | SKILL.md | Built-in | Varies |
| Raw OpenRouter API | None | None | None |

AXON's design choice: **slash commands never hit the LLM** unless explicitly LLM-backed (`/review`, `/commit`, `/delegate` task). That saves tokens and makes automation deterministic.

### Memory model (high level)

```
LLMManager.messages: list[dict]   # OpenAI chat format, grows per turn
task_manager.tasks: list[Task]    # plan mode only, cleared on /clear
SkillManager._skills: dict        # reloaded every message
approved_session_tools: set       # until /exit
```

No database. Everything is process-local except files you write.""",
        """## God Mode: end-to-end map

```
User keystroke
    │
    ▼
main.py chat_loop / process_user_message
    │
    ├─ '&' in text? ──► command_parser.split_command_chain()
    │                      └── sequential handle_single_input()
    │
    ├─ starts with '/'? ──► execute_slash_command()  [NO LLM]
    │       except /review, /commit, /delegate → LLM involved
    │
    └─ natural language ──► llm_manager.send_message_async()
            │
            ▼
        llm_client._agent_loop()
            ├─ messages[0] = system prompt (memory + skills summary)
            ├─ tools = native + task + skill schemas
            └─ tool call ──► _dispatch_tool()
                    ├─ skill? invoke_skill() + inject_shell_context
                    ├─ task? execute_task_tool()
                    └─ native? execute_tool() + approval gate
```

### Files you must know

| Path | Responsibility |
|------|----------------|
| `main.py` | Routing, approval UI, chain execution |
| `llm_client.py` | Prompt assembly, agent loop, delegation swap |
| `skills_manager.py` | Parse SKILL.md, inline shell, invoke |
| `skills/tools.py` | Native tools + approval |
| `command_parser.py` | `&` splitting |
| `agent_manager.py` | Sub-agent prompts |
| `task_manager.py` | Plan board state |""",
        """### Failure tree: module-level confusion

```
Symptom: "AXON ignored my slash command"
├─ Command typo → /help to list
├─ Command sent via web with wrong format → check bridge payload
├─ Chain split wrong → unbalanced quotes around &
└─ LLM path taken instead → line didn't start with /

Symptom: "Skill not in tool list"
├─ disable-model-invocation: true
├─ YAML parse error → check --- delimiters
├─ Folder missing SKILL.md
└─ reload_skills not called → send any message to refresh
```""",
    ),
    page(
        "dd-skill-filesystem",
        "Anatomy: Skill Filesystem Layout",
        "A skill is a folder with a recipe card (SKILL.md). AXON scans folders, not a database. Delete the folder — skill vanishes next reload.",
        """## Design history: why folders, not a registry DB

Early agent frameworks used JSON registries. AXON chose **git-friendly directories** because:
1. Skills travel with the repo (code reviewable)
2. No migration scripts when schema changes
3. Authors can add `helper.sh`, `template.json` beside SKILL.md

The cost: `SkillManager.reload()` walks disk every message. For typical projects (<50 skills) this is negligible (<5ms).""",
        """## Deep Internal: reload() walk

```python
# skills_manager.py — simplified
for skill_dir in sorted(root.iterdir()):
    skill_file = skill_dir / "SKILL.md"
    skill = parse_skill_file(skill_file)
    self._skills[skill.skill_id] = skill
    self._by_tool_name[sanitize_tool_name(skill.name)] = skill
```

**skill_id** = folder name (`git-status`)
**tool_name** = sanitized YAML `name` (falls back to folder)

### Disk layout

```
.axon/skills/
  git-status/
    SKILL.md          ← required
    helper.sh         ← optional, referenced in instructions
  web-research-writer/
    SKILL.md
    research/         ← output dir created by agent, not AXON
```

### Interaction with project memory

`load_project_memory()` reads `.axon/memory.md` **independently** of skills. Both inject into `messages[0]` system prompt. Skills additionally appear as **callable tools** with their own invoke payload.""",
        """### Failure tree: filesystem

```
Skill not found
├─ Wrong cwd → AXON uses Path.cwd(), cd to project root
├─ Typo in folder name vs YAML name
├─ SKILL.md not UTF-8 → parse may fail silently (returns None)
└─ Skill in user home but project elsewhere

Fix: ls .axon/skills/ && cat .axon/skills/<name>/SKILL.md
```""",
    ),
    # ... I'll continue with remaining pages in the script - use a loop for case studies
]

# Append remaining pages programmatically with full content
PAGES.extend([
    page(
        "dd-yaml-parser",
        "Anatomy: YAML Frontmatter Parser",
        "The recipe label on SKILL.md is parsed by a tiny custom parser — not PyYAML. It only understands keys, values, commas, and booleans.",
        """## Why custom YAML?

Dependency minimization. SKILL frontmatter is intentionally simple. A 80-line `_parse_simple_yaml` handles every production skill AXON ships.

### What gets parsed into memory

```python
@dataclass(frozen=True)
class Skill:
    skill_id: str           # folder name
    name: str               # from YAML
    description: str        # → OpenRouter tool description
    disable_model_invocation: bool
    allowed_tools: tuple[str, ...]
    body_raw: str           # markdown AFTER frontmatter
    path: Path              # absolute path to SKILL.md
```

**Memory allocation:** One `Skill` object per folder per reload. `body_raw` holds full file body as string (typically 1-8KB).""",
        """## God Mode: parse_frontmatter()

```
SKILL.md bytes on disk
    │
    ▼
read_text(utf-8)
    │
    ▼
regex ^---\\s*\\n(.*?)\\n---\\s*\\n?
    ├─ match → YAML block + body
    └─ no match → entire file is body, empty meta
    │
    ▼
_parse_simple_yaml() → dict
    │
    ▼
Skill dataclass frozen in SkillManager._skills
```

### LLM prompt construction impact

Only `description` and `tool_name` enter the **tools array** sent to OpenRouter. The full `body_raw` is NOT in the system prompt — it arrives only when the LLM **calls** the skill tool (via `invoke_skill` return value). This keeps system prompts small.""",
        """```
Parse returns None
├─ File unreadable (permissions)
├─ Empty file
└─ Rare: regex edge case with --- in body without opening ---

disable-model-invocation ignored
└─ Must be literal true/false in YAML (custom parser)

allowed-tools not enforced at runtime
└─ DOCUMENTED GAP: listed in invoke text, not blocked in execute_tool
    Fix: only document tools you trust; future: enforce in _dispatch_tool
```""",
    ),
    page(
        "dd-inline-shell",
        "Anatomy: Inline Shell Injection (`!`command`)",
        "Before the AI reads your skill, AXON runs shell commands hidden in the markdown and pastes the output in place — like a mail merge for terminal text.",
        """## Why inline shell exists

Without it, the LLM must burn tool rounds:
1. call execute_shell for git status
2. read output
3. reason

With `!`git status``, step 1-2 happen **before** the model sees the skill body. This is **eager evaluation** — a design pattern from static site generators (Jekyll) applied to agent instructions.

### Security boundary

Inline shell does **NOT** go through user approval. It runs at skill invoke time with AXON process permissions. **Never** put user-controlled text inside `!`...``.""",
        """## God Mode: inject_shell_context()

```python
INLINE_SHELL_PATTERN = re.compile(r"!`([^`]+)`")

def inject_shell_context(body: str) -> str:
    return INLINE_SHELL_PATTERN.sub(
        lambda m: run_inline_shell(m.group(1)), body
    )
```

### run_inline_shell internals

| Platform | Execution |
|----------|-----------|
| Windows | `subprocess.run(cmd, shell=True)` |
| Unix | `shlex.split(cmd)` then run |

Limits: `SHELL_TIMEOUT_SECONDS = 30`, `MAX_INLINE_OUTPUT = 16384`

### State chart

```
invoke_skill(tool_name)
    │
    ▼
load body_raw (frozen at reload)
    │
    ▼
inject_shell_context(body_raw)  ← mutates COPY as string
    │
    ▼
wrap in "# Skill activated" template
    │
    ▼
return str → appended as tool result message in messages[]
```

The hydrated string lives only in the conversation transcript — not written to disk unless the LLM later calls write_file.""",
        """```
(empty command) in output
└─ Placeholder was !`` or whitespace

command timed out after 30s
└─ Split long scripts; use read_file on cached log

truncated at 16KB
└─ Pipe through tail/head in the shell command

Windows vs Unix
└─ Use 2>nul || fallback pattern in skill templates
```""",
        animations=[
            {
                "id": "anim-plumbing-deep",
                "title": "[ANIMATION: Plumbing cross-section]",
                "description": "[ANIMATION: User drags SKILL.md to terminal → AXON displays 'Context Loaded' in blue → !`cmd` pipes glow → stdout drops into document preview panel]",
                "trigger": "on-hover",
            }
        ],
    ),
    page(
        "dd-invoke-skill-llm",
        "Anatomy: invoke_skill → LLM Message Construction",
        "When the AI 'calls' your skill, it doesn't run Python in the skill file — AXON returns a fat instruction string that becomes the next message in the chat history.",
        """## OpenAI message shape after skill call

```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "# Skill activated: git-status\\n\\n## Skill instructions\\n\\nBranch:\\nmain\\n..."
}
```

The model's **next** turn reads this as ground truth. Token cost = len(content). Heavy `!`shell`` output directly bills tokens.""",
        """## invoke_skill() template assembly

```python
sections = [
    f"# Skill activated: {skill.name}",
    "Follow the instructions below strictly...",
    "## Skill instructions",
    resolved_body.strip(),  # post-injection
]
if user_request:
    sections.extend(["## User request", user_request])
return "\\n".join(sections)
```

### allowed-tools: advisory vs enforced

The string says `(tools: execute_shell, read_file)` but `_dispatch_tool` does not filter native tools by skill. **The LLM can still call write_file** unless you rely on model discipline. Deep Internal note for contributors: enforcement belongs in `_dispatch_tool` future patch.

### Comparison

| Approach | Pros | Cons |
|----------|------|------|
| AXON invoke string | Simple, debuggable | Large tool results |
| MCP resources | Standardized | Extra server |
| RAG over SKILL.md | Smaller prompts | Stale, retrieval errors |""",
        """```
Skill returns empty
├─ body_raw only frontmatter
├─ All shell injections failed silently
└─ tool_name mismatch

Model ignores skill instructions
├─ Competing system prompt rules
├─ Skill body too long → truncated by model context
└─ Retry with shorter body; move detail to supporting files
```""",
    ),
    page(
        "dd-skill-tool-schema",
        "Anatomy: Skill Registration in OpenRouter Tool Schema",
        "Every invocable skill becomes a JSON function schema appended to read_file, write_file, etc. The LLM chooses when to call it based on description quality.",
        """## _get_all_tool_schemas() composition

```python
return (
    get_tools_schema()           # 4 native tools
    + get_task_tool_schemas()    # create_plan, complete_task
    + self._skill_manager.get_tool_schemas()  # 0..N skills
)
```

Plan mode filters to **only** `create_plan`.

### Schema shape per skill

```json
{
  "name": "git-status",
  "description": "Inspect git repository...",
  "parameters": {
    "properties": {
      "request": { "type": "string", "description": "Optional context" }
    }
  }
}
```

No required parameters — skills are always callable with `{}`.""",
        """## God Mode: from disk to API payload

```
reload_skills()
    │
    ▼
get_tool_schemas() per skill where not disable_model_invocation
    │
    ▼
_agent_loop() → client.chat.completions.create(tools=[...])
    │
    ▼
model returns tool_calls[]
    │
    ▼
_dispatch_tool("git-status", args)
```

### Persisted where?

Tool schemas are **ephemeral per request** — rebuilt each agent loop iteration after `reload_skills()`. Only SKILL.md on disk is persistent.""",
        """```
Skill missing from API tools list
├─ disable-model-invocation: true
├─ reload returned 0 (empty .axon/skills)
└─ OpenRouter model without tool support

Duplicate tool names
└─ sanitize_tool_name collision → rename folder or YAML name
```""",
    ),
    page(
        "dd-create-skill-cmd",
        "Deep Internal: /create-skill",
        "The wizard in main.py writes SKILL.md — it never touches the LLM except optionally reloading skills into the system prompt.",
        """## Routing

```python
# main.py execute_slash_command
if cmd == "/create-skill":
    await run_create_skill()
    return True  # handled locally
```

`run_create_skill` uses `run_in_terminal` for interactive `input()` when prompt_toolkit session is active — same pattern as tool approval.""",
        """## create_skill_file() disk write

```python
skill_dir = skills_root(workspace) / sanitize_skill_name(name)
skill_path = skill_dir / "SKILL.md"
skill_path.write_text(content, encoding="utf-8")
```

Then `llm_manager.reload_skills()` rescans disk and updates `messages[0]`.

### Console execution trace

```
❯ /create-skill
🛠 Creating a new AXON skill
Skill Name: check-logs
Description: Tail application logs and summarize errors
Auto-execute shell command: tail -50 logs/app.log
[✓] Skill created successfully! AXON can now use check-logs.
```

### ASCII: approval vs wizard

```
/create-skill ──► run_in_terminal(input prompts) ──► create_skill_file()
                                                         │
                                                         ▼
                                                    SKILL.md on disk
                                                         │
                                                         ▼
                                                    reload_skills()
```""",
        """```
Wizard empty name
└─ Validation in run_create_skill — required fields

Skill created but not callable
├─ AXON cwd != project cwd
├─ disable-model-invocation accidentally true in template
└─ Restart not needed — reload_skills on next message

Permission denied writing .axon/skills
└─ mkdir parents=True should handle; check antivirus locks
```""",
        sandbox={
            "title": "/create-skill trace",
            "placeholder": "/create-skill",
            "initial": "$ axon\n",
            "scenarios": {
                "/create-skill": "🛠 Creating a new AXON skill\nSkill Name: demo\n[✓] Skill created!"
            },
        },
    ),
    page(
        "dd-slash-router",
        "Deep Internal: Slash Command Router in main.py",
        "Every line starting with / is parsed before the LLM unless it's part of a quoted & chain segment.",
        """## execute_slash_command vs handle_single_input

- `execute_slash_command` — returns bool, used for pure slash
- `handle_single_input` — also handles /plan prefix, /delegate, natural language

Special cases **outside** execute_slash_command:
- `/plan <desc>` → `run_plan_mode` (LLM with create_plan only)
- `/delegate` → `run_delegate` (sub-agent swap)
- `/commit` → `run_commit` (LLM one-shot + git)""",
        """## God Mode dispatch table

| Input pattern | Handler | LLM? | Persists |
|---------------|---------|------|----------|
| `/help` | emit list | No | No |
| `/clear` | reset messages[1:] | No | No |
| `/plan x` | send_plan_async | Yes | task_manager |
| `/delegate a t` | send_delegated_async | Yes | No swap persist |
| `/commit` | generate_commit_message | Yes | git commit |
| `/undo` | backup_manager | No | restores file |
| natural | send_message_async | Yes | messages[] |

### & chain overlay

```python
if is_command_chain(stripped):
    for part in split_command_chain(stripped):
        await handle_single_input(part, ...)
```

Order is **left-to-right**. No parallelism.""",
        """```
Unknown command
└─ Falls through to emit yellow warning — does NOT reach LLM

/plan without description
└─ Usage hint only

Chain stops mid-way
├─ Earlier segment raised shutdown
├─ User /exit in chain (unlikely)
└─ Exception in LLM segment — later segments still run unless exception propagates
```""",
    ),
    page(
        "dd-plan-deep",
        "Deep Internal: /plan and task_manager",
        "Plan mode flips a global flag that restricts the tool schema to a single function: create_plan.",
        """## task_manager state

```python
task_manager.plan_mode = True   # during send_plan_async
task_manager.execution_mode = True  # during send_execute_async
task_manager.tasks: list[Task]  # id, name, status
task_manager.goal: str
```

Cleared on `/clear`.""",
        """## send_plan_async prompt injection

Hard-coded user message forces planning behavior. Tools filtered:

```python
if task_manager.plan_mode:
    return [schema for schema in get_task_tool_schemas()
            if name == "create_plan"]
```

### execute / go / run

Natural language triggers `run_execute_mode` → `send_execute_async` with full tool schema restored.

### ASCII state machine

```
[idle] --/plan--> [plan_mode] --create_plan--> [has_plan]
[has_plan] --execute--> [execution_mode] --complete_task*--> [idle or done]
```""",
        """```
Plan empty after /plan
├─ Model didn't call create_plan — retry with clearer description
├─ Wrong model (no tool support)
└─ API error — check /cost and logs

execute does nothing
└─ task_manager.has_plan() false — run /plan first

Tasks stuck not done
└─ Model never calls complete_task — nudge in natural language
```""",
    ),
    page(
        "dd-delegate-deep",
        "Deep Internal: /delegate and Agent Prompt Swap",
        "Delegation temporarily replaces messages[0] with the sub-agent's system_prompt.md while keeping the same tool surface.",
        """## agent_manager layout

```
.axon/agents/code-reviewer/system_prompt.md
```

`load_agent_prompt(name)` reads file or returns None.""",
        """## send_delegated_async lifecycle

```python
original_system = self.messages[0]["content"]
self.messages[0]["content"] = self._build_agent_system_prompt(agent_prompt)
try:
    return await self._agent_loop(payload)
finally:
    self.messages[0]["content"] = original_system
```

**Critical:** Conversation history remains — only system role swaps. Sub-agent sees prior turns unless you `/clear`.

### vs skills

| | Skill | Sub-agent |
|---|-------|-----------|
| Trigger | LLM tool call | /delegate slash |
| Prompt source | SKILL.md body on invoke | system_prompt.md replaces system |
| Persistence | Per invoke | Per delegate call |""",
        """```
Agent not found
└─ Check .axon/agents/<name>/system_prompt.md exists

Delegate seems like main AXON
├─ Prompt swap failed — agent file empty
└─ Main personality strong in conversation history

Forgot to create agent
└─ /create-agent wizard first
```""",
    ),
    page(
        "dd-amp-chain-deep",
        "Deep Internal: Multi-Command `&` Parser",
        "The ampersand splitter is a character scanner with quote awareness — not shell parsing.",
        """## Why not shlex.split the whole line?

Because `/plan 'a & b' & /help` must split into TWO commands, not three. The `&` inside quotes is literal.""",
        """## Algorithm (command_parser.py)

```
state: buf, quote=None
for each char:
  if in quote: handle close quote
  elif char is quote: enter quote
  elif char is &: flush buf as segment
  else: append to buf
```

Returns single-element list if no split occurred (optimization).

### Real chain console

```
❯ /plan 'Fix auth bug' & /delegate reviewer Audit auth module
⛓ Running 2 chained commands…
── Chain 1/2 ──
[plan output...]
── Chain 2/2 ──
🤖 Sub-agent reviewer working...
```""",
        """```
Chain split wrong
├─ Unmatched quote → entire line one segment
├─ & without spaces OK: /a&/b still splits
└─ Nested quotes not supported — use one quote style

Second command never runs
└─ First command hung on approval — answer y/n
```""",
    ),
    page(
        "dd-commit-deep",
        "Deep Internal: /commit",
        "Git status + diff feed a one-shot LLM call with no tools; user confirms before git commit -am.",
        """## collect_git_changes()

Runs `git status` and `git diff` via subprocess in project cwd.

## generate_commit_message_async()

Separate API call — does NOT use agent loop or tools. Strict system prompt: return ONLY message.""",
        """## Console flow

```
❯ /commit
📝 Generating commit message...
[?] Commit with message: "feat: add JWT middleware"? (y/n)
y
[✓] [master abc1234] feat: add JWT middleware
```

`run_in_terminal` wraps y/n prompt when CLI session active.""",
        """```
Not a git repository
└─ collect_git_changes error message

Empty diff
└─ Nothing to commit message

User says n
└─ Cancelled — no git side effects

commit -am skips untracked
└─ git add needed first — document in workflow
```""",
    ),
    page(
        "dd-at-mentions-deep",
        "Deep Internal: @ File Context + Skills/Commands",
        "When you type @src/app.ts in a message, file content is injected BEFORE the LLM sees your text — separate from skills but part of the same prompt budget.",
        """## ui/file_context.py role

`build_file_context(stripped, workspace)` regex-matches `@path` tokens, reads files or directory trees (depth 2), prepends to user payload in `send_message_async`:

```python
payload = f"{user_text}\\n\\n---\\n[Context attached]\\n{file_context}"
```

Not stored on disk. Not a skill. Ephemeral per message.""",
        """## Interaction with skills and slash commands

| Path | @ mentions attached? |
|------|---------------------|
| Natural language | Yes, via handle_single_input |
| /delegate task | Yes, on task string |
| /plan desc | No file_context in run_plan_mode |
| /create-skill | No |
| Skill invoke | LLM may read_file separately |

### ASCII: message assembly

```
User: "Fix bug in @auth/login.ts"
        │
        ▼
build_file_context() ──► file bytes in RAM
        │
        ▼
messages.append(user, payload with file + question)
        │
        ▼
_agent_loop → may ALSO call read_file (duplicate awareness)
```

### Why duplicate reads happen

The model may not trust attached context and call read_file anyway. Cost: extra tokens + approval-free read.""",
        """```
@file not found
└─ Regex didn't match path — check chars allowed [a-zA-Z0-9_./\\\\-]

Huge directory @src/
└─ Depth-2 tree still large — narrow path

Context overflow
└─ Attach fewer/smaller files; use skills with targeted !`shell`
```""",
    ),
])

# Five case studies — each heavy
CASE_STUDIES = [
    (
        "dd-case-web-research",
        "Case Study 1: Web Research → Read → Summarize → File",
        "web-research-writer",
    ),
    (
        "dd-case-deploy",
        "Case Study 2: Deploy Staging Pipeline Skill",
        "deploy-staging",
    ),
    (
        "dd-case-test-fixer",
        "Case Study 3: Test Failure Auto-Diagnosis",
        "test-fixer",
    ),
    (
        "dd-case-chain-pdc",
        "Case Study 4: Plan → Delegate → Commit Chain",
        "chain-pdc",
    ),
    (
        "dd-case-skill-at-search",
        "Case Study 5: Skill + @ Mention + web_search",
        "skill-at-search",
    ),
]

for pid, title, key in CASE_STUDIES:
    PAGES.append(
        page(
            pid,
            title,
            f"This case study follows {key} from business problem through AXON internals to failure branches — the way a staff engineer would document a production playbook.",
            f"""## Problem (Why we need this)

Production teams repeatedly need **{key}**: the same multi-step sequence involving context gathering, reasoning, and optional file writes. Without encoding in a skill or chain, every developer re-prompts from scratch — inconsistent results, wasted tokens, approval fatigue.

### Success criteria

1. Reproducible output format
2. Minimal tool calls
3. Clear approval boundaries
4. Observable console trace for audits""",
            f"""## Implementation (Code structure)

### Skill / command artifacts

```
.axon/skills/{key}/SKILL.md     # or chain of slash commands
.axon/memory.md                 # project conventions
```

### SKILL.md skeleton for {key}

```markdown
---
name: {key}
description: [Write for the MODEL — when to invoke]
allowed-tools: read_file, execute_shell, web_search, write_file
---

# Instructions
1. ...
!`git status -sb`
```

### Deep Internal path

```
User message or /delegate
  → llm_client._agent_loop
  → tool: {key}
  → invoke_skill → inject_shell_context
  → tool result in messages[]
  → LLM calls native tools (approval on write/shell)
```""",
            f"""## Execution (Console transcript pattern)

```
❯ Research FastAPI lifespan events and save to research/fastapi.md

✦ AXON
[Tool: {key}] invoking skill...

[Tool: Search] web_search("FastAPI lifespan events 2025")
[Tool: Write] write_file("research/fastapi.md", ...) 
[?] Allow write_file? (1 once / 2 session / 3 deny)

✦ AXON
Saved research/fastapi.md with summary of lifespan hooks...
```

## Failure Tree

```
web_search empty
├─ No network → check firewall
├─ DuckDuckGo rate limit → retry later
└─ Query too vague → tighten user prompt

write_file denied
├─ User pressed 3 → agent must explain alternative
└─ Path outside cwd → use relative paths

Skill not invoked
├─ Description doesn't match user intent → improve YAML description
└─ Model chose execute_shell directly → strengthen skill instructions
```

### Debug commands

`/cost` — token spend
`/clear` — reset without losing memory.md
ls .axon/skills/{key}/ — verify disk

### Extended failure branches

**Error: API rate limit (429)** — OpenRouter returns error; `_agent_loop` surfaces friendly message. Fix: wait, switch model, reduce context with `/clear`.

**Error: tool_call_id mismatch** — Rare OpenRouter/SDK bug on interrupted stream. Fix: `/clear` and retry.

**Error: skill body encoding** — UTF-8 BOM in SKILL.md can break frontmatter regex. Fix: save as UTF-8 without BOM.

**Error: chained command partial success** — Plan succeeds, delegate fails. State: plan remains in task_manager. Fix: run `execute` manually or `/clear` plan.

### Observability

Enable mental tracing: every tool call prints `[Tool: Label]` via `tool_display_label` in main.py callbacks. Map label → function in `skills/tools.py` TOOL_SCHEMAS.""",
            examples=[
                {"title": f"Stage 1 — Problem definition ({key})", "markdown": "User story: As a developer I want automated {key} so that I stop repeating manual steps."},
                {"title": "Stage 2 — Scaffold", "markdown": f"/create-skill or manual mkdir .axon/skills/{key}"},
                {"title": "Stage 3 — Dry run", "markdown": "Invoke with read-only tools first; no write_file until output validated."},
                {"title": "Stage 4 — Production", "markdown": "Add !`shell` injections for live context; commit SKILL.md to git."},
                {"title": "Stage 5 — Chain", "markdown": f"/plan 'Improve {key}' & /delegate reviewer Validate skill output"},
            ],
        )
    )

PAGES.extend([
    page(
        "dd-failure-master",
        "Master Failure Tree — Skills & Commands",
        "One diagram to rule every support ticket.",
        """## Why centralized failure trees matter

AXON surfaces errors in three places: terminal Rich output, tool result strings, and bridge WebSocket to Zenith. Users blame 'the AI' when the root cause is cwd, approval, or YAML.""",
        """## ASCII master tree

```
AXON misbehaves
│
├─ Slash command wrong
│   ├─ Typo → /help
│   ├─ Chain quote error → count segments
│   └─ Wrong cwd
│
├─ Skill wrong
│   ├─ Not in tool list → disable_model_invocation, reload
│   ├─ Empty invoke → shell injection failed
│   └─ Model ignores body → shorten, strengthen description
│
├─ Tool denied
│   ├─ User chose deny
│   └─ Session not approved → press 2 for session allow
│
├─ LLM errors
│   ├─ API key → .env OPENROUTER_API_KEY
│   ├─ Model → /model switch
│   └─ Context length → /clear, fewer @ files
│
└─ Bridge
    ├─ Port 8765 in use → warning only
    └─ Refresh Zenith after CLI restart
```""",
        """### Persistence cheat sheet

| Data | Location | Survives /clear? | Survives restart? |
|------|----------|------------------|-------------------|
| Chat | messages[] | No | No |
| memory | .axon/memory.md | Yes | Yes |
| skills | .axon/skills/ | Yes | Yes |
| agents | .axon/agents/ | Yes | Yes |
| plan | task_manager RAM | No | No |
| backups | .axon/backups/ | Yes | Yes |
| approvals | approved_session_tools | No | No |

Use this page as index — each branch links to a Deep Dive page with specifics.""",
    ),
    page(
        "dd-builder-appendix",
        "Builder's Appendix — Implement Skills/Commands From Scratch",
        "If you were forking AXON tomorrow, this is the build order.",
        """## Historical design decisions (expanded)

1. **prompt_toolkit + async** — Windows ANSI safety drove `safe_async_print` and `run_in_terminal` for nested UI.
2. **Skills as tools not prompts** — Keeps system prompt small; pays cost on invoke.
3. **Slash local-first** — Predictable automation for power users.
4. **No skill sandbox** — Trust model; inline shell is the main security footgun.""",
        """## Build order (God mode for implementers)

```
Week 1: main.py loop + OpenRouter chat (no tools)
Week 2: skills/tools.py read/write/shell + approval
Week 3: skills_manager.py parse + invoke + !`shell`
Week 4: task_manager plan/execute
Week 5: slash router + command_parser chains
Week 6: agent_manager + delegate swap
Week 7: bridge.py + Zenith
```

### Minimal invoke_skill pseudocode

```python
def invoke_skill(name, args):
    body = inject_shell_context(skills[name].body_raw)
    return f"# Skill activated\\n{body}\\n## User\\n{args.get('request','')}"
```

### Test checklist

- [ ] SKILL.md with !`echo hi`
- [ ] /create-skill wizard
- [ ] /plan & /delegate chain
- [ ] write_file deny path
- [ ] reload_skills after edit""",
        """```
Fork breaks on Windows
└─ shell=True path in run_inline_shell

Tests flake on CI
└─ skills invoke real git — mock subprocess in tests

Documentation drift
└─ Regenerate: python scripts/generate_deep_dive_module.py
                python scripts/merge_docs_content.py
```""",
    ),
])

# Trim or pad to exactly 20 pages
assert len(PAGES) == 20, f"Expected 20 pages, got {len(PAGES)}"

CHAPTER = {
    "meta": {
        "title": "Ultra Deep Dive — Skills, Commands & Content",
        "stats": {"module": "deep_dive", "pages": 20},
    },
    "sections": [
        {
            "id": "ultra-deep-dive",
            "title": "Ultra Deep Dive Mode",
            "lead": "20 pages of God-mode internals — memory, prompts, filesystem, case studies, failure trees.",
            "chapter": 16,
            "subsections": PAGES,
        }
    ],
}


def main() -> None:
    OUT_EN.parent.mkdir(parents=True, exist_ok=True)
    OUT_EN.write_text(
        json.dumps(CHAPTER, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    word_est = sum(
        len(str(v).split())
        for p in PAGES
        for v in p.values()
        if isinstance(v, str)
    )
    print(f"Wrote {OUT_EN}")
    print(f"Pages: {len(PAGES)}")
    print(f"Estimated words: ~{word_est}")


if __name__ == "__main__":
    main()
