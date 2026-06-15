from __future__ import annotations

import asyncio
from dataclasses import dataclass

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI

from config_store import get_model, get_openrouter_api_key

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct"

AXON_SYSTEM_PROMPT = (
    "You are AXON, a helpful command-line AI assistant. "
    "Provide clear, concise answers."
)


@dataclass(frozen=True)
class TokenUsage:
    """Token usage metadata from the OpenRouter API response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class LLMResult:
    """Result of an AXON LLM request, including content and usage for cost tracking."""

    content: str
    model: str
    usage: TokenUsage | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def display_text(self) -> str:
        if self.ok:
            return self.content or "(empty response)"
        return self.error or "Unknown error"


class LLMManager:
    """AXON LLM client — reads shared config.json before each request."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model or get_model()
        self.messages: list[dict[str, str]] = [
            {"role": "system", "content": AXON_SYSTEM_PROMPT},
        ]
        self._api_key = api_key or get_openrouter_api_key()
        self._client = self._build_client(self._api_key)

    def _build_client(self, api_key: str) -> OpenAI:
        return OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key or "missing-key",
        )

    def reload_credentials(self) -> None:
        """Reload API key and model from shared config.json / .env."""
        key = get_openrouter_api_key()
        model = get_model()

        if model and model != self.model:
            self.model = model

        if key != self._api_key:
            self._api_key = key
            self._client = self._build_client(key)

    def set_model(self, model: str) -> None:
        self.model = model

    def send_message(self, user_text: str) -> LLMResult:
        """Synchronous LLM call (reloads shared config first)."""
        self.reload_credentials()
        return self._send_message_impl(user_text)

    async def send_message_async(self, user_text: str) -> LLMResult:
        """Async wrapper — safe to await from prompt_toolkit background tasks."""
        self.reload_credentials()
        return await asyncio.to_thread(self._send_message_impl, user_text)

    def _send_message_impl(self, user_text: str) -> LLMResult:
        if not self._api_key:
            return LLMResult(
                content="",
                model=self.model,
                error=(
                    "AXON: OPENROUTER_API_KEY is not set. "
                    "Save your key in the web dashboard or config.json."
                ),
            )

        self.messages.append({"role": "user", "content": user_text})

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=self.messages,
            )
        except APITimeoutError:
            self._rollback_last_user_message()
            return LLMResult(
                content="",
                model=self.model,
                error="AXON: Request timed out. Check your connection and try again.",
            )
        except APIConnectionError:
            self._rollback_last_user_message()
            return LLMResult(
                content="",
                model=self.model,
                error="AXON: Could not connect to OpenRouter. Check your internet connection.",
            )
        except APIError as exc:
            self._rollback_last_user_message()
            return LLMResult(
                content="",
                model=self.model,
                error=f"AXON: API error — {self._friendly_api_error(exc)}",
            )
        except Exception:
            self._rollback_last_user_message()
            return LLMResult(
                content="",
                model=self.model,
                error="AXON: An unexpected error occurred. Please try again.",
            )

        choice = response.choices[0] if response.choices else None
        content = (choice.message.content or "").strip() if choice else ""

        if content:
            self.messages.append({"role": "assistant", "content": content})

        usage = self._parse_usage(response.usage)

        return LLMResult(
            content=content,
            model=self.model,
            usage=usage,
        )

    def _rollback_last_user_message(self) -> None:
        if self.messages and self.messages[-1]["role"] == "user":
            self.messages.pop()

    @staticmethod
    def _friendly_api_error(exc: APIError) -> str:
        status = getattr(exc, "status_code", None)
        if status == 401:
            return "Invalid API key. Save a valid key in the AXON dashboard."
        if status == 402:
            return "Insufficient credits on your OpenRouter account."
        if status == 429:
            return "Rate limit reached. Wait a moment and try again."
        message = getattr(exc, "message", None) or str(exc)
        return message[:200] if message else "Unknown API error."

    @staticmethod
    def _parse_usage(usage: object | None) -> TokenUsage | None:
        if usage is None:
            return None
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        total = getattr(usage, "total_tokens", None)
        if prompt is None and completion is None and total is None:
            return None
        return TokenUsage(
            prompt_tokens=int(prompt or 0),
            completion_tokens=int(completion or 0),
            total_tokens=int(total or (prompt or 0) + (completion or 0)),
        )
