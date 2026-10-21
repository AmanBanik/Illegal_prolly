import pytest
from unittest.mock import MagicMock
from Proj_03.src.exceptions import (
    CollisionExhaustionError,
    InvalidShortCodeError,
    InvalidUrlError,
)
from Proj_03.src.service import UrlShortenerService


def test_url_validation_valid(service):
    assert service.validate_url("https://example.com") == "https://example.com"
    assert service.validate_url("http://localhost:8080/path?query=1") == "http://localhost:8080/path?query=1"
    assert service.validate_url("https://sub.domain.org/nested/resource#section") == "https://sub.domain.org/nested/resource#section"


def test_url_validation_invalid(service):
    with pytest.raises(InvalidUrlError):
        service.validate_url("ftp://example.com")
    with pytest.raises(InvalidUrlError):
        service.validate_url("javascript:alert(1)")
    with pytest.raises(InvalidUrlError):
        service.validate_url("not_a_url")
    with pytest.raises(InvalidUrlError):
        service.validate_url("")
    with pytest.raises(InvalidUrlError):
        service.validate_url("https://" + "a" * 2050)


def test_custom_code_validation_valid(service):
    assert service.validate_custom_code("promo2026") == "promo2026"
    assert service.validate_custom_code("my-custom_link") == "my-custom_link"
    assert service.validate_custom_code("abc") == "abc"


def test_custom_code_validation_invalid(service):
    with pytest.raises(InvalidShortCodeError):
        service.validate_custom_code("ab")  # Too short (<3)
    with pytest.raises(InvalidShortCodeError):
        service.validate_custom_code("a" * 35)  # Too long (>30)
    with pytest.raises(InvalidShortCodeError):
        service.validate_custom_code("has space")
    with pytest.raises(InvalidShortCodeError):
        service.validate_custom_code("invalid$char")


def test_custom_code_reserved_keywords(service):
    with pytest.raises(InvalidShortCodeError):
        service.validate_custom_code("api")
    with pytest.raises(InvalidShortCodeError):
        service.validate_custom_code("stats")
    with pytest.raises(InvalidShortCodeError):
        service.validate_custom_code("admin")


def test_collision_retry_and_exhaustion():
    mock_repo = MagicMock()
    # Mock code_exists to always return True (always collision)
    mock_repo.code_exists.return_value = True

    svc = UrlShortenerService(repository=mock_repo, max_collision_retries=3)
    with pytest.raises(CollisionExhaustionError):
        svc._generate_unique_code()
    assert mock_repo.code_exists.call_count == 3
