"""Fast-path routing for trivial chat — no LLM, no tools."""

from __future__ import annotations

import random
import re

_WORD_RE = re.compile(r"[\w']+", re.UNICODE)

_CHITCHAT_WORDS = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "yo",
        "sup",
        "thanks",
        "thank",
        "you",
        "thx",
        "bye",
        "goodbye",
        "ok",
        "okay",
        "how",
        "are",
        "doing",
        "morning",
        "evening",
        "night",
        "good",
        "привет",
        "приветик",
        "здравствуй",
        "здравствуйте",
        "здарова",
        "здорово",
        "спасибо",
        "благодарю",
        "пока",
        "как",
        "дела",
        "что",
        "нового",
        "доброе",
        "утро",
        "день",
        "вечер",
        "привіт",
        "вітаю",
        "дякую",
        "спасибі",
        "бувай",
        "справи",
        "доброго",
        "ранку",
        "дня",
        "вечора",
    }
)

_GREETING_HINTS = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "привет",
        "привіт",
        "здравствуй",
        "здравствуйте",
        "здарова",
        "здорово",
        "вітаю",
        "good",
        "доброе",
        "доброго",
    }
)

_REPLIES: dict[str, tuple[str, ...]] = {
    "en": (
        "Hello! I'm AXON — your CLI agent. Ask me to inspect files, run commands, or help with code.",
        "Hi there! What would you like to work on?",
    ),
    "ru": (
        "Привет! Я AXON — твой CLI-агент. Могу помочь с кодом, файлами и командами.",
        "Здравствуй! Чем помочь?",
    ),
    "uk": (
        "Привіт! Я AXON — твій CLI-агент. Можу допомогти з кодом, файлами та командами.",
        "Вітаю! Чим допомогти?",
    ),
}

_THANKS_REPLIES: dict[str, tuple[str, ...]] = {
    "en": ("You're welcome!", "Happy to help."),
    "ru": ("Пожалуйста!", "Рад помочь."),
    "uk": ("Будь ласка!", "Радий допомогти."),
}

_BYE_REPLIES: dict[str, tuple[str, ...]] = {
    "en": ("Goodbye! I'll be here when you need me.",),
    "ru": ("До встречи! Обращайся, если понадоблюсь.",),
    "uk": ("До зустрічі! Звертайся, якщо знадоблюсь.",),
}


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _WORD_RE.findall(text)]


def _detect_lang(words: list[str]) -> str:
    joined = " ".join(words)
    if any(ch in joined for ch in "іїєґ"):
        return "uk"
    if any("\u0400" <= ch <= "\u04ff" for ch in joined):
        return "ru"
    return "en"


def is_chitchat_only(text: str) -> bool:
    words = _tokenize(text.strip())
    if not words or len(words) > 6:
        return False
    return all(word in _CHITCHAT_WORDS for word in words)


def try_chitchat_reply(text: str) -> str | None:
    stripped = text.strip()
    if not stripped or stripped.startswith("/"):
        return None
    if "@" in stripped or "[file:" in stripped:
        return None

    words = _tokenize(stripped)
    if not is_chitchat_only(stripped):
        return None

    lang = _detect_lang(words)
    lowered = set(words)

    if lowered & {"thanks", "thank", "thx", "спасибо", "дякую", "благодарю", "спасибі"}:
        return random.choice(_THANKS_REPLIES[lang])

    if lowered & {"bye", "goodbye", "пока", "бувай"}:
        return random.choice(_BYE_REPLIES[lang])

    if lowered & _GREETING_HINTS or lowered & {"как", "дела", "справи", "how", "are"}:
        return random.choice(_REPLIES[lang])

    return random.choice(_REPLIES[lang])
