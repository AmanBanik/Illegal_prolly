import re
from typing import Callable, Iterable, Optional, Protocol, Set
from .exceptions import CheckerExecutionError
from .models import ModerationResult


class ContentChecker(Protocol):
    """Protocol defining the interface for injected moderation checkers."""

    def check_content(self, text: str) -> ModerationResult:
        """Inspects text and returns a ModerationResult.

        Raises:
            Exception: If an external inspection failure occurs (network timeout, 500 error, etc.)
        """
        ...


class RuleBasedContentChecker:
    """Production reference checker evaluating forbidden words and regex patterns."""

    def __init__(
        self,
        banned_words: Optional[Iterable[str]] = None,
        banned_patterns: Optional[Iterable[str]] = None,
    ):
        self._banned_words: Set[str] = {w.lower().strip() for w in (banned_words or []) if w.strip()}
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in (banned_patterns or [])
        ]

    def check_content(self, text: str) -> ModerationResult:
        # Check explicit banned words
        normalized = text.lower()
        words = set(re.findall(r"\b\w+\b", normalized))
        matched_words = words.intersection(self._banned_words)
        if matched_words:
            word = sorted(matched_words)[0]
            return ModerationResult.rejected(reason=f"Forbidden keyword detected: '{word}'")

        # Check regex patterns
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                return ModerationResult.rejected(reason=f"Pattern match violation: '{pattern.pattern}'")

        return ModerationResult.approved()


class CallableContentChecker:
    """Adapter wrapping any arbitrary function into a ContentChecker."""

    def __init__(self, func: Callable[[str], ModerationResult]):
        self._func = func

    def check_content(self, text: str) -> ModerationResult:
        return self._func(text)
