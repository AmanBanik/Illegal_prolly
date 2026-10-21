import pytest
from Proj_10.src.checker import RuleBasedContentChecker
from Proj_10.src.exceptions import ValidationError
from Proj_10.src.service import ReviewDesk


def test_service_initialization_validation():
    checker = RuleBasedContentChecker()

    with pytest.raises(ValidationError):
        ReviewDesk(checker=None)

    with pytest.raises(ValidationError):
        ReviewDesk(checker=checker, max_strikes=0)

    with pytest.raises(ValidationError):
        ReviewDesk(checker=checker, max_strikes=-2)

    with pytest.raises(ValidationError):
        ReviewDesk(checker=checker, max_content_length=0)


def test_create_comment_empty_or_invalid_fields(service):
    with pytest.raises(ValidationError):
        service.create_comment(post_id="", user_id="user_1", content="Hello")

    with pytest.raises(ValidationError):
        service.create_comment(post_id="   ", user_id="user_1", content="Hello")

    with pytest.raises(ValidationError):
        service.create_comment(post_id="post_1", user_id="", content="Hello")

    with pytest.raises(ValidationError):
        service.create_comment(post_id="post_1", user_id="  ", content="Hello")

    with pytest.raises(ValidationError):
        service.create_comment(post_id="post_1", user_id="user_1", content="")

    with pytest.raises(ValidationError):
        service.create_comment(post_id="post_1", user_id="user_1", content="   \t\n")

    with pytest.raises(ValidationError):
        service.create_comment(post_id=None, user_id="user_1", content="Hello")

    with pytest.raises(ValidationError):
        service.create_comment(post_id="post_1", user_id=None, content="Hello")

    with pytest.raises(ValidationError):
        service.create_comment(post_id="post_1", user_id="user_1", content=None)


def test_create_comment_oversized_content():
    checker = RuleBasedContentChecker()
    svc = ReviewDesk(checker=checker, max_content_length=50)

    # 50 chars is fine
    svc.create_comment("p1", "u1", "a" * 50)

    # 51 chars raises ValidationError
    with pytest.raises(ValidationError):
        svc.create_comment("p1", "u1", "a" * 51)


def test_edit_comment_invalid_params(service):
    comment = service.create_comment("post_1", "user_1", "Original")

    with pytest.raises(ValidationError):
        service.edit_comment(comment_id=0, user_id="user_1", new_content="Valid")

    with pytest.raises(ValidationError):
        service.edit_comment(comment_id=-1, user_id="user_1", new_content="Valid")

    with pytest.raises(ValidationError):
        service.edit_comment(comment_id="not_an_int", user_id="user_1", new_content="Valid")

    with pytest.raises(ValidationError):
        service.edit_comment(comment_id=comment.id, user_id="", new_content="Valid")

    with pytest.raises(ValidationError):
        service.edit_comment(comment_id=comment.id, user_id="user_1", new_content="")

    with pytest.raises(ValidationError):
        service.edit_comment(comment_id=comment.id, user_id="user_1", new_content="   ")
