from __future__ import annotations

import asyncio
import base64
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI

from config_store import get_model, get_openrouter_api_key, save_model, get_custom_headers
from provider_config import is_llm_configured, provider_config_hint, resolve_llm_endpoint
from system_prompt_store import get_global_system_prompt
from skills.tasks import execute_task_tool, get_task_tool_schemas, is_task_tool
from skills.tools import (
    ApprovalCallback,
    clear_read_file_cache,
    execute_tool,
    get_tools_schema,
    parse_tool_arguments,
    tool_activity_detail,
)
from skills.text_tool_calls import extract_text_tool_calls
from skills_manager import SkillManager, load_project_memory
from agent_manager import load_agent_prompt
from mcp_client import get_mcp_tool_schemas
from task_manager import task_manager

from pricing import estimate_cost
from context_optimizer import (
    compose_system_prompt,
    prepare_messages_for_api,
    should_auto_compact,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct"
COST_PER_TOKEN = 0.000002
MAX_TOOL_ROUNDS = 12
MAX_IMAGE_BYTES = 20 * 1024 * 1024
SUPPORTED_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})

AXON_SYSTEM_PROMPT_BASE = (
    "You are AXON, an agentic command-line AI assistant with access to tools. "
    "Use read_file, list_dir, glob_files, and search_code to explore codebases. "
    "Prefer apply_patch for small edits and write_file for new files or full rewrites. "
    "Use execute_shell for builds/tests when needed, and web_search for current docs. "
    "Users can load images with /image for multimodal vision models — analyze "
    "images carefully when they appear in the conversation. "
    "Call take_screenshot only when you genuinely need to see the desktop or "
    "verify a GUI outcome; do not screenshot after every command. "
    "With a vision-capable model, the screenshot is added to your context automatically. "
    "Markdown skills (SKILL.md) can be invoked as tools — when a skill returns "
    "instructions, follow them strictly and use allowed built-in tools to "
    "complete the user's request. "
    "write_file and execute_shell require explicit user approval — if denied, "
    "explain alternatives. When executing a plan, call complete_task after each "
    "finished step. After using tools, always reply with a clear summary "
    "for the user in plain language. "
    "When the user asks for a multi-step plan, call create_plan with 3-5 tasks. "
    "When the goal has independent parallel workstreams (e.g. review code AND "
    "write tests AND update docs), call run_multitask with the full goal. "
    "Never call tools for simple greetings, thanks, goodbye, or other small talk — "
    "reply briefly in plain text instead."
)

ToolNotifyCallback = Callable[[str, str], Awaitable[None]]
StreamTokenCallback = Callable[[str], Awaitable[None]]
StreamThinkingCallback = Callable[[str], Awaitable[None]]
StreamLifecycleCallback = Callable[[], Awaitable[None]]

TOTAL_TOKENS: int = 0
TOTAL_COST: float = 0.0
SESSION_PROMPT_TOKENS: int = 0
SESSION_COMPLETION_TOKENS: int = 0
SESSION_STARTED_AT: float = time.time()

_usage_listeners: list[Callable[[], None]] = []


def register_usage_listener(callback: Callable[[], None]) -> None:
    """Notify UI when session token/cost counters change."""
    if callback not in _usage_listeners:
        _usage_listeners.append(callback)


def _notify_usage_listeners() -> None:
    for callback in _usage_listeners:
        try:
            callback()
        except Exception:
            pass


def record_token_usage(
    total_tokens: int,
    *,
    model: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> None:
    global TOTAL_TOKENS, TOTAL_COST, SESSION_PROMPT_TOKENS, SESSION_COMPLETION_TOKENS
    prompt_i = max(int(prompt_tokens or 0), 0)
    completion_i = max(int(completion_tokens or 0), 0)
    if prompt_i or completion_i:
        tokens = prompt_i + completion_i
    else:
        tokens = max(int(total_tokens or 0), 0)
    TOTAL_TOKENS += tokens
    SESSION_PROMPT_TOKENS += prompt_i
    SESSION_COMPLETION_TOKENS += completion_i
    if model and (prompt_i or completion_i):
        TOTAL_COST += estimate_cost(model, prompt_i, completion_i)
    else:
        TOTAL_COST += tokens * COST_PER_TOKEN
    _notify_usage_listeners()


def reset_session_counters() -> None:
    global TOTAL_TOKENS, TOTAL_COST, SESSION_PROMPT_TOKENS, SESSION_COMPLETION_TOKENS
    TOTAL_TOKENS = 0
    TOTAL_COST = 0.0
    SESSION_PROMPT_TOKENS = 0
    SESSION_COMPLETION_TOKENS = 0
    _notify_usage_listeners()


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class LLMResult:
    content: str
    model: str
    usage: TokenUsage | None = None
    error: str | None = None
    tool_steps: int = 0

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def display_text(self) -> str:
        if self.ok:
            return self.content or "(empty response)"
        return self.error or "Unknown error"


@dataclass
class _ApiStreamResult:
    content: str
    tool_calls: list[dict[str, Any]]
    usage: object | None
    cancelled: bool = False


class LLMManager:
    """AXON LLM client with OpenRouter tool-calling agent loop."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        approve: ApprovalCallback | None = None,
        workspace: Path | None = None,
    ) -> None:
        self.model = model or get_model()
        self._workspace = workspace or Path.cwd()
        self._skill_manager = SkillManager(workspace=self._workspace)
        self._skill_manager.reload()
        self.session_system_prompt: str = ""
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._build_system_prompt()},
        ]
        self._api_key = api_key or get_openrouter_api_key()
        base_url, resolved_key = resolve_llm_endpoint()
        if api_key is None:
            self._api_key = resolved_key
            self._base_url = base_url
        else:
            self._base_url = OPENROUTER_BASE_URL
        self._client = self._build_client(self._api_key, self._base_url)
        self._approve = approve
        self._on_tool: ToolNotifyCallback | None = None
        self._on_stream_token: StreamTokenCallback | None = None
        self._on_stream_thinking: StreamThinkingCallback | None = None
        self._on_stream_start: StreamLifecycleCallback | None = None
        self._on_stream_end: StreamLifecycleCallback | None = None
        self._stream_loop: asyncio.AbstractEventLoop | None = None
        self._cancel_requested = False
        self._tool_schemas_cache: list[dict[str, Any]] | None = None
        self._tool_schemas_key: tuple[Any, ...] | None = None
        self.prompt_cache_enabled = True
        self.trim_tool_history = True
        self.auto_compact_enabled = True
        from ui.observe_mode import set_observe_llm

        set_observe_llm(self)

    def set_session_system_prompt(self, text: str) -> None:
        self.session_system_prompt = text.strip()
        self.refresh_system_prompt()

    def clear_session_system_prompt(self) -> None:
        self.session_system_prompt = ""
        self.refresh_system_prompt()

    def _build_system_prompt(self) -> str:
        dynamic_parts: list[str] = []

        from autopilot_mode import is_autopilot_active
        from runtime_policy import load_runtime_policy
        policy = load_runtime_policy()
        if is_autopilot_active() or policy.autonomy_enabled:
            dynamic_parts.append(
                "AUTOPILOT ACTIVE:\n"
                "You have full autonomy to read/write files and run shell commands without user prompts. "
                "If compilation or tests fail, analyze the error output, modify code, and retry. "
                "Do not stop until the goal is fully achieved and verified."
            )

        global_prompt = get_global_system_prompt()
        if global_prompt:
            dynamic_parts.append(f"User Instructions (always apply):\n{global_prompt}")

        if self.session_system_prompt:
            dynamic_parts.append(f"Session Instructions:\n{self.session_system_prompt}")

        memory = load_project_memory(self._workspace)
        if memory:
            dynamic_parts.append(f"Project Context:\n{memory}")
        skills_block = self._skill_manager.skills_summary_for_system()
        if skills_block:
            dynamic_parts.append(skills_block)

        try:
            from code_mapper import generate_code_map
            code_map = generate_code_map(self._workspace)
            if code_map:
                if len(code_map) > 4000:
                    code_map = code_map[:4000] + "\n... (remaining codebase map truncated) ..."
                dynamic_parts.append(code_map)
        except Exception:
            pass

        try:
            import subprocess
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self._workspace),
                capture_output=True,
                text=True,
                timeout=2
            )
            if res.returncode == 0 and res.stdout.strip():
                dirty_files = []
                for line in res.stdout.splitlines():
                    s_parts = line.strip().split(None, 1)
                    if len(s_parts) == 2:
                        dirty_files.append(s_parts[1])
                if dirty_files:
                    focus_list = "\n".join(f" - {f}" for f in dirty_files[:10])
                    dynamic_parts.append(
                        "ACTIVE DEVELOPMENT FOCUS (Git modified/dirty files):\n"
                        "You are currently modifying or working on these files. "
                        "Keep them in mind for code-related tasks:\n"
                        f"{focus_list}"
                    )
        except Exception:
            pass

        return compose_system_prompt(AXON_SYSTEM_PROMPT_BASE, "\n\n".join(dynamic_parts))

    def _build_agent_system_prompt(self, agent_prompt: str) -> str:
        parts = [
            agent_prompt.strip(),
            (
                "You are operating as an AXON sub-agent. You have the same native tools: "
                "read_file, write_file, execute_shell, web_search. "
                "write_file and execute_shell require user approval."
            ),
        ]
        memory = load_project_memory(self._workspace)
        if memory:
            parts.append(f"Project Context:\n{memory}")
        skills_block = self._skill_manager.skills_summary_for_system()
        if skills_block:
            parts.append(skills_block)
        return "\n\n".join(parts)

    def refresh_system_prompt(self) -> None:
        """Rebuild system message (memory, skills) without clearing chat."""
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0]["content"] = self._build_system_prompt()

    def reload_skills(self) -> int:
        """Rescan `.axon/skills/` and refresh the system prompt."""
        count = self._skill_manager.reload_if_changed()
        self._invalidate_tool_schema_cache()
        self.refresh_system_prompt()
        return count

    def _invalidate_tool_schema_cache(self) -> None:
        self._tool_schemas_cache = None
        self._tool_schemas_key = None

    def _get_all_tool_schemas(self) -> list[dict[str, Any]]:
        skill_names = tuple(sorted(self._skill_manager._by_tool_name))
        cache_key = (task_manager.plan_mode, skill_names)
        if self._tool_schemas_cache is not None and cache_key == self._tool_schemas_key:
            return self._tool_schemas_cache

        if task_manager.plan_mode:
            schemas = [
                schema
                for schema in get_task_tool_schemas()
                if schema["function"]["name"] == "create_plan"
            ]
        else:
            schemas = (
                get_tools_schema()
                + get_task_tool_schemas()
                + self._skill_manager.get_tool_schemas()
                + get_mcp_tool_schemas()
            )
        self._tool_schemas_cache = schemas
        self._tool_schemas_key = cache_key
        return schemas

    async def _dispatch_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        if is_task_tool(tool_name):
            return await execute_task_tool(tool_name, arguments)
        if self._skill_manager.is_skill_tool(tool_name):
            from ui.session_timeline import session_timeline

            session_timeline.record_skill(tool_name)
            return self._skill_manager.invoke_skill(tool_name, arguments)
        return await execute_tool(tool_name, arguments, self._approve)

    def _build_client(self, api_key: str, base_url: str | None = None) -> OpenAI:
        url = base_url or OPENROUTER_BASE_URL
        headers = get_custom_headers()
        return OpenAI(
            base_url=url,
            api_key=api_key or "missing-key",
            default_headers=headers if headers else None,
        )

    def set_approval_callback(self, approve: ApprovalCallback | None) -> None:
        self._approve = approve

    def set_tool_callback(self, callback: ToolNotifyCallback | None) -> None:
        self._on_tool = callback

    def set_stream_callbacks(
        self,
        *,
        on_token: StreamTokenCallback | None = None,
        on_thinking: StreamThinkingCallback | None = None,
        on_start: StreamLifecycleCallback | None = None,
        on_end: StreamLifecycleCallback | None = None,
    ) -> None:
        self._on_stream_token = on_token
        self._on_stream_thinking = on_thinking
        self._on_stream_start = on_start
        self._on_stream_end = on_end

    def spawn_worker(self) -> LLMManager:
        """Isolated LLM session for parallel sub-agents (does not share chat history)."""
        worker = LLMManager(
            api_key=self._api_key,
            model=self.model,
            approve=self._approve,
            workspace=self._workspace,
        )
        worker._base_url = self._base_url
        worker._client = self._build_client(self._api_key, self._base_url)
        worker.session_system_prompt = self.session_system_prompt
        worker.refresh_system_prompt()
        if self._on_tool:
            worker.set_tool_callback(self._on_tool)
        return worker

    async def complete_text_async(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.2,
    ) -> LLMResult:
        """Single-shot completion without tools or chat history mutation."""
        from config_store import get_provider
        if get_provider() == "antigravity":
            return await self._complete_text_antigravity(system=system, user=user)

        self.reload_credentials()
        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            choice = response.choices[0] if response.choices else None
            if choice is None:
                return LLMResult(
                    content="",
                    model=self.model,
                    error="AXON: Empty response from model.",
                )
            raw = (choice.message.content or "").strip()
            usage = self._parse_usage(response.usage)
            if usage is not None:
                record_token_usage(
                    usage.total_tokens,
                    model=self.model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                )
            if not raw:
                return LLMResult(
                    content="",
                    model=self.model,
                    error="AXON: Model returned empty text.",
                    usage=usage,
                )
            return LLMResult(content=raw, model=self.model, usage=usage)
        except APIError as exc:
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: API error — {self._friendly_api_error(exc)}",
            )
        except Exception as exc:
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: Could not complete request — {exc}",
            )

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def clear_cancel(self) -> None:
        self._cancel_requested = False

    def _is_cancelled(self) -> bool:
        return self._cancel_requested

    def reload_credentials(self) -> None:
        """Reload API endpoint when provider or API key changes."""
        base_url, key = resolve_llm_endpoint()
        if key != self._api_key or getattr(self, "_base_url", "") != base_url:
            self._api_key = key
            self._base_url = base_url
            self._client = self._build_client(key, base_url)

    def set_model(self, model: str) -> None:
        """Set active model and persist to shared config."""
        from ui.model_registry import normalize_model_id

        cleaned = normalize_model_id(model.strip())
        if not cleaned:
            return
        self.model = cleaned
        save_model(cleaned)

    @staticmethod
    def _image_media_type(path: Path) -> str:
        mapping = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return mapping.get(path.suffix.lower(), "image/jpeg")

    def load_image_into_context(
        self,
        image_path: str,
        prompt: str = "Analyze this image.",
    ) -> str | None:
        """Append an OpenAI-compatible vision user message. Returns error or None."""
        from ui.image_cmd import resolve_image_path

        path, resolve_error = resolve_image_path(image_path)
        if resolve_error:
            return resolve_error
        assert path is not None

        try:
            data = path.read_bytes()
        except OSError as exc:
            return f"AXON: Could not read image — {exc}"

        if len(data) > MAX_IMAGE_BYTES:
            return (
                f"AXON: Image too large ({len(data)} bytes). "
                f"Maximum is {MAX_IMAGE_BYTES} bytes."
            )

        encoded = base64.b64encode(data).decode("ascii")
        media_type = self._image_media_type(path)
        text = prompt.strip() or "Analyze this image."

        self.messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{encoded}",
                        },
                    },
                ],
            }
        )
        return None

    async def analyze_image_once_async(
        self,
        image_path: str,
        prompt: str,
        *,
        model: str | None = None,
    ) -> str:
        """One-shot vision call; returns description text (for non-vision chat models)."""
        from ui.image_cmd import resolve_image_path
        from ui.vision_models import SUGGESTED_VISION_MODELS, is_confirmed_non_vision

        primary = (model or self.model).strip() or SUGGESTED_VISION_MODELS[0]
        candidates = [primary]
        if is_confirmed_non_vision(primary):
            for candidate in SUGGESTED_VISION_MODELS:
                if candidate not in candidates:
                    candidates.append(candidate)

        path, resolve_error = resolve_image_path(image_path)
        if resolve_error:
            raise ValueError(resolve_error)
        assert path is not None

        data = path.read_bytes()
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError(f"Image too large ({len(data)} bytes)")

        encoded = base64.b64encode(data).decode("ascii")
        media_type = self._image_media_type(path)
        text = prompt.strip() or "Describe what is visible on this screen."
        payload = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{encoded}",
                        },
                    },
                ],
            }
        ]

        last_error: Exception | None = None
        for vision_model in candidates:
            try:
                response = await asyncio.to_thread(
                    self._client.chat.completions.create,
                    model=vision_model,
                    messages=payload,
                    max_tokens=600,
                )
            except (APIConnectionError, APITimeoutError, APIError) as exc:
                last_error = exc
                continue
            except Exception as exc:
                last_error = exc
                continue

            usage = getattr(response, "usage", None)
            if usage is not None:
                record_token_usage(
                    int(getattr(usage, "total_tokens", 0) or 0),
                    model=vision_model,
                    prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                    completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
                )

            message = response.choices[0].message
            return (message.content or "").strip()

        if last_error is not None:
            raise last_error
        return ""

    async def compact_context(self, keep_last: int = 6) -> tuple[bool, str]:
        if len(self.messages) <= keep_last + 1:
            return False, "Nothing to compact yet."

        system_msg = self.messages[0]
        middle = self.messages[1:-keep_last]
        tail = self.messages[-keep_last:]
        if not middle:
            return False, "Nothing to compact yet."

        summary_prompt = (
            "Summarize the following conversation turns into concise bullet points "
            "for future context. Preserve decisions, file paths, and open tasks.\n\n"
            + json.dumps(middle, ensure_ascii=False)[:12000]
        )

        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": summary_prompt}],
            )
            usage = self._parse_usage(response.usage)
            if usage:
                record_token_usage(usage.total_tokens)
            summary = (response.choices[0].message.content or "").strip()
        except Exception as exc:
            return False, f"Compact failed — {exc}"

        if not summary:
            return False, "Compact produced an empty summary."

        self.messages = [
            system_msg,
            {"role": "system", "content": f"Compacted conversation summary:\n{summary}"},
            *tail,
        ]
        return True, f"Compacted {len(middle)} messages into summary."

    def send_message(self, user_text: str) -> LLMResult:
        self.reload_credentials()
        self.reload_skills()
        try:
            return asyncio.run(self._agent_loop(user_text))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._agent_loop(user_text))
            finally:
                loop.close()

    async def send_message_async(
        self,
        user_text: str,
        *,
        file_context: str = "",
    ) -> LLMResult:
        self.reload_credentials()
        self.reload_skills()
        payload = user_text
        if file_context.strip():
            payload = (
                f"{user_text}\n\n---\n"
                f"[Context attached by user]\n{file_context.strip()}"
            )
        return await self._agent_loop(payload)

    async def send_plan_async(self, description: str) -> LLMResult:
        """Plan Mode — only create_plan tool, no execution."""
        self.reload_credentials()
        self.reload_skills()
        task_manager.goal = description.strip()
        task_manager.plan_mode = True
        prompt = (
            f"[Plan Mode] The user wants to: {description}\n\n"
            "You are in Plan Mode. DO NOT execute any actions yet "
            "(no read_file, write_file, execute_shell, or skills). "
            "Your ONLY goal right now is to use the create_plan tool to break "
            "this down into 3-5 logical steps."
        )
        try:
            result = await self._agent_loop(prompt)
            if not task_manager.has_plan():
                return LLMResult(
                    content=result.content or "",
                    model=self.model,
                    error=(
                        "AXON: No plan was created. "
                        "Ask again with /plan <goal> or tell the model to call create_plan."
                    ),
                    usage=result.usage,
                    tool_steps=result.tool_steps,
                )
            return result
        finally:
            task_manager.plan_mode = False

    async def send_execute_async(self) -> LLMResult:
        """Execute an existing plan step-by-step."""
        self.reload_credentials()
        self.reload_skills()
        if not task_manager.has_plan():
            return LLMResult(
                content="",
                model=self.model,
                error="AXON: No active plan. Use /plan <description> first.",
            )

        task_manager.execution_mode = True
        next_task = next(
            (task for task in task_manager.tasks if task.status != "done"),
            None,
        )
        next_label = (
            f"{next_task.id}. {next_task.name}" if next_task else "all tasks done"
        )
        prompt = (
            "[Execute Mode] The user approved plan execution.\n"
            "Work through the plan step by step using available tools.\n"
            "After completing each step, you MUST call complete_task(task_id).\n"
            f"Start with: {next_label}\n\n"
            f"Current plan:\n{task_manager.get_plan_plaintext()}"
        )
        try:
            return await self._agent_loop(prompt)
        finally:
            task_manager.execution_mode = False

    async def send_delegated_async(
        self,
        agent_name: str,
        task: str,
        *,
        file_context: str = "",
    ) -> LLMResult:
        """Run a task using a sub-agent's system_prompt.md while keeping native tools."""
        self.reload_credentials()
        self.reload_skills()

        agent_prompt = load_agent_prompt(agent_name, self._workspace)
        if not agent_prompt:
            return LLMResult(
                content="",
                model=self.model,
                error=(
                    f"AXON: Agent '{agent_name}' not found. "
                    f"Use /create-agent to scaffold one in .axon/agents/"
                ),
            )

        if not self.messages or self.messages[0].get("role") != "system":
            self.messages.insert(
                0,
                {"role": "system", "content": self._build_system_prompt()},
            )

        original_system = self.messages[0]["content"]
        self.messages[0]["content"] = self._build_agent_system_prompt(agent_prompt)

        payload = (
            f"[Delegated to agent: {agent_name}]\n{task.strip()}"
        )
        if file_context.strip():
            payload += (
                f"\n\n---\n[Context attached by user]\n{file_context.strip()}"
            )

        try:
            return await self._agent_loop(payload)
        finally:
            self.messages[0]["content"] = original_system

    async def generate_skill_file_async(self, description: str) -> LLMResult:
        """Ask the LLM for a complete AXON skill file (no tools)."""
        self.reload_credentials()
        skill_system = (
            "You are an AXON skill author. AXON skills are markdown files with YAML "
            "frontmatter followed by instruction markdown (not Python modules). "
            "Built-in tools: read_file, write_file, execute_shell, web_search. "
            "Inline shell injection uses !`command` syntax in the markdown body. "
            "Return ONLY the complete skill file inside one markdown code fence. "
            "No text outside the fence."
        )
        user_prompt = (
            "Create a complete AXON skill file based on this description: "
            f"{description}. Return the file content as a valid YAML header "
            "(name, description, usage) followed by markdown skill instructions "
            "that reference allowed AXON built-in tools and optional !`shell` blocks."
        )
        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": skill_system},
                    {"role": "user", "content": user_prompt},
                ],
            )
            choice = response.choices[0] if response.choices else None
            if choice is None:
                return LLMResult(
                    content="",
                    model=self.model,
                    error="AXON: Empty response while generating skill.",
                )

            raw = (choice.message.content or "").strip()
            usage = self._parse_usage(response.usage)
            if usage is not None:
                record_token_usage(usage.total_tokens)

            if not raw:
                return LLMResult(
                    content="",
                    model=self.model,
                    error="AXON: Model returned empty skill content.",
                    usage=usage,
                )

            return LLMResult(content=raw, model=self.model, usage=usage)
        except APIError as exc:
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: API error — {self._friendly_api_error(exc)}",
            )
        except Exception as exc:
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: Could not generate skill — {exc}",
            )

    async def generate_commit_message_async(
        self,
        status: str,
        diff: str,
    ) -> LLMResult:
        """Ask the LLM for a single Conventional Commit message (no tools)."""
        self.reload_credentials()
        commit_system = (
            "Analyze this git diff and status. Generate a single, highly professional "
            "Conventional Commit message (e.g., 'feat: added parser'). "
            "Return ONLY the commit message, no explanations."
        )
        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": commit_system},
                    {
                        "role": "user",
                        "content": (
                            f"## git status\n{status}\n\n## git diff\n{diff}"
                        ),
                    },
                ],
            )
            choice = response.choices[0] if response.choices else None
            if choice is None:
                return LLMResult(
                    content="",
                    model=self.model,
                    error="AXON: Empty response while generating commit message.",
                )

            raw = (choice.message.content or "").strip()
            message = raw.strip("`").strip()
            if message.startswith("```"):
                lines = message.splitlines()
                message = "\n".join(
                    line for line in lines if not line.strip().startswith("```")
                ).strip()

            usage = self._parse_usage(response.usage)
            if usage is not None:
                record_token_usage(usage.total_tokens)

            if not message:
                return LLMResult(
                    content="",
                    model=self.model,
                    error="AXON: Model returned an empty commit message.",
                    usage=usage,
                )

            return LLMResult(content=message, model=self.model, usage=usage)
        except APIError as exc:
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: API error — {self._friendly_api_error(exc)}",
            )
        except Exception as exc:
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: Could not generate commit message — {exc}",
            )

    async def _agent_loop(self, user_text: str) -> LLMResult:
        from config_store import get_provider
        if get_provider() == "antigravity":
            return await self._agent_loop_antigravity(user_text)

        if not is_llm_configured():
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: LLM provider is not configured. {provider_config_hint()}",
            )

        self.clear_cancel()
        from ui.explore_stats import reset_turn_explore_stats

        reset_turn_explore_stats()
        clear_read_file_cache()
        if self.auto_compact_enabled and should_auto_compact(self.messages):
            await self.compact_context()
        self.messages.append({"role": "user", "content": user_text})
        last_usage: TokenUsage | None = None
        tool_steps = 0
        self._stream_loop = asyncio.get_running_loop()

        from autopilot_mode import is_autopilot_active
        from runtime_policy import load_runtime_policy
        policy = load_runtime_policy()
        max_rounds = 40 if (is_autopilot_active() or policy.autonomy_enabled) else MAX_TOOL_ROUNDS

        try:
            for round_index in range(max_rounds):
                if self._is_cancelled():
                    self._rollback_last_user_message()
                    return LLMResult(
                        content="",
                        model=self.model,
                        error="AXON: Generation cancelled.",
                        usage=last_usage,
                        tool_steps=tool_steps,
                    )

                use_tools = round_index < max_rounds - 1
                stream_result = await asyncio.to_thread(
                    self._call_api_stream,
                    tools=self._get_all_tool_schemas() if use_tools else None,
                )
                last_usage = self._accumulate_usage(last_usage, stream_result.usage)

                if stream_result.cancelled:
                    self._rollback_last_user_message()
                    return LLMResult(
                        content="",
                        model=self.model,
                        error="AXON: Generation cancelled.",
                        usage=last_usage,
                        tool_steps=tool_steps,
                    )

                content = stream_result.content or ""
                tool_calls = list(stream_result.tool_calls)
                if not tool_calls and content:
                    cleaned, parsed_calls = extract_text_tool_calls(content)
                    if parsed_calls:
                        content = cleaned
                        tool_calls = parsed_calls

                if tool_calls:
                    self.messages.append(
                        {
                            "role": "assistant",
                            "content": content or None,
                            "tool_calls": tool_calls,
                        }
                    )
                    for tool_call in tool_calls:
                        if self._is_cancelled():
                            self._rollback_last_user_message()
                            return LLMResult(
                                content="",
                                model=self.model,
                                error="AXON: Generation cancelled.",
                                usage=last_usage,
                                tool_steps=tool_steps,
                            )
                        tool_steps += 1
                        tool_name = tool_call["function"]["name"]
                        arguments = parse_tool_arguments(
                            tool_call["function"].get("arguments") or "{}"
                        )
                        if self._on_tool is not None:
                            detail = tool_activity_detail(tool_name, arguments)
                            await self._on_tool(tool_name, detail)
                        result = await self._dispatch_tool(tool_name, arguments)
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": result,
                            }
                        )
                    continue

                content = content.strip()
                if content:
                    self.messages.append({"role": "assistant", "content": content})
                    return LLMResult(
                        content=content,
                        model=self.model,
                        usage=last_usage,
                        tool_steps=tool_steps,
                    )

                if tool_steps > 0:
                    continue

                return LLMResult(
                    content="",
                    model=self.model,
                    error="AXON: Model returned an empty response.",
                    usage=last_usage,
                    tool_steps=tool_steps,
                )

            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: Exceeded maximum tool rounds ({max_rounds}).",
                usage=last_usage,
                tool_steps=tool_steps,
            )
        except APITimeoutError:
            self._rollback_last_user_message()
            return LLMResult(
                content="",
                model=self.model,
                error="AXON: Request timed out. Check your connection and try again.",
                tool_steps=tool_steps,
            )
        except APIConnectionError:
            self._rollback_last_user_message()
            return LLMResult(
                content="",
                model=self.model,
                error="AXON: Could not connect to OpenRouter. Check your internet connection.",
                tool_steps=tool_steps,
            )
        except APIError as exc:
            self._rollback_last_user_message()
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: API error — {self._friendly_api_error(exc)}",
                tool_steps=tool_steps,
            )
        except Exception as exc:
            self._rollback_last_user_message()
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: Unexpected error — {exc}",
                tool_steps=tool_steps,
            )
        finally:
            self._stream_loop = None

    def _schedule_stream(self, coro: Any) -> None:
        loop = self._stream_loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)

    def _call_api_stream(
        self,
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> _ApiStreamResult:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": prepare_messages_for_api(
                self.messages,
                model=self.model,
                prompt_cache_enabled=self.prompt_cache_enabled,
                trim_tool_history=self.trim_tool_history,
            ),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = self._client.chat.completions.create(**kwargs)
        content_parts: list[str] = []
        tool_acc: dict[int, dict[str, str]] = {}
        usage_obj: object | None = None

        async def _emit_start() -> None:
            if self._on_stream_start:
                await self._on_stream_start()

        async def _emit_token(token: str) -> None:
            if self._on_stream_token:
                await self._on_stream_token(token)

        async def _emit_thinking(token: str) -> None:
            if self._on_stream_thinking:
                await self._on_stream_thinking(token)

        async def _emit_end() -> None:
            if self._on_stream_end:
                await self._on_stream_end()

        if self._on_stream_start:
            self._schedule_stream(_emit_start())

        for chunk in stream:
            if self._is_cancelled():
                return _ApiStreamResult("", [], usage_obj, cancelled=True)

            if getattr(chunk, "usage", None):
                usage_obj = chunk.usage

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None) or getattr(
                delta, "reasoning", None
            )
            if reasoning:
                if self._on_stream_thinking:
                    self._schedule_stream(_emit_thinking(reasoning))
            if delta.content:
                content_parts.append(delta.content)
                if self._on_stream_token:
                    self._schedule_stream(_emit_token(delta.content))

            for tc in delta.tool_calls or []:
                idx = tc.index
                if idx not in tool_acc:
                    tool_acc[idx] = {"id": "", "name": "", "arguments": ""}
                if tc.id:
                    tool_acc[idx]["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tool_acc[idx]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_acc[idx]["arguments"] += tc.function.arguments

        if self._on_stream_end:
            self._schedule_stream(_emit_end())

        content = "".join(content_parts)
        tool_calls: list[dict[str, Any]] = []
        for idx in sorted(tool_acc):
            entry = tool_acc[idx]
            if not entry["name"]:
                continue
            tool_calls.append(
                {
                    "id": entry["id"] or f"call_{idx}",
                    "type": "function",
                    "function": {
                        "name": entry["name"],
                        "arguments": entry["arguments"],
                    },
                }
            )

        return _ApiStreamResult(content, tool_calls, usage_obj)

    def _call_api(self, *, tools: list[dict[str, Any]] | None = None) -> Any:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": prepare_messages_for_api(
                self.messages,
                model=self.model,
                prompt_cache_enabled=self.prompt_cache_enabled,
                trim_tool_history=self.trim_tool_history,
            ),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self._client.chat.completions.create(**kwargs)

    def _accumulate_usage(
        self,
        previous: TokenUsage | None,
        usage: object | None,
    ) -> TokenUsage | None:
        parsed = self._parse_usage(usage)
        if parsed is not None:
            record_token_usage(
                parsed.total_tokens,
                model=self.model,
                prompt_tokens=parsed.prompt_tokens,
                completion_tokens=parsed.completion_tokens,
            )
        if previous is None:
            return parsed
        if parsed is None:
            return previous
        return TokenUsage(
            prompt_tokens=previous.prompt_tokens + parsed.prompt_tokens,
            completion_tokens=previous.completion_tokens + parsed.completion_tokens,
            total_tokens=previous.total_tokens + parsed.total_tokens,
        )

    @staticmethod
    def _serialize_assistant_message(message: Any) -> dict[str, Any]:
        tool_calls = getattr(message, "tool_calls", None) or []

        if tool_calls:
            payload: dict[str, Any] = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
            if message.content:
                payload["content"] = message.content
            return payload

        return {
            "role": "assistant",
            "content": message.content or "",
        }


    async def _complete_text_antigravity(self, system: str, user: str) -> LLMResult:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return LLMResult(
                content="",
                model=self.model,
                error="AXON: google-genai SDK is not installed. Please run: pip install google-genai",
            )
            
        try:
            from config_store import get_antigravity_api_key
            key = get_antigravity_api_key()
            client = genai.Client(api_key=key if key else None)
            
            model_name = self.model or "gemini-2.5-flash"
            if "/" in model_name:
                model_name = model_name.split("/")[-1]
            if model_name.startswith("google/"):
                model_name = model_name[7:]
            if not model_name.startswith("gemini-"):
                model_name = "gemini-2.5-flash"

            config = types.GenerateContentConfig(
                system_instruction=system,
            )
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=user,
                config=config
            )
            return LLMResult(content=response.text or "", model=model_name)
        except Exception as exc:
            return LLMResult(content="", model=self.model, error=f"AXON: Gemini API error — {exc}")

    async def _agent_loop_antigravity(self, user_text: str) -> LLMResult:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return LLMResult(
                content="",
                model=self.model,
                error="AXON: google-genai SDK is not installed. Please run: pip install google-genai",
            )

        self.clear_cancel()
        from ui.explore_stats import reset_turn_explore_stats
        reset_turn_explore_stats()
        clear_read_file_cache()

        if self.auto_compact_enabled and should_auto_compact(self.messages):
            await self.compact_context()

        self.messages.append({"role": "user", "content": user_text})
        
        from config_store import get_antigravity_api_key
        key = get_antigravity_api_key()
        client = genai.Client(api_key=key if key else None)

        model_name = self.model or "gemini-2.5-flash"
        if "/" in model_name:
            model_name = model_name.split("/")[-1]
        if model_name.startswith("google/"):
            model_name = model_name[7:]
        if not model_name.startswith("gemini-"):
            model_name = "gemini-2.5-flash"

        from autopilot_mode import is_autopilot_active
        from runtime_policy import load_runtime_policy
        policy = load_runtime_policy()
        max_rounds = 40 if (is_autopilot_active() or policy.autonomy_enabled) else MAX_TOOL_ROUNDS

        tool_steps = 0

        try:
            for round_index in range(max_rounds):
                if self._is_cancelled():
                    self._rollback_last_user_message()
                    return LLMResult(
                        content="",
                        model=self.model,
                        error="AXON: Generation cancelled.",
                        tool_steps=tool_steps,
                    )

                use_tools = round_index < max_rounds - 1
                contents = _openai_to_gemini_contents(self.messages)
                
                g_tools = []
                if use_tools:
                    openai_tools = self._get_all_tool_schemas()
                    declarations = []
                    for ot in openai_tools:
                        gfn = _openai_to_gemini_tool(ot)
                        declarations.append(types.FunctionDeclaration(**gfn))
                    if declarations:
                        g_tools = [types.Tool(function_declarations=declarations)]

                system_prompt = self._build_system_prompt()
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=g_tools if use_tools else None,
                )

                if self._on_stream_start:
                    await self._on_stream_start()

                content_parts = []
                accumulated_tool_calls = []

                response_stream = await client.aio.models.generate_content_stream(
                    model=model_name,
                    contents=contents,
                    config=config
                )

                async for chunk in response_stream:
                    if self._is_cancelled():
                        if self._on_stream_end:
                            await self._on_stream_end()
                        self._rollback_last_user_message()
                        return LLMResult(
                            content="",
                            model=self.model,
                            error="AXON: Generation cancelled.",
                            tool_steps=tool_steps,
                        )

                    if chunk.text:
                        content_parts.append(chunk.text)
                        if self._on_stream_token:
                            await self._on_stream_token(chunk.text)

                    if chunk.function_calls:
                        for fc in chunk.function_calls:
                            accumulated_tool_calls.append(fc)

                if self._on_stream_end:
                    await self._on_stream_end()

                content = "".join(content_parts).strip()
                
                import uuid
                import json
                tool_calls = []
                for fc in accumulated_tool_calls:
                    call_id = fc.id or f"call_{uuid.uuid4().hex[:12]}"
                    tool_calls.append({
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": fc.name,
                            "arguments": json.dumps(fc.args or {})
                        }
                    })

                if tool_calls:
                    self.messages.append(
                        {
                            "role": "assistant",
                            "content": content or None,
                            "tool_calls": tool_calls,
                        }
                    )
                    for tool_call in tool_calls:
                        if self._is_cancelled():
                            self._rollback_last_user_message()
                            return LLMResult(
                                content="",
                                model=self.model,
                                error="AXON: Generation cancelled.",
                                tool_steps=tool_steps,
                            )
                        tool_steps += 1
                        tool_name = tool_call["function"]["name"]
                        arguments = parse_tool_arguments(
                            tool_call["function"].get("arguments") or "{}"
                        )
                        if self._on_tool is not None:
                            detail = tool_activity_detail(tool_name, arguments)
                            await self._on_tool(tool_name, detail)
                        result = await self._dispatch_tool(tool_name, arguments)
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": result,
                            }
                        )
                    continue

                if content:
                    self.messages.append({"role": "assistant", "content": content})
                    return LLMResult(content=content, model=model_name, tool_steps=tool_steps)

            return LLMResult(
                content="AXON: Max tool execution rounds reached.",
                model=model_name,
                tool_steps=tool_steps,
            )

        except Exception as exc:
            if self._on_stream_end:
                await self._on_stream_end()
            return LLMResult(content="", model=self.model, error=f"AXON: Gemini API error — {exc}")


    def _rollback_last_user_message(self) -> None:
        if self.messages and self.messages[-1].get("role") == "user":
            self.messages.pop()

    @staticmethod
    def _friendly_api_error(exc: APIError) -> str:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", None) or str(exc)
        if status == 401:
            return "Invalid API key. Save a valid key in the AXON dashboard."
        if status == 402:
            return "Insufficient credits on your OpenRouter account."
        if status == 403:
            lowered = message.lower()
            if "key_model_access_denied" in lowered or "not allowed to access model" in lowered:
                return (
                    "This API key cannot use the selected model on OpenRouter. "
                    "Pick another model: /model meta-llama/llama-3.1-8b-instruct "
                    "or open the Zenith dashboard → Models."
                )
            return "Access denied (403). Check model id and API key permissions."
        if status == 429:
            return "Rate limit reached. Wait a moment and try again."
        return message[:200] if message else "Unknown API error."

    @staticmethod
    def _parse_usage(usage: object | None) -> TokenUsage | None:
        if usage is None:
            return None

        total = getattr(usage, "total_tokens", None)
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)

        if total is None and prompt is None and completion is None:
            if isinstance(usage, dict):
                total = usage.get("total_tokens")
                prompt = usage.get("prompt_tokens")
                completion = usage.get("completion_tokens")
            else:
                return None

        prompt_i = int(prompt or 0)
        completion_i = int(completion or 0)
        total_i = int(total or (prompt_i + completion_i))

        if total_i <= 0 and prompt_i <= 0 and completion_i <= 0:
            return None

        return TokenUsage(
            prompt_tokens=prompt_i,
            completion_tokens=completion_i,
            total_tokens=total_i,
        )


def _upper_type(val: Any) -> Any:
    if isinstance(val, dict):
        new_d = {}
        for k, v in val.items():
            if k == "type" and isinstance(v, str):
                new_d[k] = v.upper()
            else:
                new_d[k] = _upper_type(v)
        return new_d
    elif isinstance(val, list):
        return [_upper_type(item) for item in val]
    return val


def _openai_to_gemini_tool(openai_tool: dict) -> dict:
    fn = openai_tool.get("function", {})
    params = fn.get("parameters", {})
    params_upper = _upper_type(params)
    return {
        "name": fn.get("name"),
        "description": fn.get("description"),
        "parameters": params_upper
    }


def _openai_to_gemini_contents(messages: list[dict]) -> list[Any]:
    from google.genai import types
    gemini_contents = []
    for msg in messages:
        role = msg.get("role")
        if role == "system":
            continue
            
        parts = []
        if msg.get("content"):
            parts.append(types.Part.from_text(text=msg["content"]))
            
        if role == "assistant":
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                g_calls = []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    import json
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    g_calls.append(types.FunctionCall(
                        name=fn.get("name"),
                        args=args,
                        id=tc.get("id")
                    ))
                parts.extend(types.Part(function_call=c) for c in g_calls)
            
            gemini_contents.append(types.Content(role="model", parts=parts))
            
        elif role == "user":
            gemini_contents.append(types.Content(role="user", parts=parts))
            
        elif role == "tool":
            content_str = msg.get("content", "")
            import json
            try:
                response_dict = json.loads(content_str)
                if not isinstance(response_dict, dict):
                    response_dict = {"result": response_dict}
            except Exception:
                response_dict = {"response": content_str}
                
            fn_resp = types.FunctionResponse(
                name=msg.get("name", "unknown_tool"),
                response=response_dict,
                id=msg.get("tool_call_id")
            )
            for prev_msg in reversed(messages):
                if prev_msg.get("role") == "assistant" and prev_msg.get("tool_calls"):
                    for tc in prev_msg["tool_calls"]:
                        if tc.get("id") == msg.get("tool_call_id"):
                            fn_resp.name = tc["function"]["name"]
                            break
            
            parts.append(types.Part(function_response=fn_resp))
            gemini_contents.append(types.Content(role="user", parts=parts))
            
    return gemini_contents

