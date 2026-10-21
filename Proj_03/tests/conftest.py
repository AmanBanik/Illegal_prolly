import sys
from pathlib import Path
import pytest

# Ensure workspace root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from Proj_03.src.app import create_app
from Proj_03.src.repository import LinkRepository
from Proj_03.src.service import UrlShortenerService


@pytest.fixture
def repository():
    repo = LinkRepository(db_path=":memory:")
    yield repo
    repo.close()


@pytest.fixture
def service(repository):
    return UrlShortenerService(repository=repository)


@pytest.fixture
def client(service):
    app = create_app(service=service)
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
