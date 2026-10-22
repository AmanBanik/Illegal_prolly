"""Pytest fixtures for the Comments & Replies test suite."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from Proj_02.src.app import create_app
from Proj_02.src.service import CommentService


@pytest.fixture
def service() -> CommentService:
    """Fixture providing a fresh, isolated CommentService instance."""
    return CommentService()


@pytest.fixture
def app(service: CommentService) -> Flask:
    """Fixture providing a configured Flask application instance."""
    flask_app = create_app(service)
    flask_app.config.update({"TESTING": True})
    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Fixture providing a test client for API requests."""
    return app.test_client()
