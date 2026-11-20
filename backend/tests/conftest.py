import pytest

from app.main import app


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Подмены зависимостей одного теста не должны протекать в следующий."""
    yield
    app.dependency_overrides.clear()
