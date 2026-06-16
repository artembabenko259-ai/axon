# AXON — план на день (wave 2)

Цель: закрыть все пункты из списка «полезного» за один рабочий день.  
Порядок — от быстрых независимых фич к интеграциям. После каждой фазы — **коммит**.

**Уже сделано (не трогаем):** TUI, Orchestrator `/multitask`, queue/serve/watch/schedule, export, Ollama.

---

## Расписание (~8–10 ч)

| Блок | Время | Фаза | Результат |
|------|-------|------|-----------|
| 1 | 09:00–10:30 | A | CLI + REPL basics | ✅ |
| 2 | 10:30–12:00 | B | Plugins | ✅ |
| 3 | 12:00–13:00 | C | Auto-save | ✅ |
| 4 | 13:00–14:30 | D | TUI parity | ✅ |
| 5 | 14:30–16:00 | E | Tray + serve | ✅ |
| 6 | 16:00–18:00 | F | Zenith orchestrator UI | ✅ |
| 7 | 18:00–19:30 | G | VS Code / Cursor MVP | ✅ |

---

## Фаза A — CLI + `/config` (1.5 ч)

### A1. `axon multitask "goal"`
- [ ] `cli.py` — subcommand `multitask` с аргументом goal, флаг `--agents`, `--json`
- [ ] Headless: `Orchestrator` без Rich, вывод synthesis в stdout / JSON
- [ ] `ui/headless.py` или отдельный runner — переиспользовать `orchestrator.py`

**Проверка:**
```powershell
axon multitask "list top 5 python files in this repo"
axon multitask --agents axon "summarize README" --json
```

### A2. `/config` в REPL
- [ ] `ui/repl.py` — `/config` show | `/config set <key> <value>` | `/config path`
- [ ] Ключи: `allow_parallel_agents`, `autonomy_enabled`, `notifications_enabled`, `sound_on_*`
- [ ] `ui/completer.py` + `AXON_COMMANDS`
- [ ] Читать/писать через `runtime_policy.py` (уже есть save/load)

**Проверка:**
```
/config
/config set allow_parallel_agents true
/config
```

**Коммит:** `feat: add axon multitask CLI and /config in REPL`

---

## Фаза B — Plugins (1.5 ч)

### B1. Подключить loader в REPL
- [ ] При старте `start_axon()` — `discover_plugins(workspace)`
- [ ] Маршрутизация: `/plugin-cmd` или имена из `register()` → `plugin.run()`
- [ ] Слить `list_plugin_commands()` в `/help`
- [ ] Ошибки плагина — красное сообщение, не падать весь REPL

### B2. Пример плагина
- [ ] `.axon/plugins/example.py` — `register()` → `{"hello": fn}` с docstring
- [ ] README snippet в `.axon/plugins/README.md`

### B3. (Опционально) хук `on_message`
- [ ] Расширить `register()` до `{commands, hooks}` или отдельный `on_user_message` — **только если успеваем**

**Проверка:**
```
/help          # видны plugin-команды
/hello         # example plugin
```

**Коммит:** `feat: wire .axon/plugins into REPL and /help`

---

## Фаза C — Auto-save сессии (1 ч)

- [ ] `runtime_policy.json` или `config.json`: `auto_save_session: true` (default false)
- [ ] При `/exit`, Ctrl+C, SIGINT в REPL — `save_session()` если есть user messages
- [ ] Имя: `auto-YYYY-MM-DD-HHMM` или последний title
- [ ] `/config set auto_save_session true`
- [ ] Сообщение: `[dim]Session saved as <id>[/]`

**Проверка:** написать 2 сообщения → `/exit` → `/sessions` видит auto-save.

**Коммит:** `feat: optional auto-save session on REPL exit`

---

## Фаза D — TUI parity (1.5 ч)

Минимум для «не урезанный» TUI:

- [ ] `/multitask` в `ui/axon_tui.py` — вызов `Orchestrator`, вывод в transcript
- [ ] `/config` — read-only show + подсказка «use REPL for set»
- [ ] `/delegate`, `/plan`, `/cost` — уже частично; добить список из `AXON_COMMANDS` где trivial
- [ ] Bridge: при TUI не ломать — опционально `broadcast_stats` после ответа
- [ ] Plugin commands в TUI `_handle_command` — делегировать в loader

**Не в этот день:** полный streaming parity, approval UI в TUI (оставить run_in_terminal).

**Проверка:**
```powershell
python cli.py tui
/multitask explain project structure
/config
```

**Коммит:** `feat: extend TUI with multitask, config, and plugin commands`

---

## Фаза E — Tray + background serve (1.5 ч)

### E1. Tray icon (Windows)
- [ ] `axon_tray.py` — pystray или ctypes + иконка из `assets/`
- [ ] Меню: Open REPL, Open Zenith, Pause serve, Quit
- [ ] `axon tray` — запуск tray loop
- [ ] `axon serve --tray` — queue worker + tray

### E2. Зависимости
- [ ] `requirements.txt` — `pystray`, `Pillow` (optional extra `[tray]`)

**Проверка:** `axon serve --tray` — иконка в трее, double-click открывает браузер или статус.

**Коммит:** `feat: Windows tray for axon serve`

---

## Фаза F — Zenith Orchestrator UI (2 ч)

### F1. Bridge events
- [ ] `bridge.py` — `broadcast_multitask_update(phase, subtasks, synthesis)`
- [ ] `orchestrator.py` — optional callback `on_progress` → bridge (из REPL передавать bridge)

### F2. Frontend
- [ ] `zenith-web/components/dashboard/MultitaskPanel.tsx` — список subtasks + статусы
- [ ] `ChatContext` или новый `OrchestratorContext` — слушать WS `multitask_update`
- [ ] Dashboard tab или секция под plan board

### F3. Запуск с веба (stretch)
- [ ] POST `/api/multitask` → прокси в bridge → REPL если запущен  
- [ ] **Если не успеваем:** только отображение прогресса с терминала

**Проверка:** REPL `/multitask ...` — в Zenith dashboard видны шаги в реальном времени.

**Коммит:** `feat: Zenith multitask progress panel via bridge`

---

## Фаза G — VS Code / Cursor MVP (1.5 ч)

**Scope MVP (не полный extension marketplace):**

- [ ] Папка `vscode-extension/` — `package.json`, `activationEvents`, команда `axon.openPanel`
- [ ] Webview или terminal task: запуск `axon -p` с выделенным текстом
- [ ] `tasks.json` snippet для Cursor — «Send selection to AXON»
- [ ] README: установка unpacked extension

**Не в MVP:** inline diff, LSP, auth — в backlog.

**Проверка:** выделить код → команда → AXON отвечает в output channel.

**Коммит:** `feat: vscode/cursor extension MVP for selection prompts`

---

## Порядок коммитов (итого 7)

1. `feat: add axon multitask CLI and /config in REPL`
2. `feat: wire .axon/plugins into REPL and /help`
3. `feat: optional auto-save session on REPL exit`
4. `feat: extend TUI with multitask, config, and plugin commands`
5. `feat: Windows tray for axon serve`
6. `feat: Zenith multitask progress panel via bridge`
7. `feat: vscode/cursor extension MVP for selection prompts`

---

## Если не успеваем — приоритет среза

| Держать обязательно | Отложить |
|---------------------|----------|
| A, B, C | G полный webview |
| D `/multitask` в TUI | F POST multitask с веба |
| E tray базовый | Plugin hooks on_message |
| F только bridge + панель | Extension в marketplace |

---

## Финал дня

- [ ] `python -m py_compile` на изменённых модулях
- [ ] `axon doctor`
- [ ] Обновить `ROADMAP_PC.md` — перенести done в таблицу
- [ ] Push `origin/main` (по желанию)
- [ ] Короткий smoke: REPL → `/multitask` → Zenith dashboard → `axon tui` → `axon tray`

---

## Следующий шаг

Начинаем **Фаза A** — напиши «го A» или просто «начинай».
