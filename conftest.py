import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--fsldir", action="store", default=None, help="Path to root FSL installation"
    )


@pytest.fixture
def fsldir(request):
    return request.config.getoption("--fsldir")
