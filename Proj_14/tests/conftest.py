import pytest
from Proj_14.src.app import create_app
from Proj_14.src.service import ScreenShelf


@pytest.fixture
def service():
    """Provides an in-memory ScreenShelf service instance."""
    shelf = ScreenShelf(db_path=":memory:")
    yield shelf
    shelf.close()


@pytest.fixture
def file_db_service(tmp_path):
    """Provides a file-backed ScreenShelf service instance on disk."""
    db_file = str(tmp_path / "screenshelf_test.db")
    shelf = ScreenShelf(db_path=db_file)
    yield shelf, db_file
    shelf.close()


@pytest.fixture
def app(service):
    """Provides a Flask application configured with the in-memory service."""
    flask_app = create_app(service=service)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    """Provides a test HTTP client for ScreenShelf REST API."""
    return app.test_client()
