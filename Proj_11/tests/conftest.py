"""Pytest fixtures for IssueHub Retry-Safe Issue Service tests."""

import pytest
from flask.testing import FlaskClient

from Proj_11.src.app import create_app
from Proj_11.src.models import ProjectRole
from Proj_11.src.service import IssueService
from Proj_11.src.storage import IssueStorage


@pytest.fixture
def storage() -> IssueStorage:
    return IssueStorage()


@pytest.fixture
def service(storage) -> IssueService:
    return IssueService(storage=storage)


@pytest.fixture
def sample_project(service) -> str:
    proj = service.create_project(
        project_id="proj_core",
        name="Core Infrastructure",
        owner_id="admin_alice",
    )
    # Add member_bob as MEMBER and viewer_charlie as VIEWER
    service.add_project_member("proj_core", "admin_alice", "member_bob", ProjectRole.MEMBER)
    service.add_project_member("proj_core", "admin_alice", "viewer_charlie", ProjectRole.VIEWER)
    return proj.project_id


@pytest.fixture
def client(service) -> FlaskClient:
    app = create_app(service)
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
