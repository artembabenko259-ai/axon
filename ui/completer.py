from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.document import Document

SLASH_COMMANDS = [
    "/help",
    "/exit",
    "/clear",
    "/cost",
    "/usage",
    "/compact",
    "/model",
    "/plan",
    "/execute",
    "/image",
    "/export-skill",
    "/session",
    "/create-skill",
    "/gen-skill",
    "/review",
    "/undo",
    "/commit",
    "/docs",
    "/create-agent",
    "/delegate",
    "/multitask",
    "/config",
    "/provider",
    "/claw",
    "/openclaw",
    "/system",
    "/sessions",
    "/resume",
    "/save",
    "/export",
    "/mcp",
    "/login",
    "/logout",
]

AXON_COMMANDS: dict[str, str] = {
    "/help": "List available slash commands",
    "/exit": "Exit AXON",
    "/clear": "Clear chat context (keeps system prompt)",
    "/cost": "Show session cost and token usage",
    "/usage": "Alias for /cost",
    "/compact": "Summarize older messages to free context window (also runs automatically)",
    "/model": "Switch model — e.g. /model anthropic/claude-3.5-sonnet",
    "/plan": "Plan Mode — /plan <description> to break work into steps",
    "/execute": "Run the active plan step-by-step",
    "/tasks": "Toggle plan task side panel — F2",
    "/thinking": "Toggle AI reasoning trace in chat — F3",
    "/image": "Vision — /image <path|@file> [prompt]",
    "/export-skill": "Export skill to .axon/exports — /export-skill <name>",
    "/session": "Toggle session timeline panel — F4",
    "/create-skill": "Interactive wizard to create a new SKILL.md",
    "/gen-skill": "AI-generate a skill from a description — /gen-skill \"...\"",
    "/review": "Review current git diff for bugs and code smells",
    "/undo": "Restore last file overwritten by write_file",
    "/commit": "AI-generated Conventional Commit with confirmation",
    "/docs": "Generate and serve interactive project docs at localhost:8000",
    "/create-agent": "Scaffold a sub-agent in .axon/agents/",
    "/delegate": "Delegate task to sub-agent — /delegate <name> <task>",
    "/multitask": "Orchestrator — parallel subtasks — /multitask <goal>",
    "/config": "Runtime policy — /config | /config set <key> <value>",
    "/provider": "LLM provider — /provider | /provider custom <url> <key>",
    "/claw": "OpenClaw full autonomy — /claw on|off|status (admin)",
    "/openclaw": "Alias for /claw",
    "/system": "Session/global system prompt — /system session|global|edit|clear",
    "/sessions": "List saved chat sessions",
    "/resume": "Resume session — /resume <id>",
    "/save": "Save current session — /save [title]",
    "/export": "Export session to Markdown — /export [path]",
    "/mcp": "MCP servers — /mcp list | /mcp add <name> <command...>",
    "/login": "Sign in via runaxon.xyz — opens browser for email registration",
    "/logout": "Sign out of AXON account on this machine",
}


def build_slash_completer() -> WordCompleter:
    return WordCompleter(SLASH_COMMANDS, ignore_case=True)


class AxonCommandCompleter(Completer):
    """Slash-command completer with descriptions — Tab to complete."""

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        if not text.startswith("/"):
            return

        if " " in text.strip() and not text.strip().startswith(
            (
                "/model",
                "/plan",
                "/image",
                "/delegate",
                "/gen-skill",
                "/multitask",
                "/config",
                "/claw",
                "/openclaw",
                "/resume",
                "/export",
                "/mcp",
                "/system",
            )
        ):
            return

        word = text.split()[-1] if text.endswith(" ") else text

        for command, description in AXON_COMMANDS.items():
            if command.startswith(word):
                yield Completion(
                    command,
                    start_position=-len(word),
                    display=command,
                    display_meta=description,
                )

        if word.startswith("/mul") and "/multitask" not in word:
            yield Completion(
                "/multitask ",
                start_position=-len(word),
                display="/multitask ",
                display_meta=AXON_COMMANDS["/multitask"],
            )

        if word.startswith("/del") and "/delegate" not in word:
            yield Completion(
                "/delegate ",
                start_position=-len(word),
                display="/delegate ",
                display_meta=AXON_COMMANDS["/delegate"],
            )

        if word.startswith("/doc") and "/docs" not in word:
            yield Completion(
                "/docs",
                start_position=-len(word),
                display="/docs",
                display_meta=AXON_COMMANDS["/docs"],
            )

        if word.startswith("/com") and "/commit" not in word:
            yield Completion(
                "/commit",
                start_position=-len(word),
                display="/commit",
                display_meta=AXON_COMMANDS["/commit"],
            )

        if word.startswith("/und") and "/undo" not in word:
            yield Completion(
                "/undo",
                start_position=-len(word),
                display="/undo",
                display_meta=AXON_COMMANDS["/undo"],
            )

        if word.startswith("/cre") and "/create-skill" not in word:
            yield Completion(
                "/create-skill",
                start_position=-len(word),
                display="/create-skill",
                display_meta=AXON_COMMANDS["/create-skill"],
            )

        if word.startswith("/gen") and "/gen-skill" not in word:
            yield Completion(
                "/gen-skill ",
                start_position=-len(word),
                display="/gen-skill ",
                display_meta=AXON_COMMANDS["/gen-skill"],
            )

        if word.startswith("/rev") and "/review" not in word:
            yield Completion(
                "/review",
                start_position=-len(word),
                display="/review",
                display_meta=AXON_COMMANDS["/review"],
            )

        if word.startswith("/ima") and "/image" not in word:
            yield Completion(
                "/image ",
                start_position=-len(word),
                display="/image ",
                display_meta=AXON_COMMANDS["/image"],
            )

        if word.startswith("/pla") and "/plan" not in word:
            yield Completion(
                "/plan ",
                start_position=-len(word),
                display="/plan ",
                display_meta=AXON_COMMANDS["/plan"],
            )

        if word.startswith("/mod") and "/model" not in word:
            yield Completion(
                "/model ",
                start_position=-len(word),
                display="/model ",
                display_meta=AXON_COMMANDS["/model"],
            )
