import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--fsldir", action="store", default=None, help="Path to root FSL installation"
    )
    parser.addoption(
        "--fshome", action="store", default=None, help="Path to root FreeSurfer installation"
    )
    parser.addoption(
        "--antsdir", action="store", default=None, help="Path to root ANTs installation"
    )


@pytest.fixture
def fsldir(request):
    return request.config.getoption("--fsldir")


@pytest.fixture
def freesurfer_home(request):
    return request.config.getoption("--fshome")


@pytest.fixture
def antsdir(request):
    return request.config.getoption("--antsdir")
