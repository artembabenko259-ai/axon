#!/usr/bin/env python3
"""Generate zenith-web/locales/skills-mastery/{en,ru,ua}.json with identical key hierarchy."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "zenith-web" / "locales" / "skills-mastery"

BT = "`"

CODE = {
    "deployStaging": f"""---
name: deploy-staging
description: Check staging cluster health and summarize pod status for the team
usage: Invoke before releases or when staging looks unhealthy
disable-model-invocation: false
allowed-tools: execute_shell, read_file, web_search
---

# Staging Deploy Health

## Live context (auto-injected)
!{BT}kubectl get pods -n staging --no-headers 2>nul || echo "(kubectl unavailable)"{BT}

Recent deploy tag:
!{BT}git describe --tags --abbrev=0 2>nul || echo "no tags"{BT}

## Instructions

1. Parse the pod list above. Flag CrashLoopBackOff, Pending, or 0/1 Ready.
2. If kubectl failed, use execute_shell to diagnose (do not guess).
3. Cross-check deployment/README.md with read_file if rollback is mentioned.
4. Reply with: **Status**, **Risk level**, **Recommended next action**.""",
    "anatomyDiagram": f"""┌─────────────────────────────────────────────────────────────┐
│  SKILL FILE  (.axon/skills/deploy-staging/SKILL.md)         │
├─────────────────────────────────────────────────────────────┤
│  ╔════════════════ YAML FRONTMATTER ════════════════════╗   │
│  ║  name          → OpenRouter tool identifier          ║   │
│  ║  description   → Shown in tools[] array to LLM       ║   │
│  ║  usage         → Human/docs hint (optional)          ║   │
│  ║  allowed-tools → Advisory list for the model         ║   │
│  ║  disable-model-invocation → hide from tool list      ║   │
│  ╚══════════════════════════════════════════════════════╝   │
├─────────────────────────────────────────────────────────────┤
│  ╔════════════════ MARKDOWN LOGIC LAYER ════════════════╗   │
│  ║  # Headings, numbered steps, constraints             ║   │
│  ║  !{BT}shell commands{BT}  → INLINE SHELL (eager eval)      ║   │
│  ║  References to read_file / execute_shell / etc.      ║   │
│  ╚══════════════════════════════════════════════════════╝   │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   SkillManager.reload()          invoke_skill()
   → tool schema only            → full body + injected shell
   → messages[0] summary         → appended as tool result""",
    "genSkillTrace": """❯ /gen-skill "Create a skill that checks Docker container health and lists unhealthy ones"

🛠 Generating skill with AI...

[✓] Skill "docker-health" created and loaded successfully. Use it with !docker-health.

❯ Check my containers using the docker health skill
✦ AXON: [Tool: docker_health] …""",
    "webResearchSkill": """---
name: web-research-writer
description: Search the web, synthesize findings, and save a markdown report
allowed-tools: web_search, read_file, write_file
---

# Research Pipeline

## Step 1 — Gather (you execute)
Use web_search with the user's topic. Collect 3–5 authoritative sources.

## Step 2 — Synthesize
Summarize findings in structured markdown: Executive Summary, Key Points, Sources.

## Step 3 — Persist
Write to research/<date>-<topic-slug>.md using write_file.
Ask user approval before writing.""",
    "chainedSession": """❯ /gen-skill "Web research writer that searches, summarizes, saves to research/"
[✓] Skill "web-research-writer" created and loaded successfully.

❯ Use web-research-writer to research "AXON agent skills 2026" & /commit
⛓ Running 2 chained commands…
── Chain 1/2 ──
[Tool: web_search] …
[Tool: write_file] [?] Allow once? …
── Chain 2/2 ──
📝 Generating commit message…""",
    "skillTemplate": f"""---
name: [Name]
description: [What it does]
usage: ![Name]
disable-model-invocation: false
allowed-tools: read_file, execute_shell, web_search
---

# [Name] Skill

## Live context
!{BT}[shell command for auto-injected context]{BT}

## Instructions
1. [First step]
2. [Second step]
3. [Output format]""",
}

PIPING_TABLE = f"""| Layer | Mechanism | When it runs |
|-------|-----------|--------------|
| `!{BT}cmd{BT}` | Inline shell pipe | Skill invoke, pre-LLM |
| Skill tool call | invoke_skill() | Model chooses tool |
| `execute_shell` | Native tool + approval | Model during agent loop |
| `&` chains | command_parser.py | Sequential slash commands |"""

PIPING_TABLE_RU = f"""| Слой | Механизм | Когда выполняется |
|------|----------|-------------------|
| `!{BT}cmd{BT}` | Inline shell pipe | Invoke скилла, до LLM |
| Skill tool call | invoke_skill() | Модель выбирает tool |
| `execute_shell` | Нативный tool + approval | Модель в agent loop |
| `&` chains | command_parser.py | Последовательные slash-команды |"""

PIPING_TABLE_UA = f"""| Шар | Механізм | Коли виконується |
|-----|----------|------------------|
| `!{BT}cmd{BT}` | Inline shell pipe | Invoke скіла, до LLM |
| Skill tool call | invoke_skill() | Модель обирає tool |
| `execute_shell` | Нативний tool + approval | Модель у agent loop |
| `&` chains | command_parser.py | Послідовні slash-команди |"""


def en_locale() -> dict:
    return {
        "meta": {
            "pageTitle": "Skills Mastery",
            "moduleLabel": "Mastery Module",
            "title": "The Ultimate AXON Skills Guide",
            "lead": "Everything you need to design, generate, pipe, and debug markdown skills — the programmable memory of your local agent.",
            "badge": "Skills System · Deep Reference",
            "tocTitle": "On this page",
            "backToBible": "Back to AXON Bible",
        },
        "labels": {
            "proTip": "Pro Tip",
            "before": "Before",
            "after": "After",
            "troubleshootingHeaders": ["#", "Symptom", "Root Cause", "Fix"],
        },
        "toc": [
            {"id": "philosophy", "label": "Core Philosophy"},
            {"id": "anatomy", "label": "Anatomy of a Skill"},
            {"id": "creation", "label": "3-Step Creation Flow"},
            {"id": "patterns", "label": "Expert Patterns & Piping"},
            {"id": "troubleshooting", "label": "Troubleshooting"},
            {"id": "try-it", "label": "Try It"},
        ],
        "code": CODE,
        "sections": [
            {
                "id": "philosophy",
                "eyebrow": "Chapter I",
                "title": "The Core Philosophy",
                "lead": "Skills are not configuration files. They are specialized AI brain cells — modular expertise your agent can summon on demand.",
                "paragraphs": [
                    "A raw large language model is a brilliant generalist with amnesia. Every session, it must re-learn your repository conventions, your deployment rituals, your testing philosophy, and the dozen small workflows that make your team productive. AXON solves this not by stuffing megabytes of instructions into the system prompt, but by giving the model a library of callable expertise stored on disk under .axon/skills/.",
                    "Think of skills as building blocks in a workshop. The base AXON agent is a capable craftsperson with a standard toolbox: read_file, write_file, execute_shell, and web_search. Skills are pre-written playbooks that say: \"When someone asks about logs, first run this command, then reason about these files, then respond in this format.\" The model does not memorize the playbook at startup. It discovers skill names and one-line descriptions in the system prompt, then loads the full instructions only when it invokes the skill — like pulling a recipe card from a drawer only when you start cooking.",
                    "This architecture mirrors how professional kitchens work. The head chef (the LLM) knows what stations exist (skill tool schemas). Each station has a recipe binder (SKILL.md or .skill file). Ingredients are fetched just-in-time via inline shell injection — the plumbing that pipes live terminal output directly into the recipe before the chef reads it.",
                ],
                "beforeAfter": {
                    "before": {
                        "title": "Without Skills",
                        "content": 'User: "Summarize our staging deploy health."\n\nAXON must guess:\n• Which scripts to run\n• Which log paths exist in this repo\n• How your team names environments\n• Whether kubectl, docker, or ssh applies\n\nResult: 4–6 tool rounds, inconsistent answers, repeated explanations every session. Token cost climbs. Trust drops.',
                    },
                    "after": {
                        "title": "With Skills",
                        "content": 'User: "Run the staging health skill."\n\nAXON calls deploy-staging skill tool once.\nSkill body injects live context via !`kubectl get pods -n staging`\nInstructions tell the model exactly how to summarize.\n\nResult: 1 skill invoke + 1–2 tool rounds. Same playbook every time. Git-reviewable expertise your whole team shares.',
                    },
                },
                "proTip": {
                    "title": "Pro Tip — Treat Skills Like Code",
                    "body": "Version-control every skill under .axon/skills/. Review them in pull requests the same way you review CI scripts. A skill that encodes \"how we deploy\" is more valuable than a hundred ad-hoc chat sessions that evaporate when the terminal closes.",
                },
                "designPrinciple": {
                    "label": "Design Principle",
                    "body": "AXON deliberately keeps skill bodies out of the system prompt. Only names and short descriptions are registered with OpenRouter as tool schemas. Full instructions arrive as a tool result when invoke_skill() runs. This keeps your context window lean while still allowing arbitrarily deep playbooks — some production skills exceed 8 KB of markdown without penalizing every message.",
                },
            },
            {
                "id": "anatomy",
                "eyebrow": "Chapter II",
                "title": "The Anatomy of a Skill",
                "lead": "Every skill is two layers: YAML metadata (the label on the jar) and markdown logic (the recipe inside).",
                "intro": "AXON skills are not Python modules and not JSON blobs. They are markdown files with YAML frontmatter, stored either as .axon/skills/<folder>/SKILL.md or .axon/skills/<name>.skill after AI generation. The frontmatter is parsed by a lightweight custom YAML reader in skills_manager.py — no PyYAML dependency. The body is raw markdown that becomes the instruction payload when the skill activates.",
                "codePanels": [
                    {"label": "Full skill example — deploy-staging", "codeKey": "deployStaging"},
                    {"label": "ASCII — skill file layers", "codeKey": "anatomyDiagram"},
                ],
                "subsectionTitle": "Visual Anatomy Diagram",
                "cards": [
                    {
                        "title": "YAML Layer — Registration",
                        "body": "The frontmatter is the API contract. name becomes the sanitized tool name sent to OpenRouter. description is the only text the model sees before choosing to call the skill — write it like a product feature blurb, not a filename. allowed-tools is documented in the invoke payload; treat it as guidance for the model, not a hard sandbox (native tools still pass through the approval gate separately).",
                    },
                    {
                        "title": "Logic Layer — Execution",
                        "body": "The markdown body is the procedure. Unlike Python decorators, AXON skills express logic as natural-language steps plus optional !`command` blocks. When inject_shell_context() runs, each placeholder is replaced with live stdout before the LLM reads the skill — shrinking tool rounds and eliminating \"please run git status first\" back-and-forth.",
                    },
                ],
                "proTip": {
                    "title": "Pro Tip — Name vs Folder",
                    "body": "The folder name (git-status) and YAML name: field can differ, but keeping them aligned prevents confusion in logs and /help output. For .skill files, the filename stem becomes the skill_id automatically.",
                },
            },
            {
                "id": "creation",
                "eyebrow": "Chapter III",
                "title": "The 3-Step Creation Flow",
                "lead": "Use /gen-skill to go from a sentence of intent to a loaded, callable skill in under a minute.",
                "intro": "Manual skill authoring via /create-skill is ideal when you know exact shell commands. /gen-skill is for exploratory work: describe the outcome in plain language, let the LLM draft the YAML and markdown body, save to disk, and hot-reload without restarting AXON.",
                "steps": [
                    {
                        "step": "01",
                        "title": "Describe the skill",
                        "body": 'Type /gen-skill followed by a quoted description. Be specific about inputs, tools, and output format. Example: /gen-skill "Audit npm vulnerabilities, summarize critical CVEs, suggest fix commands"',
                    },
                    {
                        "step": "02",
                        "title": "AI generates & saves",
                        "body": "AXON sends your description to the LLM with a skill-author system prompt. The response is extracted from a markdown code fence, validated for a name field in YAML, and written to .axon/skills/<name>.skill",
                    },
                    {
                        "step": "03",
                        "title": "Hot reload",
                        "body": 'llm_manager.reload_skills() rescans the skills directory and rebuilds messages[0]. The new tool appears in the next agent turn immediately. Success prints: [✓] Skill "<name>" created and loaded successfully.',
                    },
                ],
                "ioTable": {
                    "title": "What to Expect — Inputs & Outputs",
                    "headers": ["Stage", "You Provide", "AXON Does", "You Receive"],
                    "rows": [
                        {"cells": ["Invoke", '/gen-skill "description"', "Parse quoted text, call OpenRouter (no tools)", "🛠 Generating skill with AI…"]},
                        {"cells": ["Generate", "OPENROUTER_API_KEY in .env", "LLM returns fenced SKILL content", "Silent (watch token usage via /cost)"]},
                        {"cells": ["Validate", "—", "extract_skill_code_block(), check name: in YAML", "Error if empty or missing name"]},
                        {"cells": ["Persist", "—", "Write .axon/skills/<name>.skill", "File on disk, git-trackable"]},
                        {"cells": ["Reload", "—", "SkillManager.reload() + refresh system prompt", '[✓] Skill "name" created and loaded…']},
                        {"cells": ["Use", "Natural language task", "Model calls skill tool by sanitized name", "Full playbook injected as tool result"]},
                    ],
                },
                "codePanels": [
                    {"label": "Console trace — successful /gen-skill", "codeKey": "genSkillTrace"},
                ],
            },
            {
                "id": "patterns",
                "eyebrow": "Chapter IV",
                "title": "Expert Patterns & Piping",
                "lead": "Master the ! backtick pipe — AXON's eager-evaluation plumbing for live context.",
                "intro": "The !`command` syntax is not a shell alias and not the same as typing !skill-name in chat. It is an inline pipe: when a skill is invoked, AXON runs the command locally before the model sees the skill body, then pastes stdout into the markdown. Think of it as a mail-merge for terminal output — the recipe stays static, the ingredients are always fresh.",
                "proTip": {
                    "title": "Pro Tip — Security Boundary",
                    "body": "Inline shell runs without user approval at skill-invoke time. Never put user-controlled text inside !`…`. Only hard-code commands you would run yourself. Destructive operations belong in execute_shell where the approval gate applies.",
                },
                "multiStepTitle": "Multi-Step Chain: Search → Summarize → Save",
                "multiStepIntro": "Advanced workflows combine a skill (orchestration playbook), native tools (side effects), and optional command chains with &. Below is a production pattern for research pipelines.",
                "codePanels": [
                    {"label": "Skill: web-research-writer.skill", "codeKey": "webResearchSkill"},
                    {"label": "Chained CLI session", "codeKey": "chainedSession"},
                ],
                "pipingMentalModelTitle": "Piping mental model",
                "pipingTableMarkdown": PIPING_TABLE,
            },
            {
                "id": "troubleshooting",
                "eyebrow": "Chapter V",
                "title": "Troubleshooting & Debugging",
                "lead": "Ten failures you'll hit in production — and exactly how to fix each one.",
                "troubleshootingRows": [
                    {"cells": ["1", "Skill not in tool list", "disable-model-invocation: true or YAML parse failed", "Set false; verify --- delimiters; check UTF-8 without BOM"]},
                    {"cells": ["2", "/gen-skill returns API error", "Missing or invalid OPENROUTER_API_KEY", "Set key in .env or Zenith /config; run /model to verify"]},
                    {"cells": ["3", "Generated skill won't save", "LLM omitted name: in frontmatter", "Re-run with clearer description; or edit file manually"]},
                    {"cells": ["4", "Skill exists but AXON can't find it", "Wrong working directory (cwd)", "cd to project root where .axon/ lives"]},
                    {"cells": ["5", "!`cmd` shows (command error)", "Shell syntax differs on Windows vs Unix", "Use portable commands; test in terminal first"]},
                    {"cells": ["6", "Inline shell times out", "Command exceeds 30s SHELL_TIMEOUT", "Shorten command; move heavy work to execute_shell"]},
                    {"cells": ["7", "Model ignores allowed-tools", "Advisory only — not enforced in _dispatch_tool", "Document constraints; rely on approval for writes"]},
                    {"cells": ["8", "Duplicate skill names", "Folder SKILL.md and .skill share same name", "Delete one; later reload wins on collision"]},
                    {"cells": ["9", "Changes not visible mid-chat", "reload_skills not called after manual edit", "Send any message or /clear to trigger reload"]},
                    {"cells": ["10", "Skill body truncated", "Inline output exceeds 16 KB MAX_INLINE_OUTPUT", "Pipe through head/tail; summarize in smaller chunks"]},
                ],
                "proTip": {
                    "title": "Pro Tip — Debug Checklist",
                    "body": "Run ls .axon/skills/ in your terminal. Cat the skill file. Invoke it with an explicit natural-language request mentioning the skill name. Watch for [Tool: skill_name] in the console — that confirms the model called the right tool.",
                },
            },
            {
                "id": "try-it",
                "eyebrow": "Chapter VI",
                "title": "Interactive Try It",
                "lead": "Practice the syntax. Type the sample commands in the sandbox below.",
                "templateLabel": "Skill File Template — Copy This Structure",
                "sandbox": {
                    "title": "AXON Skills Sandbox",
                    "placeholder": 'Try: /gen-skill "my skill idea"',
                    "initial": "$ axon\nAXON v1.0 — Skills Mastery Sandbox\n\nType a command below to simulate responses.\n",
                    "scenarios": {
                        '/gen-skill "check git status and summarize"': '🛠 Generating skill with AI...\n[✓] Skill "git-status-helper" created and loaded successfully. Use it with !git-status-helper.',
                        "/help": "  /gen-skill   AI-generate a skill from a description\n  /create-skill   Interactive SKILL.md wizard\n  /clear   Clear context and reload skills",
                        "/create-skill": "🛠 Creating a new AXON skill\nSkill Name: _\n(interactive wizard — use terminal for full flow)",
                        "check git status": "✦ AXON: [Tool: git_status] Summarizing repository...\nOn branch main. 2 files modified.",
                        "*": 'AXON: Try /gen-skill "your idea" or /help for skill commands.',
                    },
                    "footer": "For live skill generation, run python main.py in your project root with a valid OpenRouter API key.",
                },
            },
        ],
    }


def ru_locale() -> dict:
    base = en_locale()
    base["meta"] = {
        "pageTitle": "Мастерство Skills",
        "moduleLabel": "Модуль мастерства",
        "title": "Полное руководство по Skills в AXON",
        "lead": "Всё, что нужно для проектирования, генерации, пайпинга и отладки markdown-скиллов — программируемой памяти вашего локального агента.",
        "badge": "Система Skills · Глубокий справочник",
        "tocTitle": "На этой странице",
        "backToBible": "Назад к AXON Bible",
    }
    base["labels"] = {
        "proTip": "Pro Tip",
        "before": "До",
        "after": "После",
        "troubleshootingHeaders": ["#", "Симптом", "Причина", "Решение"],
    }
    base["toc"] = [
        {"id": "philosophy", "label": "Базовая философия"},
        {"id": "anatomy", "label": "Анатомия скилла"},
        {"id": "creation", "label": "Создание за 3 шага"},
        {"id": "patterns", "label": "Паттерны и пайпинг"},
        {"id": "troubleshooting", "label": "Устранение неполадок"},
        {"id": "try-it", "label": "Попробуйте"},
    ]
    sections = base["sections"]
    sections[0].update({
        "eyebrow": "Глава I",
        "title": "Базовая философия",
        "lead": "Skills — это не конфигурационные файлы. Это специализированные «нейроны» ИИ — модульная экспертиза, которую агент вызывает по требованию.",
        "paragraphs": [
            "«Голый» LLM — блестящий универсал с амнезией. Каждую сессию он заново изучает конвенции репозитория, ритуалы деплоя, философию тестирования и десятки мелких workflow, которые делают вашу команду продуктивной. AXON решает это не забиванием системного промпта мегабайтами инструкций, а библиотекой вызываемой экспертизы на диске в .axon/skills/.",
            "Представьте skills как строительные блоки в мастерской. Базовый агент AXON — умелый мастер со стандартным ящиком инструментов: read_file, write_file, execute_shell и web_search. Skills — готовые плейбуки: «Когда спрашивают про логи — сначала выполни эту команду, затем проанализируй эти файлы, ответь в таком формате». Модель не запоминает плейбук при старте. Она видит имена и краткие описания в системном промпте и загружает полные инструкции только при вызове скилла — как рецепт из ящика, который достают только когда начинают готовить.",
            "Эта архитектура похожа на профессиональную кухню. Шеф (LLM) знает, какие станции есть (схемы tool для skills). У каждой станции — папка с рецептами (SKILL.md или .skill). Ингредиенты подаются just-in-time через inline shell injection — «трубы», которые вставляют живой вывод терминала в рецепт до того, как шеф его прочитает.",
        ],
        "beforeAfter": {
            "before": {
                "title": "Без Skills",
                "content": 'Пользователь: «Суммируй здоровье staging-деплоя».\n\nAXON должен угадать:\n• Какие скрипты запускать\n• Где лежат логи в этом репо\n• Как команда называет окружения\n• Нужны kubectl, docker или ssh\n\nИтог: 4–6 раундов tool, разные ответы, повторные объяснения каждую сессию. Растут токены. Падает доверие.',
            },
            "after": {
                "title": "Со Skills",
                "content": 'Пользователь: «Запусти скилл проверки staging».\n\nAXON один раз вызывает tool deploy-staging.\nТело скилла вставляет контекст через !`kubectl get pods -n staging`\nИнструкции точно описывают, как суммировать.\n\nИтог: 1 invoke скилла + 1–2 tool. Один плейбук каждый раз. Экспертиза в git, доступна всей команде.',
            },
        },
        "proTip": {
            "title": "Pro Tip — Относитесь к Skills как к коду",
            "body": "Храните каждый скилл в git под .axon/skills/. Ревьюйте в pull request так же, как CI-скрипты. Скилл «как мы деплоим» ценнее сотни чатов, которые исчезают после закрытия терминала.",
        },
        "designPrinciple": {
            "label": "Принцип проектирования",
            "body": "AXON намеренно держит тела скиллов вне системного промпта. В OpenRouter уходят только имена и короткие описания как tool schemas. Полные инструкции приходят как результат tool при invoke_skill(). Контекст остаётся компактным, а плейбуки могут быть глубокими — production-скиллы > 8 KB markdown не штрафуют каждое сообщение.",
        },
    })
    sections[1].update({
        "eyebrow": "Глава II",
        "title": "Анатомия скилла",
        "lead": "Два слоя: YAML-метаданные (этикетка на банке) и markdown-логика (рецепт внутри).",
        "intro": "Skills AXON — не Python-модули и не JSON. Это markdown с YAML frontmatter: .axon/skills/<folder>/SKILL.md или .axon/skills/<name>.skill после /gen-skill. Frontmatter парсит лёгкий YAML-ридер в skills_manager.py без PyYAML. Тело — сырой markdown, который становится payload инструкций при активации.",
        "subsectionTitle": "Визуальная схема анатомии",
        "codePanels": [
            {"label": "Полный пример — deploy-staging", "codeKey": "deployStaging"},
            {"label": "ASCII — слои файла скилла", "codeKey": "anatomyDiagram"},
        ],
        "cards": [
            {
                "title": "Слой YAML — регистрация",
                "body": "Frontmatter — API-контракт. name становится sanitized tool name для OpenRouter. description — единственный текст, который модель видит до вызова скилла; пишите как описание фичи, не как имя файла. allowed-tools документируется в invoke payload — это рекомендация, не жёсткая песочница (нативные tools проходят approval отдельно).",
            },
            {
                "title": "Слой логики — выполнение",
                "body": "Markdown-тело — процедура. В отличие от Python-декораторов, логика выражается шагами на естественном языке и блоками !`command`. inject_shell_context() подставляет живой stdout до чтения скилла LLM — меньше раундов tool и без «сначала запусти git status».",
            },
        ],
        "proTip": {
            "title": "Pro Tip — Имя vs папка",
            "body": "Имя папки (git-status) и поле YAML name: могут различаться, но лучше держать их в sync — меньше путаницы в логах и /help. Для .skill skill_id берётся из имени файла.",
        },
    })
    sections[2].update({
        "eyebrow": "Глава III",
        "title": "Создание за 3 шага",
        "lead": "С /gen-skill — от одной фразы намерения до загруженного скилла меньше чем за минуту.",
        "intro": "/create-skill — когда знаете точные shell-команды. /gen-skill — для исследования: опишите результат, LLM черновик YAML и markdown, сохранение на диск и hot-reload без перезапуска AXON.",
        "steps": [
            {
                "step": "01",
                "title": "Опишите скилл",
                "body": 'Введите /gen-skill с описанием в кавычках. Укажите входы, tools и формат ответа. Пример: /gen-skill "Проверь npm-уязвимости, суммируй критичные CVE, предложи команды исправления"',
            },
            {
                "step": "02",
                "title": "ИИ генерирует и сохраняет",
                "body": "AXON отправляет описание в LLM со skill-author промптом. Ответ извлекается из markdown fence, проверяется name в YAML, пишется в .axon/skills/<name>.skill",
            },
            {
                "step": "03",
                "title": "Hot reload",
                "body": 'llm_manager.reload_skills() пересканирует каталог и пересобирает messages[0]. Новый tool доступен в следующем ходе. Успех: [✓] Skill "<name>" created and loaded successfully.',
            },
        ],
        "ioTable": {
            "title": "Чего ожидать — входы и выходы",
            "headers": ["Этап", "Вы даёте", "AXON делает", "Вы получаете"],
            "rows": [
                {"cells": ["Вызов", '/gen-skill "описание"', "Парсит кавычки, вызывает OpenRouter (без tools)", "🛠 Generating skill with AI…"]},
                {"cells": ["Генерация", "OPENROUTER_API_KEY в .env", "LLM возвращает SKILL в fence", "Тихо (следите за /cost)"]},
                {"cells": ["Валидация", "—", "extract_skill_code_block(), проверка name:", "Ошибка при пустом или без name"]},
                {"cells": ["Сохранение", "—", "Запись .axon/skills/<name>.skill", "Файл на диске, в git"]},
                {"cells": ["Reload", "—", "SkillManager.reload() + system prompt", '[✓] Skill "name" created and loaded…']},
                {"cells": ["Использование", "Задача на естественном языке", "Модель вызывает tool по sanitized name", "Плейбук в tool result"]},
            ],
        },
        "codePanels": [
            {"label": "Трассировка консоли — успешный /gen-skill", "codeKey": "genSkillTrace"},
        ],
    })
    sections[3].update({
        "eyebrow": "Глава IV",
        "title": "Паттерны экспертов и пайпинг",
        "lead": "Освойте pipe с ! и backtick — eager-evaluation «трубы» AXON для живого контекста.",
        "intro": "Синтаксис !`command` — не shell-алиас и не то же самое, что !skill-name в чате. Это inline pipe: при invoke AXON выполняет команду локально до того, как модель увидит тело скилла, и вставляет stdout в markdown. Как mail-merge для терминала — рецепт статичен, ингредиенты всегда свежие.",
        "proTip": {
            "title": "Pro Tip — Граница безопасности",
            "body": "Inline shell выполняется без approval при invoke скилла. Никогда не вставляйте пользовательский ввод в !`…`. Только команды, которые запустили бы сами. Деструктивные операции — в execute_shell с approval gate.",
        },
        "multiStepTitle": "Многошаговая цепочка: Поиск → Суммаризация → Сохранение",
        "multiStepIntro": "Продвинутые workflow объединяют скилл (оркестрация), нативные tools (побочные эффекты) и цепочки с &. Ниже — паттерн research pipeline.",
        "codePanels": [
            {"label": "Скилл: web-research-writer.skill", "codeKey": "webResearchSkill"},
            {"label": "Сессия с цепочкой в CLI", "codeKey": "chainedSession"},
        ],
        "pipingMentalModelTitle": "Ментальная модель пайпинга",
        "pipingTableMarkdown": PIPING_TABLE_RU,
    })
    sections[4].update({
        "eyebrow": "Глава V",
        "title": "Устранение неполадок и отладка",
        "lead": "Десять типичных сбоев в production — и точные способы исправления.",
        "troubleshootingRows": [
            {"cells": ["1", "Скилла нет в списке tools", "disable-model-invocation: true или ошибка YAML", "false; проверьте ---; UTF-8 без BOM"]},
            {"cells": ["2", "/gen-skill — ошибка API", "Нет или неверный OPENROUTER_API_KEY", "Ключ в .env или Zenith /config; /model"]},
            {"cells": ["3", "Сгенерированный скилл не сохраняется", "LLM не указал name: в frontmatter", "Повторите с ясным описанием или правьте файл"]},
            {"cells": ["4", "Скилл есть, AXON не находит", "Неверный cwd", "cd в корень проекта с .axon/"]},
            {"cells": ["5", "!`cmd` показывает (command error)", "Разный shell на Windows и Unix", "Портируемые команды; тест в терминале"]},
            {"cells": ["6", "Таймаут inline shell", "Команда > 30s SHELL_TIMEOUT", "Укоротите; тяжёлое — в execute_shell"]},
            {"cells": ["7", "Модель игнорирует allowed-tools", "Только advisory, не enforced в _dispatch_tool", "Документируйте; approval для записи"]},
            {"cells": ["8", "Дубликаты имён скиллов", "SKILL.md и .skill с одним именем", "Удалите один; при reload побеждает последний"]},
            {"cells": ["9", "Правки не видны в чате", "reload_skills не вызван после правки", "Любое сообщение или /clear"]},
            {"cells": ["10", "Тело скилла обрезано", "Вывод > 16 KB MAX_INLINE_OUTPUT", "head/tail; суммируйте частями"]},
        ],
        "proTip": {
            "title": "Pro Tip — Чеклист отладки",
            "body": "В терминале: ls .axon/skills/. Прочитайте файл скилла. Вызовите явным запросом с именем скилла. Ищите [Tool: skill_name] в консоли — подтверждение вызова.",
        },
    })
    sections[5].update({
        "eyebrow": "Глава VI",
        "title": "Интерактивно — попробуйте",
        "lead": "Отработайте синтаксис. Введите примеры команд в песочницу ниже.",
        "templateLabel": "Шаблон файла скилла — скопируйте структуру",
        "sandbox": {
            "title": "Песочница AXON Skills",
            "placeholder": 'Попробуйте: /gen-skill "идея скилла"',
            "initial": "$ axon\nAXON v1.0 — Песочница Skills Mastery\n\nВведите команду для симуляции ответа.\n",
            "scenarios": {
                '/gen-skill "check git status and summarize"': '🛠 Generating skill with AI...\n[✓] Skill "git-status-helper" created and loaded successfully. Use it with !git-status-helper.',
                "/help": "  /gen-skill   ИИ-генерация скилла из описания\n  /create-skill   Мастер SKILL.md\n  /clear   Очистить контекст и перезагрузить skills",
                "/create-skill": "🛠 Creating a new AXON skill\nSkill Name: _\n(интерактивный мастер — полный поток в терминале)",
                "check git status": "✦ AXON: [Tool: git_status] Суммаризация репозитория...\nOn branch main. 2 files modified.",
                "*": 'AXON: Попробуйте /gen-skill "ваша идея" или /help.',
            },
            "footer": "Для живой генерации запустите python main.py в корне проекта с валидным ключом OpenRouter.",
        },
    })
    return base


def ua_locale() -> dict:
    base = en_locale()
    base["meta"] = {
        "pageTitle": "Майстерність Skills",
        "moduleLabel": "Модуль майстерності",
        "title": "Повний посібник з Skills у AXON",
        "lead": "Усе для проєктування, генерації, пайпінгу та налагодження markdown-скілів — програмованої пам'яті вашого локального агента.",
        "badge": "Система Skills · Глибокий довідник",
        "tocTitle": "На цій сторінці",
        "backToBible": "Назад до AXON Bible",
    }
    base["labels"] = {
        "proTip": "Pro Tip",
        "before": "До",
        "after": "Після",
        "troubleshootingHeaders": ["#", "Симптом", "Причина", "Виправлення"],
    }
    base["toc"] = [
        {"id": "philosophy", "label": "Базова філософія"},
        {"id": "anatomy", "label": "Анатомія скіла"},
        {"id": "creation", "label": "Створення за 3 кроки"},
        {"id": "patterns", "label": "Патерни та пайпінг"},
        {"id": "troubleshooting", "label": "Усунення несправностей"},
        {"id": "try-it", "label": "Спробуйте"},
    ]
    sections = base["sections"]
    sections[0].update({
        "eyebrow": "Розділ I",
        "title": "Базова філософія",
        "lead": "Skills — не конфігураційні файли. Це спеціалізовані «нейрони» ШІ — модульна експертиза, яку агент викликає за потреби.",
        "paragraphs": [
            "«Чиста» LLM — блискучий універсал з амнезією. Кожну сесію вона знову вивчає конвенції репозиторію, ритуали деплою, філософію тестування та десятки дрібних workflow вашої команди. AXON не забиває системний промпт мегабайтами інструкцій, а дає моделі бібліотеку викликної експертизи на диску в .axon/skills/.",
            "Уявіть skills як будівельні блоки в майстерні. Базовий агент AXON — майстер зі стандартним набором: read_file, write_file, execute_shell і web_search. Skills — готові плейбуки: «Коли питають про логи — спочатку ця команда, потім ці файли, відповідь у такому форматі». Модель не запам'ятовує плейбук при старті. Вона бачить імена та короткі описи в системному промпті й завантажує повні інструкції лише при виклику скіла — як рецепт з шухляди лише коли починають готувати.",
            "Ця архітектура схожа на професійну кухню. Шеф (LLM) знає станції (tool schemas для skills). Кожна станція має папку рецептів (SKILL.md або .skill). Інгредієнти подаються just-in-time через inline shell injection — «труби», що вставляють живий вивід терміналу в рецепт до того, як шеф його прочитає.",
        ],
        "beforeAfter": {
            "before": {
                "title": "Без Skills",
                "content": 'Користувач: «Підсумуй здоров\'я staging-деплою».\n\nAXON мусить вгадати:\n• Які скрипти запускати\n• Де логи в цьому репо\n• Як команда називає середовища\n• kubectl, docker чи ssh\n\nРезультат: 4–6 раундів tool, різні відповіді, повторні пояснення щосесії. Зростають токени. Падає довіра.',
            },
            "after": {
                "title": "Зі Skills",
                "content": 'Користувач: «Запусти скил перевірки staging».\n\nAXON один раз викликає tool deploy-staging.\nТіло скіла вставляє контекст через !`kubectl get pods -n staging`\nІнструкції точно описують підсумок.\n\nРезультат: 1 invoke скіла + 1–2 tool. Один плейбук щоразу. Експертиза в git для всієї команди.',
            },
        },
        "proTip": {
            "title": "Pro Tip — Ставтеся до Skills як до коду",
            "body": "Тримайте кожен скил у git під .axon/skills/. Рев'юйте в pull request як CI-скрипти. Скил «як ми деплоїмо» цінніший за сотню чатів, що зникають після закриття терміналу.",
        },
        "designPrinciple": {
            "label": "Принцип проєктування",
            "body": "AXON навмисно тримає тіла скілів поза системним промптом. У OpenRouter йдуть лише імена та короткі описи як tool schemas. Повні інструкції приходять як tool result при invoke_skill(). Контекст залишається компактним, плейбуки можуть бути глибокими — production-скили > 8 KB markdown не карають кожне повідомлення.",
        },
    })
    sections[1].update({
        "eyebrow": "Розділ II",
        "title": "Анатомія скіла",
        "lead": "Два шари: YAML-метадані (етикетка на банці) та markdown-логіка (рецепт всередині).",
        "intro": "Skills AXON — не Python-модулі й не JSON. Це markdown з YAML frontmatter: .axon/skills/<folder>/SKILL.md або .axon/skills/<name>.skill після /gen-skill. Frontmatter парсить легкий YAML-рідер у skills_manager.py без PyYAML. Тіло — сирий markdown, що стає payload інструкцій при активації.",
        "subsectionTitle": "Візуальна схема анатомії",
        "codePanels": [
            {"label": "Повний приклад — deploy-staging", "codeKey": "deployStaging"},
            {"label": "ASCII — шари файлу скіла", "codeKey": "anatomyDiagram"},
        ],
        "cards": [
            {
                "title": "Шар YAML — реєстрація",
                "body": "Frontmatter — API-контракт. name стає sanitized tool name для OpenRouter. description — єдиний текст, який модель бачить до виклику скіла; пишіть як опис фічі, не як ім'я файлу. allowed-tools документується в invoke payload — це рекомендація, не жорстка пісочниця (нативні tools проходять approval окремо).",
            },
            {
                "title": "Шар логіки — виконання",
                "body": "Markdown-тіло — процедура. На відміну від Python-декораторів, логіка виражається кроками природною мовою та блоками !`command`. inject_shell_context() підставляє живий stdout до читання скіла LLM — менше раундів tool без «спочатку git status».",
            },
        ],
        "proTip": {
            "title": "Pro Tip — Ім'я vs папка",
            "body": "Ім'я папки (git-status) і поле YAML name: можуть відрізнятися, але краще тримати їх узгодженими — менше плутанини в логах і /help. Для .skill skill_id береться з імені файлу.",
        },
    })
    sections[2].update({
        "eyebrow": "Розділ III",
        "title": "Створення за 3 кроки",
        "lead": "З /gen-skill — від однієї фрази наміру до завантаженого скіла менше ніж за хвилину.",
        "intro": "/create-skill — коли знаєте точні shell-команди. /gen-skill — для дослідження: опишіть результат, LLM чернетку YAML і markdown, збереження на диск і hot-reload без перезапуску AXON.",
        "steps": [
            {
                "step": "01",
                "title": "Опишіть скил",
                "body": 'Введіть /gen-skill з описом у лапках. Вкажіть входи, tools і формат відповіді. Приклад: /gen-skill "Перевір npm-вразливості, підсумуй критичні CVE, запропонуй команди виправлення"',
            },
            {
                "step": "02",
                "title": "ШІ генерує та зберігає",
                "body": "AXON надсилає опис у LLM зі skill-author промптом. Відповідь з markdown fence, перевірка name у YAML, запис у .axon/skills/<name>.skill",
            },
            {
                "step": "03",
                "title": "Hot reload",
                "body": 'llm_manager.reload_skills() пересканує каталог і перезбирає messages[0]. Новий tool доступний у наступному ході. Успіх: [✓] Skill "<name>" created and loaded successfully.',
            },
        ],
        "ioTable": {
            "title": "Чого очікувати — входи та виходи",
            "headers": ["Етап", "Ви даєте", "AXON робить", "Ви отримуєте"],
            "rows": [
                {"cells": ["Виклик", '/gen-skill "опис"', "Парсить лапки, викликає OpenRouter (без tools)", "🛠 Generating skill with AI…"]},
                {"cells": ["Генерація", "OPENROUTER_API_KEY у .env", "LLM повертає SKILL у fence", "Тихо (стежте за /cost)"]},
                {"cells": ["Валідація", "—", "extract_skill_code_block(), перевірка name:", "Помилка якщо порожньо або без name"]},
                {"cells": ["Збереження", "—", "Запис .axon/skills/<name>.skill", "Файл на диску, у git"]},
                {"cells": ["Reload", "—", "SkillManager.reload() + system prompt", '[✓] Skill "name" created and loaded…']},
                {"cells": ["Використання", "Задача природною мовою", "Модель викликає tool за sanitized name", "Плейбук у tool result"]},
            ],
        },
        "codePanels": [
            {"label": "Трасування консолі — успішний /gen-skill", "codeKey": "genSkillTrace"},
        ],
    })
    sections[3].update({
        "eyebrow": "Розділ IV",
        "title": "Патерни експертів і пайпінг",
        "lead": "Опануйте pipe з ! і backtick — eager-evaluation «труби» AXON для живого контексту.",
        "intro": "Синтаксис !`command` — не shell-аліас і не те саме, що !skill-name у чаті. Це inline pipe: при invoke AXON виконує команду локально до того, як модель побачить тіло скіла, і вставляє stdout у markdown. Як mail-merge для терміналу — рецепт статичний, інгредієнти завжди свіжі.",
        "proTip": {
            "title": "Pro Tip — Межа безпеки",
            "body": "Inline shell виконується без approval при invoke скіла. Ніколи не вставляйте ввід користувача в !`…`. Лише команди, які запустили б самі. Деструктивні операції — у execute_shell з approval gate.",
        },
        "multiStepTitle": "Багатокроковий ланцюг: Пошук → Підсумок → Збереження",
        "multiStepIntro": "Просунуті workflow поєднують скил (оркестрація), нативні tools (побічні ефекти) та ланцюги з &. Нижче — патерн research pipeline.",
        "codePanels": [
            {"label": "Скил: web-research-writer.skill", "codeKey": "webResearchSkill"},
            {"label": "Сесія з ланцюгом у CLI", "codeKey": "chainedSession"},
        ],
        "pipingMentalModelTitle": "Ментальна модель пайпінгу",
        "pipingTableMarkdown": PIPING_TABLE_UA,
    })
    sections[4].update({
        "eyebrow": "Розділ V",
        "title": "Усунення несправностей і налагодження",
        "lead": "Десять типових збоїв у production — і точні способи виправлення.",
        "troubleshootingRows": [
            {"cells": ["1", "Скіла немає в списку tools", "disable-model-invocation: true або помилка YAML", "false; перевірте ---; UTF-8 без BOM"]},
            {"cells": ["2", "/gen-skill — помилка API", "Немає або невірний OPENROUTER_API_KEY", "Ключ у .env або Zenith /config; /model"]},
            {"cells": ["3", "Згенерований скил не зберігається", "LLM не вказав name: у frontmatter", "Повторіть з чітким описом або правте файл"]},
            {"cells": ["4", "Скил є, AXON не знаходить", "Невірний cwd", "cd у корінь проєкту з .axon/"]},
            {"cells": ["5", "!`cmd` показує (command error)", "Різний shell на Windows і Unix", "Портовані команди; тест у терміналі"]},
            {"cells": ["6", "Таймаут inline shell", "Команда > 30s SHELL_TIMEOUT", "Скоротіть; важке — у execute_shell"]},
            {"cells": ["7", "Модель ігнорує allowed-tools", "Лише advisory, не enforced у _dispatch_tool", "Документуйте; approval для запису"]},
            {"cells": ["8", "Дублікати імен скілів", "SKILL.md і .skill з одним ім'ям", "Видаліть один; при reload перемагає останній"]},
            {"cells": ["9", "Правки не видно в чаті", "reload_skills не викликано після правки", "Будь-яке повідомлення або /clear"]},
            {"cells": ["10", "Тіло скіла обрізано", "Вивід > 16 KB MAX_INLINE_OUTPUT", "head/tail; підсумовуйте частинами"]},
        ],
        "proTip": {
            "title": "Pro Tip — Чеклист налагодження",
            "body": "У терміналі: ls .axon/skills/. Прочитайте файл скіла. Викличте явним запитом з іменем скіла. Шукайте [Tool: skill_name] у консолі — підтвердження виклику.",
        },
    })
    sections[5].update({
        "eyebrow": "Розділ VI",
        "title": "Інтерактивно — спробуйте",
        "lead": "Відпрацюйте синтаксис. Введіть приклади команд у пісочницю нижче.",
        "templateLabel": "Шаблон файлу скіла — скопіюйте структуру",
        "sandbox": {
            "title": "Пісочниця AXON Skills",
            "placeholder": 'Спробуйте: /gen-skill "ідея скіла"',
            "initial": "$ axon\nAXON v1.0 — Пісочниця Skills Mastery\n\nВведіть команду для симуляції відповіді.\n",
            "scenarios": {
                '/gen-skill "check git status and summarize"': '🛠 Generating skill with AI...\n[✓] Skill "git-status-helper" created and loaded successfully. Use it with !git-status-helper.',
                "/help": "  /gen-skill   ШІ-генерація скіла з опису\n  /create-skill   Майстер SKILL.md\n  /clear   Очистити контекст і перезавантажити skills",
                "/create-skill": "🛠 Creating a new AXON skill\nSkill Name: _\n(інтерактивний майстер — повний потік у терміналі)",
                "check git status": "✦ AXON: [Tool: git_status] Підсумок репозиторію...\nOn branch main. 2 files modified.",
                "*": 'AXON: Спробуйте /gen-skill "ваша ідея" або /help.',
            },
            "footer": "Для живої генерації запустіть python main.py у корені проєкту з валідним ключем OpenRouter.",
        },
    })
    return base


def assert_same_keys(a: dict, b: dict, path: str = "") -> None:
    if set(a.keys()) != set(b.keys()):
        raise SystemExit(f"Key mismatch at {path}: {set(a.keys()) ^ set(b.keys())}")
    for k in a:
        pa = f"{path}.{k}" if path else k
        if isinstance(a[k], dict) and isinstance(b[k], dict):
            assert_same_keys(a[k], b[k], pa)
        elif isinstance(a[k], list) and isinstance(b[k], list):
            if len(a[k]) != len(b[k]):
                raise SystemExit(f"List length mismatch at {pa}")
            for i, (ai, bi) in enumerate(zip(a[k], b[k])):
                if isinstance(ai, dict) and isinstance(bi, dict):
                    assert_same_keys(ai, bi, f"{pa}[{i}]")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    locales = {"en": en_locale(), "ru": ru_locale(), "ua": ua_locale()}
    en_data = locales["en"]
    for lang, data in locales.items():
        assert_same_keys(en_data, data)
        path = OUT / f"{lang}.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
