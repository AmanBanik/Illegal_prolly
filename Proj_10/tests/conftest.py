import pytest
from Proj_10.src.checker import RuleBasedContentChecker
from Proj_10.src.service import ReviewDesk


@pytest.fixture
def default_checker():
    """Provides a content checker with common test banned keywords."""
    return RuleBasedContentChecker(
        banned_words=["spam", "violation", "scam", "profanity", "malware"],
        banned_patterns=[r"https?://phishing\.com"],
    )


@pytest.fixture
def service(default_checker):
    """Provides a fresh ReviewDesk service with 3-strike threshold."""
    return ReviewDesk(checker=default_checker, max_strikes=3, max_content_length=1000)
