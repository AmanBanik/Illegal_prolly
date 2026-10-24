"""Pytest fixtures for SlotWise Reservation Service tests."""

import os
import tempfile
import pytest
from flask.testing import FlaskClient

from Proj_04.src.app import create_app
from Proj_04.src.repository import ReservationRepository
from Proj_04.src.service import ReservationService


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def repository(temp_db_path):
    repo = ReservationRepository(db_path=temp_db_path)
    yield repo
    repo.close()


@pytest.fixture
def service(repository):
    svc = ReservationService(repository=repository)
    yield svc
    svc.close()


@pytest.fixture
def sample_session(service):
    return service.create_session(
        title="Intro to Distributed Systems",
        total_capacity=5,
        start_time="2026-11-01T10:00:00Z",
        end_time="2026-11-01T12:00:00Z",
        session_id="sess_dist_sys",
    )


@pytest.fixture
def client(service) -> FlaskClient:
    app = create_app(service)
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
